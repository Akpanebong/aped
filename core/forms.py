from django import forms
from django.forms import inlineformset_factory
from .models import Activity, FieldAttendance, FieldAttendanceParticipant, Project


class APEDDateFormMixin:
    def _style(self):
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class ProjectForm(APEDDateFormMixin, forms.ModelForm):
    class Meta:
        model = Project
        fields = ['code', 'name', 'description', 'location', 'start_date', 'end_date', 'is_active']
        widgets = {'description': forms.Textarea(attrs={'rows': 3}), 'start_date': forms.DateInput(attrs={'type': 'date'}), 'end_date': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class ActivityForm(APEDDateFormMixin, forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['project', 'activity_name', 'village', 'activity_date', 'facilitator', 'notes']
        widgets = {'activity_date': forms.DateInput(attrs={'type': 'date'}), 'notes': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class FieldAttendanceForm(APEDDateFormMixin, forms.ModelForm):
    class Meta:
        model = FieldAttendance
        fields = ['district', 'county', 'sub_county', 'parish', 'village', 'activity_date', 'activity']
        widgets = {'activity_date': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()
        self.fields['activity'].queryset = Activity.objects.select_related('project').order_by('-activity_date', 'activity_name')
        self.fields['activity'].required = False


class FieldAttendanceParticipantForm(APEDDateFormMixin, forms.ModelForm):
    class Meta:
        model = FieldAttendanceParticipant
        fields = ['name', 'sex', 'title_role', 'contact', 'signature']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Participant name'}),
            'title_role': forms.TextInput(attrs={'placeholder': 'Title or role'}),
            'contact': forms.TextInput(attrs={'placeholder': 'Email or telephone'}),
            'signature': forms.TextInput(attrs={'placeholder': 'Initials', 'readonly': True, 'data-auto-initials': 'true'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


FieldAttendanceParticipantFormSet = inlineformset_factory(
    FieldAttendance,
    FieldAttendanceParticipant,
    form=FieldAttendanceParticipantForm,
    extra=1,
    max_num=25,
    can_delete=True,
)
