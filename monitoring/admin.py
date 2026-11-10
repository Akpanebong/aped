from django.contrib import admin
from .models import MonitoringForm, MonitoringRecord, FollowUpAction
@admin.register(MonitoringForm)
class MonitoringFormAdmin(admin.ModelAdmin):
    list_display=('name','category','is_active','created_at')
    list_filter=('category','is_active'); search_fields=('name','description'); prepopulated_fields={}
@admin.register(MonitoringRecord)
class MonitoringRecordAdmin(admin.ModelAdmin):
    list_display=('reference','form','visit_date','location','district','status','created_by')
    list_filter=('form','status','visit_date','district'); search_fields=('reference','location','district','group_or_beneficiary')
@admin.register(FollowUpAction)
class FollowUpActionAdmin(admin.ModelAdmin):
    list_display=('action','record','assigned_to','due_date','status')
    list_filter=('status','due_date'); search_fields=('action','record__reference')
