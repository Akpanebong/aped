from functools import wraps
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from account.permissions import can_write
from account.models import StaffProfile


def can_access_vsla(user):
    if not user.is_authenticated or not getattr(user, "is_active", True):
        return False
    return user.role in {
        StaffProfile.Role.SYSTEM_ADMIN,
        StaffProfile.Role.PROGRAMME_MANAGER,
        StaffProfile.Role.DATA_ENTRY,
        StaffProfile.Role.READ_ONLY,
    }


def vsla_write_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if not can_write(request.user):
            raise PermissionDenied("Your role is read-only.")
        return view_func(request, *args, **kwargs)
    return _wrapped


def vsla_access_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if not can_access_vsla(request.user):
            raise PermissionDenied("You do not have permission to access VSLA Management.")
        return view_func(request, *args, **kwargs)
    return _wrapped
