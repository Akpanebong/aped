import csv, json
from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Q, Count, Sum
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from xml.sax.saxutils import escape
from .models import MonitoringForm, MonitoringRecord, FollowUpAction
from .forms import MonitoringFormDefinitionForm, MonitoringRecordForm, FollowUpActionForm
from .linked_records import linked_record_choices as get_linked_record_choices
from account.permissions import create_required, edit_required, system_admin_required


@login_required
def form_definition_list(request):
    forms = (
        MonitoringForm.objects
        .annotate(record_count=Count("records", distinct=True))
        .order_by("category", "name")
    )

    summary = forms.aggregate(
        total_records=Sum("record_count")
    )

    context = {
        "forms": forms,
        "active_count": forms.filter(is_active=True).count(),
        "total_records": summary["total_records"] or 0,
    }

    return render(
        request,
        "monitoring/form_definition_list.html",
        context,
    )

@login_required
@system_admin_required
def form_definition_create(request):
    form = MonitoringFormDefinitionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            obj = form.save()
        except IntegrityError:
            form.add_error('slug', 'A monitoring form with this slug already exists.')
        else:
            messages.success(request, 'Monitoring form created.')
            return redirect('form_definition_list')
    return render(request, 'monitoring/form_definition_form.html', {
        'form': form,
        'page_title': 'Create monitoring form',
        'schema_data': schema_builder_data(request),
    })


@login_required
@system_admin_required
def form_definition_update(request, pk):
    obj = get_object_or_404(MonitoringForm, pk=pk)
    form = MonitoringFormDefinitionForm(request.POST or None, instance=obj)
    if request.method == 'POST' and form.is_valid():
        try:
            form.save()
        except IntegrityError:
            form.add_error('slug', 'A monitoring form with this slug already exists.')
        else:
            messages.success(request, 'Monitoring form updated.')
            return redirect('form_definition_list')
    return render(request, 'monitoring/form_definition_form.html', {
        'form': form,
        'page_title': 'Edit monitoring form',
        'monitoring_form': obj,
        'schema_data': schema_builder_data(request, obj),
    })


def schema_builder_data(request, obj=None):
    if request.method == 'POST':
        try:
            value = json.loads(request.POST.get('schema', '[]'))
            return value if isinstance(value, list) else []
        except (TypeError, ValueError):
            return []
    return (obj.schema if obj else []) or []


@login_required
@system_admin_required
def form_definition_delete(request, pk):
    obj = get_object_or_404(MonitoringForm, pk=pk)
    if request.method == 'POST':
        try:
            obj.delete()
        except ProtectedError:
            messages.error(request, 'This monitoring form cannot be deleted because it has saved records. Deactivate it instead.')
            return redirect('form_definition_list')
        messages.success(request, 'Monitoring form deleted.')
        return redirect('form_definition_list')
    return render(request, 'monitoring/form_definition_confirm_delete.html', {'object': obj})


@login_required
def form_catalog(request):
    category = request.GET.get("category", "").strip()

    forms = (
        MonitoringForm.objects
        .filter(is_active=True)
        .annotate(record_count=Count("records"))
        .order_by("category", "name")
    )

    if category:
        forms = forms.filter(category=category)

    context = {
        "forms": forms,
        "categories": MonitoringForm.CATEGORY_CHOICES,
        "category": category,
    }

    return render(request, "monitoring/monitoring_tool_list.html", context)


@login_required
def form_records(request, form_id):
    monitoring_form = get_object_or_404(MonitoringForm, pk=form_id, is_active=True)
    records = monitoring_form.records.select_related('created_by').all()
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    if q:
        records = records.filter(Q(reference__icontains=q) | Q(group_or_beneficiary__icontains=q) | Q(location__icontains=q) | Q(district__icontains=q))
    if status:
        records = records.filter(status=status)
    return render(request, 'monitoring/monitoring_tool_detail.html', {
        'monitoring_form': monitoring_form,
        'records': records,
        'filters': request.GET,
    })

@login_required
def record_list(request):
    records=MonitoringRecord.objects.select_related('form','created_by','project','activity')
    q=request.GET.get('q','').strip(); form_id=request.GET.get('form',''); status=request.GET.get('status','')
    start=request.GET.get('start',''); end=request.GET.get('end',''); district=request.GET.get('district','')
    if q: records=records.filter(Q(reference__icontains=q)|Q(location__icontains=q)|Q(group_or_beneficiary__icontains=q)|Q(project_name__icontains=q))
    if form_id: records=records.filter(form_id=form_id)
    if status: records=records.filter(status=status)
    if start: records=records.filter(visit_date__gte=start)
    if end: records=records.filter(visit_date__lte=end)
    if district: records=records.filter(district__icontains=district)
    return render(request,'monitoring/record_list.html',{'records':records,'forms':MonitoringForm.objects.filter(is_active=True),'filters':request.GET})

@login_required
@create_required
def record_create(request):
    initial = {}
    for key in ('form', 'activity', 'group_or_beneficiary', 'project_name', 'location', 'district'):
        if request.GET.get(key):
            initial[key] = request.GET[key]
    form=MonitoringRecordForm(request.POST or None, initial=initial)
    selected_schema=[]
    if request.method=='POST':
        if form.is_valid():
            required_errors = required_schema_errors(request, form.cleaned_data['form'])
            if required_errors:
                form.add_error(None, 'Complete the required monitoring fields: ' + ', '.join(required_errors))
            else:
                obj=form.save(commit=False); obj.created_by=request.user
                if obj.project:
                    obj.project_name = obj.project.name
                if obj.activity and not obj.project:
                    obj.project = obj.activity.project
                    obj.project_name = obj.activity.project.name
                obj.data=collect_schema_data(request, obj.form)
                obj.save(); messages.success(request,'Monitoring record saved.'); return redirect('record_detail',pk=obj.pk)
        form_id=request.POST.get('form')
        if form_id:
            try: selected_schema=MonitoringForm.objects.get(pk=form_id).schema
            except MonitoringForm.DoesNotExist: pass
    elif request.GET.get('form'):
        form.fields['form'].initial=request.GET['form']
        try: selected_schema=MonitoringForm.objects.get(pk=request.GET['form']).schema
        except (MonitoringForm.DoesNotExist,ValueError): pass
    return render(request,'monitoring/record_form.html',{'form':form,'schema':prepare_schema(selected_schema),'page_title':'New monitoring record'})

@login_required
@edit_required
def record_update(request,pk):
    obj=get_object_or_404(MonitoringRecord,pk=pk); form=MonitoringRecordForm(request.POST or None,instance=obj)
    schema=obj.form.schema
    if request.method=='POST' and form.is_valid():
        required_errors = required_schema_errors(request, form.cleaned_data['form'])
        if required_errors:
            form.add_error(None, 'Complete the required monitoring fields: ' + ', '.join(required_errors))
        else:
            obj=form.save(commit=False); obj.updated_by=request.user; obj.data=collect_schema_data(request,obj.form)
            if obj.project:
                obj.project_name = obj.project.name
            if obj.activity and not obj.project:
                obj.project = obj.activity.project
                obj.project_name = obj.activity.project.name
            obj.save()
            messages.success(request,'Record updated.'); return redirect('record_detail',pk=obj.pk)
    return render(request,'monitoring/record_form.html',{'form':form,'schema':prepare_schema(schema,obj.data),'page_title':'Update monitoring record','record':obj})

def required_schema_errors(request, monitoring_form):
    errors = []
    for section_index, section in enumerate(monitoring_form.schema or [], 1):
        section_title = section.get('title', f'Section {section_index}')
        section_key = section.get('key', f'section_{section_index}')
        required_fields = [field for field in section.get('fields', []) if field.get('required')]
        if section.get('repeatable'):
            for row_index in range(100):
                row_values = [request.POST.get(f"{section_key}__row_{row_index}__{field['name']}", '').strip() for field in section.get('fields', [])]
                if not any(row_values):
                    continue
                for field in required_fields:
                    if not request.POST.get(f"{section_key}__row_{row_index}__{field['name']}", '').strip():
                        errors.append(f"{section_title}: {field.get('label', field['name'])}")
        else:
            for field in required_fields:
                if not request.POST.get(f"{section_key}__{field['name']}", '').strip():
                    errors.append(f"{section_title}: {field.get('label', field['name'])}")
    return errors

def collect_schema_data(request, monitoring_form):
    data={}
    for section_index, section in enumerate(monitoring_form.schema, 1):
        section_key=section.get('key',f'section_{section_index}')
        if section.get('repeatable'):
            rows=[]
            for row_index in range(0, 100):
                row={}
                for field in section.get('fields',[]):
                    key=f"{section_key}__row_{row_index}__{field['name']}"
                    value = 'Yes' if field.get('type') == 'checkbox' and request.POST.get(key) else request.POST.get(key, '').strip()
                    if field.get('type') == 'checkbox' or value:
                        row[field['label'].lstrip('▢ ').strip()] = value or 'No'
                if row: rows.append(row)
            if rows: data[section.get('title','Section')]=rows
        else:
            values={}
            for field in section.get('fields',[]):
                key=f"{section_key}__{field['name']}"
                value = 'Yes' if field.get('type') == 'checkbox' and request.POST.get(key) else request.POST.get(key, '').strip()
                if field.get('type') == 'checkbox' or value:
                    values[field['label'].lstrip('▢ ').strip()] = value or 'No'
            if values: data[section.get('title','Section')]=values
    return data


def prepare_schema(schema, saved_data=None):
    saved_data=saved_data or {}
    prepared=[]
    for section_index, section in enumerate(schema or [], 1):
        item=dict(section)
        item['key']=section.get('key',f'section_{section_index}')
        existing=saved_data.get(section.get('title',''), [])
        if section.get('repeatable'):
            if isinstance(existing, dict): existing=[existing]
            rows=[]
            for row_index, row in enumerate(existing or [{}]):
                rows.append({'fields': [prepared_field(field, row, item['key'], row_index) for field in section.get('fields',[]) ]})
            while len(rows)<3:
                row_index=len(rows)
                rows.append({'fields': [prepared_field(field, {}, item['key'], row_index) for field in section.get('fields',[]) ]})
            item['rows']=rows
        else:
            values=existing if isinstance(existing, dict) else {}
            item['fields']=[prepared_field(field, values, item['key']) for field in section.get('fields',[])]
        prepared.append(item)
    return prepared


def prepared_field(field, values, section_key, row_index=None):
    field = dict(field)
    if field.get('type') == 'linked_record':
        field['choices'] = get_linked_record_choices(field.get('linked_model'))
    suffix = f'__row_{row_index}__' if row_index is not None else '__'
    label = field.get('label', '')
    field['value'] = values.get(label, values.get(label.lstrip('▢ ').strip(), ''))
    field['input_name'] = f"{section_key}{suffix}{field['name']}"
    return field


def linked_record_choices(linked_model):
    from core.models import FieldAttendance, FieldAttendancePart
    if linked_model == 'field_attendance_participant':
        records = FieldAttendancePart.objects.select_related('attendance', 'attendance__activity').order_by('name')
        return [(str(record.pk), f'{record.name} — {record.attendance}') for record in records]
    records = FieldAttendance.objects.select_related('activity').order_by('-activity_date', '-created_at')
    return [(str(record.pk), str(record)) for record in records]

@login_required
def record_detail(request,pk):
    obj=get_object_or_404(MonitoringRecord.objects.select_related('form','created_by','project','activity'),pk=pk)
    actions=obj.followups.select_related('assigned_to')
    action_form=FollowUpActionForm()
    if request.method=='POST':
        action_form=FollowUpActionForm(request.POST)
        if action_form.is_valid():
            action=action_form.save(commit=False); action.record=obj; action.save()
            messages.success(request,'Follow-up action added.'); return redirect('record_detail',pk=obj.pk)
    structured_sections=[]
    saved_data = obj.data or {}
    for index, section in enumerate(obj.form.schema or [], 1):
        title = section.get('title', f'Section {index}')
        values = saved_data.get(title, [] if section.get('repeatable') else {})
        rows = values if isinstance(values, list) else [values]
        if section.get('repeatable') and not rows:
            rows = [{}]
        if not section.get('repeatable') and not rows:
            rows = [{}]
        structured_rows = []
        for row in rows:
            row = row if isinstance(row, dict) else {}
            structured_rows.append([(field.get('label', ''), row.get(field.get('label', ''), '')) for field in section.get('fields', [])])
        structured_sections.append({'id': f'monitoring-section-{index}', 'title': title, 'repeatable': section.get('repeatable', False), 'rows': structured_rows})
    section_links = []
    for index, section in enumerate(obj.form.schema or [], 1):
        section_links.append({'id': f'monitoring-section-{index}', 'title': section.get('title', f'Section {index}'), 'index': index})
    return render(request,'monitoring/record_detail.html',{
        'record':obj,
        'actions':actions,
        'action_form':action_form,
        'structured_sections':structured_sections,
        'section_links':section_links,
    })

@login_required
@edit_required
def record_section_update(request, pk, section_index):
    obj = get_object_or_404(MonitoringRecord.objects.select_related('form', 'project', 'activity'), pk=pk)
    sections = obj.form.schema or []
    if section_index < 1 or section_index > len(sections):
        from django.http import Http404
        raise Http404('Monitoring section not found.')
    section = sections[section_index - 1]
    if request.method == 'POST':
        section_data = collect_schema_data(request, type('SectionForm', (), {'schema': [section]}))
        obj.data = {**(obj.data or {}), **section_data}
        obj.updated_by = request.user
        obj.save(update_fields=['data', 'updated_by', 'updated_at'])
        messages.success(request, f"{section.get('title', 'Section')} saved.")
        return redirect('record_detail', pk=obj.pk)
    prepared = prepare_schema([section], obj.data)
    return render(request, 'monitoring/section_form.html', {
        'record': obj,
        'section': prepared[0] if prepared else {},
        'section_index': section_index,
        'section_count': len(sections),
    })

@login_required
@system_admin_required
def record_delete(request,pk):
    obj=get_object_or_404(MonitoringRecord,pk=pk)
    if request.method=='POST':
        obj.delete(); messages.success(request,'Monitoring record deleted.'); return redirect('record_list')
    return render(request,'monitoring/confirm_delete.html',{'object':obj,'cancel_url':'record_detail'})

@login_required
@edit_required
def followup_update(request,pk):
    obj=get_object_or_404(FollowUpAction,pk=pk); record_id=obj.record_id
    form=FollowUpActionForm(request.POST or None,instance=obj)
    if request.method=='POST' and form.is_valid():
        form.save(); messages.success(request,'Follow-up updated.'); return redirect('record_detail',pk=record_id)
    return render(request,'monitoring/followup_form.html',{'form':form,'action':obj})

@login_required
@system_admin_required
def followup_delete(request,pk):
    obj=get_object_or_404(FollowUpAction,pk=pk); rid=obj.record_id
    if request.method=='POST': obj.delete(); messages.success(request,'Follow-up deleted.')
    return redirect('record_detail',pk=rid)

@login_required
def export_excel(request):
    records=filtered_records(request)
    export_scope = 'filtered' if export_filters_applied(request) else 'all'
    records = list(records)
    wb=Workbook(); ws=wb.active; ws.title='Monitoring records'
    core_headers=['Reference','Form','Visit date','Project','Location','District','Beneficiary / Group','Status','Officer','Observations']
    dynamic_headers=[]
    for record in records:
        for section, field, _row, _value in structured_export_rows(record):
            header=f'{section} / {field}'
            if header not in dynamic_headers: dynamic_headers.append(header)
    headers=core_headers + dynamic_headers
    ws.append(headers)
    for r in records:
        values={}
        for section, field, _row, value in structured_export_rows(r):
            values.setdefault(f'{section} / {field}', []).append(value)
        ws.append([
            r.reference, r.form.name, str(r.visit_date), r.project.name if r.project else r.project_name,
            r.location, r.district, r.group_or_beneficiary, r.get_status_display(), str(r.created_by or ''),
            r.observations,
        ] + ['; '.join(values.get(header, [])) for header in dynamic_headers])
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width=min(max(max(len(str(c.value or '')) for c in col)+2,14),45)
    ws.freeze_panes='A2'; ws.auto_filter.ref=ws.dimensions

    detail_ws=wb.create_sheet('Field data')
    detail_ws.append(['Reference','Form','Section','Row','Field','Value'])
    for r in records:
        for section, field, row_number, value in structured_export_rows(r):
            detail_ws.append([r.reference, r.form.name, section, row_number, field, value])
    for col in detail_ws.columns:
        detail_ws.column_dimensions[col[0].column_letter].width=min(max(max(len(str(c.value or '')) for c in col)+2,14),55)
    detail_ws.freeze_panes='A2'; detail_ws.auto_filter.ref=detail_ws.dimensions
    response=HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition']=f'attachment; filename="aped-monitoring-records-{export_scope}.xlsx"'; wb.save(response); return response

@login_required
def export_pdf(request):
    records=filtered_records(request)
    export_scope = 'filtered' if export_filters_applied(request) else 'all'
    response=HttpResponse(content_type='application/pdf'); response['Content-Disposition']=f'attachment; filename="aped-monitoring-records-{export_scope}.pdf"'
    doc=SimpleDocTemplate(response,pagesize=landscape(A4),rightMargin=24,leftMargin=24,topMargin=28,bottomMargin=24)
    styles=getSampleStyleSheet()
    cell_style=styles['BodyText'].clone('MonitoringRecordCell')
    cell_style.fontName='Helvetica'; cell_style.fontSize=7; cell_style.leading=8
    header_style=cell_style.clone('MonitoringRecordHeader')
    header_style.fontName='Helvetica-Bold'; header_style.textColor=colors.white
    story=[Paragraph('APED Monitoring Records',styles['Title']),Spacer(1,12)]
    records = list(records)
    for index, r in enumerate(records):
        story.append(Paragraph(escape(f'{r.reference} — {r.form.name}'), styles['Heading2']))
        metadata=[
            ['Visit date', str(r.visit_date or ''), 'Status', r.get_status_display()],
            ['Project', r.project.name if r.project else r.project_name, 'Officer', str(r.created_by or '')],
            ['Location', r.location, 'District', r.district],
            ['Group / beneficiary', r.group_or_beneficiary, 'Observations', r.observations],
        ]
        metadata_table=Table([[Paragraph(escape(str(v or '')), header_style if i % 2 == 0 else cell_style) for i,v in enumerate(row)] for row in metadata], colWidths=[75,195,75,195])
        metadata_table.setStyle(TableStyle([('BACKGROUND',(0,0),(0,-1),colors.HexColor('#163b32')),('BACKGROUND',(2,0),(2,-1),colors.HexColor('#163b32')),('TEXTCOLOR',(0,0),(0,-1),colors.white),('TEXTCOLOR',(2,0),(2,-1),colors.white),('GRID',(0,0),(-1,-1),.35,colors.HexColor('#d7dfdb')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5)]))
        story.extend([metadata_table, Spacer(1,8)])
        field_rows=[[Paragraph('Section',header_style), Paragraph('Row',header_style), Paragraph('Field',header_style), Paragraph('Value',header_style)]]
        field_rows.extend([[Paragraph(escape(str(section)),cell_style), Paragraph(escape(str(row_number)),cell_style), Paragraph(escape(str(field)),cell_style), Paragraph(escape(str(value or '')),cell_style)] for section, field, row_number, value in structured_export_rows(r)])
        if len(field_rows) == 1:
            field_rows.append([Paragraph('No structured fields captured.', cell_style), '', '', ''])
        field_table=Table(field_rows, repeatRows=1, colWidths=[170,35,150,185])
        field_table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#163b32')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),.35,colors.HexColor('#d7dfdb')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f2f6f3')]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5)]))
        story.append(field_table)
        if index < len(records)-1: story.append(PageBreak())
    if not records: story.append(Paragraph('No monitoring records matched the selected filters.', cell_style))
    doc.build(story); return response


def structured_export_rows(record):
    """Return every schema field and captured value in export-friendly rows."""
    rows=[]
    saved=record.data or {}
    known_sections=set()
    for section in record.form.schema or []:
        title=section.get('title','Section')
        known_sections.add(title)
        values=saved.get(title, [] if section.get('repeatable') else {})
        section_rows=values if isinstance(values, list) else [values]
        if not section.get('repeatable'): section_rows=section_rows[:1]
        for row_number, value_map in enumerate(section_rows, 1):
            value_map=value_map if isinstance(value_map, dict) else {}
            schema_labels=set()
            for field in section.get('fields', []):
                label=field.get('label','')
                value=value_map.get(label, value_map.get(label.lstrip('▢ ').strip(), ''))
                if value not in ('', None, []):
                    rows.append((title, label.lstrip('▢ ').strip(), row_number, export_value(value)))
                schema_labels.update((label, label.lstrip('▢ ').strip()))
            for label, value in value_map.items():
                if label not in schema_labels and value not in ('', None, []):
                    rows.append((title, str(label).lstrip('▢ ').strip(), row_number, export_value(value)))
    # Preserve data written by older/custom schemas even if the schema changed later.
    for title, section_data in saved.items():
        if title in known_sections or not isinstance(section_data, dict): continue
        for label, value in section_data.items():
            if value not in ('', None, []): rows.append((title, str(label).lstrip('▢ ').strip(), 1, export_value(value)))
    return rows


def export_value(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


EXPORT_FILTER_KEYS = ('q', 'form', 'status', 'start', 'end', 'district')


def export_filters_applied(request):
    """Treat blank query-string controls as unfiltered exports."""
    return any(request.GET.get(key, '').strip() for key in EXPORT_FILTER_KEYS)

def filtered_records(request):
    records=MonitoringRecord.objects.select_related('form','created_by','project')
    q=request.GET.get('q','').strip(); form_id=request.GET.get('form',''); status=request.GET.get('status','')
    start=request.GET.get('start',''); end=request.GET.get('end',''); district=request.GET.get('district','')
    if q: records=records.filter(Q(reference__icontains=q)|Q(location__icontains=q)|Q(group_or_beneficiary__icontains=q)|Q(project_name__icontains=q))
    if form_id: records=records.filter(form_id=form_id)
    if status: records=records.filter(status=status)
    if start: records=records.filter(visit_date__gte=start)
    if end: records=records.filter(visit_date__lte=end)
    if district: records=records.filter(district__icontains=district)
    return records
