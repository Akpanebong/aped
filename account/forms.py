from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserChangeForm

from .models import StaffProfile


class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget_class = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            if isinstance(field.widget, forms.CheckboxInput):
                widget_class = "form-check-input"
            field.widget.attrs.setdefault("class", widget_class)


class StaffCreateForm(StyledFormMixin, forms.ModelForm):
    role = forms.ChoiceField(choices=StaffProfile.Role.choices)
    job_title = forms.CharField(required=False)
    department = forms.CharField(required=False)
    phone = forms.CharField(required=False)
    location = forms.CharField(required=False)

    class Meta:
        model = StaffProfile
        fields = ("first_name", "last_name", "email", "role", "job_title", "department", "phone", "location")
        widgets = {"email": forms.EmailInput(attrs={"required": True})}

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if not email:
            raise forms.ValidationError("An email address is required so onboarding credentials can be sent.")
        if StaffProfile.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A staff account already uses this email address.")
        return email


class StaffUpdateForm(StyledFormMixin, forms.ModelForm):
    role = forms.ChoiceField(choices=StaffProfile.Role.choices)
    job_title = forms.CharField(required=False)
    department = forms.CharField(required=False)
    phone = forms.CharField(required=False)
    location = forms.CharField(required=False)

    class Meta:
        model = StaffProfile
        fields = ("username", "first_name", "last_name", "email", "is_active", "role", "job_title", "department", "phone", "location")


class MyProfileForm(StyledFormMixin, forms.ModelForm):
    job_title = forms.CharField(required=False)
    department = forms.CharField(required=False)
    phone = forms.CharField(required=False)
    location = forms.CharField(required=False)

    class Meta:
        model = StaffProfile
        fields = ("username", "first_name", "last_name", "email", "job_title", "department", "phone", "location")


class IdentifierAuthenticationForm(StyledFormMixin, AuthenticationForm):
    username = forms.CharField(label="Username, staff ID, email or phone", widget=forms.TextInput(attrs={"autocomplete": "username", "autofocus": True}))


class AdminUserChangeForm(UserChangeForm):
    class Meta:
        model = StaffProfile
        fields = "__all__"
