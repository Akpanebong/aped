from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .forms import AdminUserChangeForm
from .models import StaffProfile


@admin.register(StaffProfile)
class StaffUserAdmin(UserAdmin):
    form = AdminUserChangeForm
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        ("APED staff profile", {"fields": ("staff_id", "role", "job_title", "department", "phone", "location")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("username", "password1", "password2", "email", "role")}),
    )
    filter_horizontal = ()
    list_display = ("username", "first_name", "last_name", "email", "staff_role", "is_active")
    list_filter = ("is_active", "is_superuser", "role")
    search_fields = ("username", "staff_id", "first_name", "last_name", "email", "department")

    @admin.display(description="Role")
    def staff_role(self, obj):
        return obj.role_label
