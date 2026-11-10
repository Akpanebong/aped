from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render
from monitoring.models import MonitoringForm, MonitoringRecord, FollowUpAction
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from .forms import ActivityForm, FieldAttendanceForm, FieldAttendanceParticipantFormSet, ProjectForm
from .models import Activity, FieldAttendance, Project
from account.permissions import approval_required, create_required, edit_required, system_admin_required


@login_required
def dashboard(request):
    forms=MonitoringForm.objects.filter(is_active=True).order_by('category','name')
    records=MonitoringRecord.objects.select_related('form','created_by').order_by('-created_at')
    q=request.GET.get('q','').strip(); form_id=request.GET.get('form','').strip(); status=request.GET.get('status','').strip()
    start=request.GET.get('start','').strip(); end=request.GET.get('end','').strip(); district=request.GET.get('district','').strip()
    if q: records=records.filter(Q(reference__icontains=q)|Q(location__icontains=q)|Q(group_or_beneficiary__icontains=q)|Q(project_name__icontains=q))
    if form_id: records=records.filter(form_id=form_id)
    if status: records=records.filter(status=status)
    if start: records=records.filter(visit_date__gte=start)
    if end: records=records.filter(visit_date__lte=end)
    if district: records=records.filter(district__icontains=district)
    actions=FollowUpAction.objects.select_related('record').order_by('due_date')[:8]
    context={
      'forms':forms,'recent_records':records[:8],'record_count':records.count(),
      'form_count':forms.count(),'open_actions':FollowUpAction.objects.exclude(status='done').count(),
      'overdue_actions':FollowUpAction.objects.filter(status__in=['open','in_progress'],due_date__lt=__import__('django').utils.timezone.localdate()).count(),
      'actions':actions,'filters':request.GET,
    }
    context['metric_cards']=[
      ('Monitoring records', context['record_count'], 'All field submissions'),
      ('Active tools', context['form_count'], 'Configured APED forms'),
      ('Open follow-ups', context['open_actions'], 'Actions not yet completed'),
      ('Overdue actions', context['overdue_actions'], 'Past due date'),
    ]
    return render(request,'core/dashboard.html',context)


@login_required
def project_list(request):
    projects = Project.objects.order_by("-start_date", "name")

    context = {
        "projects": projects,
        "active_count": projects.filter(is_active=True).count(),
        "inactive_count": projects.filter(is_active=False).count(),
    }

    return render(
        request,
        "core/project_list.html",
        context,
    )

@login_required
@create_required
def project_create(request):
    form = ProjectForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Project created.')
        return redirect('project_list')
    return render(request, 'core/project_form.html', {'form': form, 'page_title': 'Create project'})


@login_required
def activity_list(request):
    return render(request, 'core/activity_list.html', {'activities': Activity.objects.select_related('project', 'created_by')})


@login_required
@create_required
def activity_create(request):
    form = ActivityForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        activity = form.save(commit=False)
        activity.created_by = request.user
        activity.save()
        messages.success(request, 'Activity created.')
        return redirect('activity_list')
    return render(request, 'core/activity_form.html', {'form': form, 'page_title': 'Create activity'})


@login_required
def attendance_list(request):
    sheets = filtered_attendance_sheets(request)
    return render(request, 'core/attendance_list.html', {
        'sheets': sheets,
        'activities': Activity.objects.order_by('-activity_date', 'activity_name'),
        'status_choices': FieldAttendance._meta.get_field('status').choices,
        'filters': request.GET,
    })


def filtered_attendance_sheets(request):
    sheets = FieldAttendance.objects.select_related('activity', 'activity__project', 'submitted_by').prefetch_related('participants')
    activity = request.GET.get('activity', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    district = request.GET.get('district', '').strip()
    status = request.GET.get('status', '').strip()
    participant = request.GET.get('participant', '').strip()
    if activity:
        sheets = sheets.filter(activity_id=activity)
    if date_from:
        sheets = sheets.filter(activity_date__gte=date_from)
    if date_to:
        sheets = sheets.filter(activity_date__lte=date_to)
    if district:
        sheets = sheets.filter(district__icontains=district)
    if status:
        sheets = sheets.filter(status=status)
    if participant:
        sheets = sheets.filter(participants__name__icontains=participant).distinct()
    return sheets


@login_required
@create_required
def attendance_create(request):
    sheet = FieldAttendance()
    initial = {}
    if request.method == 'GET' and request.GET.get('activity'):
        activity = get_object_or_404(Activity, pk=request.GET['activity'])
        initial.update({
            'activity': activity.pk,
            'activity_date': activity.activity_date,
            'village': activity.village,
        })
    form = FieldAttendanceForm(request.POST or None, instance=sheet, initial=initial)
    formset = FieldAttendanceParticipantFormSet(request.POST or None, instance=sheet)
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        sheet = form.save(commit=False)
        sheet.submitted_by = request.user
        sheet.save()
        formset.instance = sheet
        formset.save()
        messages.success(request, 'Attendance sheet recorded.')
        return redirect('attendance_detail', sheet.pk)
    return render(request, 'core/attendance_form.html', {'form': form, 'formset': formset, 'page_title': 'Record attendance'})


@login_required
@edit_required
def attendance_update(request, pk):
    sheet = get_object_or_404(FieldAttendance, pk=pk)
    form = FieldAttendanceForm(request.POST or None, instance=sheet)
    formset = FieldAttendanceParticipantFormSet(request.POST or None, instance=sheet)
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        was_reviewed = sheet.status in {'approved', 'rejected'}
        if was_reviewed:
            sheet.status = 'pending'
            sheet.reviewed_by = None
            sheet.reviewed_at = None
            sheet.rejection_reason = ''
        form.save()
        formset.save()
        messages.success(request, 'Attendance sheet updated and returned to pending approval.' if was_reviewed else 'Attendance sheet updated.')
        return redirect('attendance_detail', sheet.pk)
    return render(request, 'core/attendance_form.html', {'form': form, 'formset': formset, 'page_title': 'Edit attendance sheet', 'object': sheet})


@login_required
def attendance_detail(request, pk):
    sheet = get_object_or_404(FieldAttendance.objects.select_related('activity', 'activity__project').prefetch_related('participants'), pk=pk)
    return render(request, 'core/attendance_detail.html', {'sheet': sheet})


@login_required
@system_admin_required
def attendance_delete(request, pk):
    sheet = get_object_or_404(FieldAttendance, pk=pk)
    if request.method == 'POST':
        sheet.delete()
        messages.success(request, 'Attendance sheet deleted.')
    return redirect('attendance_list')


@login_required
@approval_required
def attendance_approve(request, pk):
    sheet = get_object_or_404(FieldAttendance, pk=pk)
    if request.method == 'POST':
        sheet.status = 'approved'
        sheet.reviewed_by = request.user
        sheet.reviewed_at = timezone.now()
        sheet.rejection_reason = ''
        sheet.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'rejection_reason', 'updated_at'])
        messages.success(request, 'Attendance sheet approved.')
    return redirect('attendance_detail', pk=pk)


@login_required
@approval_required
def attendance_reject(request, pk):
    sheet = get_object_or_404(FieldAttendance, pk=pk)
    if request.method == 'POST':
        reason = request.POST.get('rejection_reason', '').strip()
        if reason:
            sheet.status = 'rejected'
            sheet.reviewed_by = request.user
            sheet.reviewed_at = timezone.now()
            sheet.rejection_reason = reason
            sheet.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'rejection_reason', 'updated_at'])
            messages.success(request, 'Attendance sheet rejected with feedback.')
        else:
            messages.error(request, 'A rejection reason is required.')
    return redirect('attendance_detail', pk=pk)


@login_required
def attendance_export_excel(request):
    sheets = filtered_attendance_sheets(request)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    scope = 'filtered' if request.GET else 'all'
    response['Content-Disposition'] = f'attachment; filename="aped-attendance-{scope}.xlsx"'
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Attendance sheets'
    sheet.append(['Activity', 'Project', 'Activity date', 'District', 'County', 'Sub-county', 'Parish', 'Village', 'Status', 'Participant', 'Sex', 'Title / role', 'Contact', 'Initials'])
    for attendance in sheets:
        participants = list(attendance.participants.all())
        rows = participants or [None]
        for participant in rows:
            sheet.append([
                str(attendance.activity or 'Field activity'),
                attendance.activity.project.name if attendance.activity and attendance.activity.project else '',
                str(attendance.activity_date), attendance.district, attendance.county,
                attendance.sub_county, attendance.parish, attendance.village,
                attendance.get_status_display(), participant.name if participant else '',
                participant.get_sex_display() if participant else '', participant.title_role if participant else '',
                participant.contact if participant else '', participant.signature if participant else '',
            ])
    for column in sheet.columns:
        sheet.column_dimensions[column[0].column_letter].width = min(max(max(len(str(cell.value or '')) for cell in column) + 2, 14), 35)
    workbook.save(response)
    return response


@login_required
def attendance_export_pdf(request):
    sheets = filtered_attendance_sheets(request)
    response = HttpResponse(content_type='application/pdf')
    scope = 'filtered' if request.GET else 'all'
    response['Content-Disposition'] = f'attachment; filename="aped-attendance-{scope}.pdf"'
    document = SimpleDocTemplate(response, pagesize=landscape(A4), rightMargin=24, leftMargin=24, topMargin=28, bottomMargin=24)
    styles = getSampleStyleSheet()
    cell_style = styles['BodyText'].clone('AttendanceCell')
    cell_style.fontName = 'Helvetica'
    cell_style.fontSize = 7
    cell_style.leading = 8
    header_style = cell_style.clone('AttendanceHeader')
    header_style.fontName = 'Helvetica-Bold'
    header_style.textColor = colors.white
    story = [Paragraph('APED Attendance Register', styles['Title']), Spacer(1, 12)]
    data = [[Paragraph(value, header_style) for value in [
        'Activity', 'Date', 'Location', 'Status', 'Participant', 'Sex', 'Role', 'Contact', 'Initials'
    ]]]
    for attendance in sheets:
        participants = list(attendance.participants.all()) or [None]
        for participant in participants:
            data.append([Paragraph(str(value or ''), cell_style) for value in [
                attendance.activity or 'Field activity', str(attendance.activity_date),
                attendance.village or attendance.parish or attendance.sub_county or attendance.district,
                attendance.get_status_display(), participant.name if participant else '',
                participant.get_sex_display() if participant else '', participant.title_role if participant else '',
                participant.contact if participant else '', participant.signature if participant else '',
            ]])
    table = Table(data, repeatRows=1, colWidths=[125, 60, 100, 75, 105, 55, 95, 100, 55])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#163b32')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7), ('GRID', (0, 0), (-1, -1), .35, colors.HexColor('#d7dfdb')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f2f6f3')]),
    ]))
    story.append(table)
    document.build(story)
    return response
