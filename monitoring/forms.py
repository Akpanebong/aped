import json
from django import forms
from django.utils.text import slugify
from .models import MonitoringForm, MonitoringRecord, FollowUpAction
from .linked_records import LINKED_RECORD_SOURCES


class MonitoringFormDefinitionForm(forms.ModelForm):
    schema = forms.JSONField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 18, 'class': 'font-monospace'}),
        help_text='Enter a JSON array of sections. Each section should contain title, key, repeatable and fields.',
    )

    class Meta:
        model = MonitoringForm
        fields = ['name', 'slug', 'category', 'description', 'schema', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
        self.fields['is_active'].widget.attrs['class'] = 'form-check-input'
        self.fields['slug'].required = False
        self.fields['slug'].help_text = 'Optional URL-safe identifier. It is generated from the name when left blank.'
        self.fields['schema'].initial = json.dumps(self.instance.schema or [], indent=2) if self.instance.pk else '[]'

    def clean_slug(self):
        return slugify(self.cleaned_data.get('slug') or self.cleaned_data.get('name', ''))

    def clean_schema(self):
        schema = self.cleaned_data.get('schema') or []
        if not isinstance(schema, list):
            raise forms.ValidationError('Schema must be a JSON array of sections.')
        for index, section in enumerate(schema, 1):
            if not isinstance(section, dict) or not section.get('title') or not isinstance(section.get('fields', []), list):
                raise forms.ValidationError(f'Section {index} must have a title and a fields array.')
            for field_index, field in enumerate(section.get('fields', []), 1):
                if not isinstance(field, dict) or not field.get('name') or not field.get('label'):
                    raise forms.ValidationError(f'Section {index}, field {field_index} must have a name and label.')
                if 'required' in field and not isinstance(field['required'], bool):
                    raise forms.ValidationError(f'Section {index}, field {field_index} required must be true or false.')
                if field.get('type') == 'linked_record' and field.get('linked_model') not in LINKED_RECORD_SOURCES:
                    raise forms.ValidationError(f'Section {index}, field {field_index} must select a valid linked record source.')
        return schema

class MonitoringRecordForm(forms.ModelForm):
    class Meta:
        model=MonitoringRecord
        fields=['form','project','activity','visit_date','project_name','location','district','group_or_beneficiary','status','observations']
        widgets={'visit_date':forms.DateInput(attrs={'type':'date'}),'observations':forms.Textarea(attrs={'rows':3})}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class':'form-control'})
        self.fields['form'].queryset=self.fields['form'].queryset.filter(is_active=True)
        self.fields['project'].required = False
        self.fields['activity'].required = False
        self.fields['project_name'].label = 'Legacy project label'
        self.fields['project_name'].required = False

class FollowUpActionForm(forms.ModelForm):
    class Meta:
        model=FollowUpAction
        fields=['action','assigned_to','due_date','status','notes','completed_at']
        widgets={'due_date':forms.DateInput(attrs={'type':'date'}),'completed_at':forms.DateInput(attrs={'type':'date'}),'notes':forms.Textarea(attrs={'rows':2})}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for field in self.fields.values(): field.widget.attrs.update({'class':'form-control'})
