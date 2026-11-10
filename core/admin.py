from django.contrib import admin
from .models import Activity, FieldAttendance, FieldAttendancePart, Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'location', 'start_date', 'end_date', 'is_active')
    search_fields = ('code', 'name', 'location')
    list_filter = ('is_active',)


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('activity_name', 'project', 'village', 'activity_date', 'facilitator')
    search_fields = ('activity_name', 'village', 'facilitator', 'project__name')
    list_filter = ('project', 'activity_date')


class FieldAttendancePartInline(admin.TabularInline):
    model = FieldAttendancePart
    extra = 0


@admin.register(FieldAttendance)
class FieldAttendanceAdmin(admin.ModelAdmin):
    list_display = ('activity', 'activity_date', 'district', 'village', 'status', 'submitted_by')
    list_filter = ('status', 'activity_date', 'district')
    search_fields = ('district', 'county', 'sub_county', 'parish', 'village', 'activity__activity_name')
    inlines = [FieldAttendancePartInline]


@admin.register(FieldAttendancePart)
class FieldAttendancePartAdmin(admin.ModelAdmin):
    list_display = ('name', 'attendance', 'sex', 'title_role', 'contact')
    search_fields = ('name', 'contact', 'attendance__district', 'attendance__activity__activity_name')
    list_filter = ('sex',)
