from django.conf import settings
from django.db import models


def initials_from_name(value):
    words = [word for word in (value or '').strip().split() if word]
    return ''.join(word[0] for word in words[:3]).upper()


class Project(models.Model):
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=180, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.code} · {self.name}'


class Activity(models.Model):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name='activities')
    activity_name = models.CharField(max_length=180)
    village = models.CharField(max_length=180)
    activity_date = models.DateField()
    facilitator = models.CharField(max_length=180, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='core_activities')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-activity_date', '-created_at']

    def __str__(self):
        return f'{self.activity_name} · {self.village}'


class FieldAttendance(models.Model):
    """Attendance-sheet header, following the KAPDA field attendance structure."""
    district = models.CharField(max_length=120)
    county = models.CharField(max_length=120, blank=True)
    sub_county = models.CharField(max_length=120, blank=True)
    parish = models.CharField(max_length=120, blank=True)
    village = models.CharField(max_length=120, blank=True)
    activity_date = models.DateField()
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, null=True, blank=True, related_name='field_attendance_sheets')
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='submitted_attendance_sheets')
    submitted_title = models.CharField(max_length=160, blank=True)
    submitted_signature = models.CharField(max_length=240, blank=True)
    submitted_date = models.DateField(null=True, blank=True)
    approved_by = models.CharField(max_length=180, blank=True)
    approved_title = models.CharField(max_length=160, blank=True)
    approved_signature = models.CharField(max_length=240, blank=True)
    approved_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[('pending', 'Pending approval'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', db_index=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_attendance_sheets')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-activity_date', '-created_at']

    def __str__(self):
        return f'{self.activity or "Field activity"} - {self.activity_date}'


class FieldAttendancePart(models.Model):
    attendance = models.ForeignKey(FieldAttendance, on_delete=models.CASCADE, related_name='participants')
    name = models.CharField(max_length=180)
    sex = models.CharField(max_length=1, choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other / not stated')])
    title_role = models.CharField(max_length=160, blank=True)
    contact = models.CharField(max_length=120, blank=True, help_text='Email or telephone number')
    signature = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['pk']

    def save(self, *args, **kwargs):
        self.signature = initials_from_name(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


FieldAttendanceParticipant = FieldAttendancePart


class Attendance(Activity):
    GENDER_CHOICES = [('male', 'Male'), ('female', 'Female'), ('other', 'Other')]
    AGE_GROUP_CHOICES = [('18-35', '18-35'), ('35+', '35+')]
    YES_NO_CHOICES = [('yes', 'Yes'), ('no', 'No')]

    name = models.CharField(max_length=180)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    age_group = models.CharField(max_length=10, choices=AGE_GROUP_CHOICES)
    disability_status = models.CharField(max_length=5, choices=YES_NO_CHOICES, default='no')
    disability_type = models.CharField(max_length=120, blank=True)
    contact = models.CharField(max_length=80, blank=True)
    signature = models.CharField(max_length=180, blank=True, help_text='Signature, consent or attendance confirmation')
    attendance_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-activity_date', 'name']

    def __str__(self):
        return f'{self.name} · {self.activity_name}'
