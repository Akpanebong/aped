from django.conf import settings
from django.db import models
from django.utils.text import slugify

class MonitoringForm(models.Model):
    CATEGORY_CHOICES=[('agriculture','Agriculture'),('livestock','Livestock'),('apiary','Beekeeping / Apiary'),('peacebuilding','Peacebuilding'),('attendance','Attendance'),('other','Other')]
    name=models.CharField(max_length=180)
    slug=models.SlugField(max_length=200,unique=True)
    category=models.CharField(max_length=30,choices=CATEGORY_CHOICES,default='other')
    description=models.TextField(blank=True)
    schema=models.JSONField(default=list,help_text='Ordered sections, with field definitions. Seeded from APED workbook.')
    is_active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['category','name']
    def __str__(self): return self.name


class MonitoringRecord(models.Model):
    form=models.ForeignKey(MonitoringForm,on_delete=models.PROTECT,related_name='records')
    project=models.ForeignKey('core.Project',on_delete=models.SET_NULL,null=True,blank=True,related_name='monitoring_records')
    activity=models.ForeignKey('core.Activity',on_delete=models.SET_NULL,null=True,blank=True,related_name='monitoring_records')
    reference=models.CharField(max_length=30,unique=True,blank=True)
    visit_date=models.DateField()
    project_name=models.CharField(max_length=180,blank=True)
    location=models.CharField(max_length=180,blank=True)
    district=models.CharField(max_length=120,blank=True)
    group_or_beneficiary=models.CharField(max_length=180,blank=True)
    status=models.CharField(max_length=20,choices=[('draft','Draft'),('submitted','Submitted'),('reviewed','Reviewed')],default='submitted')
    data=models.JSONField(default=dict,blank=True)
    observations=models.TextField(blank=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,related_name='aped_monitoring_records')
    updated_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='aped_updated_records')
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=['-visit_date','-created_at']
    def save(self,*args,**kwargs):
        if not self.reference:
            from django.utils import timezone
            self.reference=f"APED-{timezone.now():%y%m%d}-{__import__('uuid').uuid4().hex[:6].upper()}"
        super().save(*args,**kwargs)
    def get_fields(self):
        return [('Monitoring tool', self.form.name), ('Project', self.project.name if self.project else self.project_name), ('Activity', self.activity.activity_name if self.activity else ''), ('Location', self.location), ('District / region', self.district), ('Group / beneficiary', self.group_or_beneficiary), ('Visit date', self.visit_date), ('Status', self.get_status_display())]
    def __str__(self): return f'{self.reference} — {self.form.name}'


class FollowUpAction(models.Model):
    STATUS=[('open','Open'),('in_progress','In progress'),('done','Completed'),('cancelled','Cancelled')]
    record=models.ForeignKey(MonitoringRecord,on_delete=models.CASCADE,related_name='followups')
    action=models.CharField(max_length=240)
    assigned_to=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)
    due_date=models.DateField(null=True,blank=True)
    status=models.CharField(max_length=20,choices=STATUS,default='open')
    notes=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    completed_at=models.DateField(null=True,blank=True)
    class Meta: ordering=['due_date','-created_at']
    def __str__(self): return self.action
