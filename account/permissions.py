from functools import wraps

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from .models import StaffProfile


def profile_for(user):
    if not user.is_authenticated:
        return None
    return sync_role_permissions(user)


def sync_role_permissions(user):
    """Keep Django admin access aligned with the APED role on the profile."""
    if user.role == StaffProfile.Role.SYSTEM_ADMIN or user.is_superuser:
        group, _ = Group.objects.get_or_create(name="System Administrators")
        if not group.permissions.exists():
            group.permissions.set(Permission.objects.all())
        user.groups.add(group)
        if not user.is_staff:
            get_user_model().objects.filter(pk=user.pk).update(is_staff=True)
    else:
        user.groups.remove(*Group.objects.filter(name="System Administrators"))
        if user.is_staff and not user.is_superuser:
            get_user_model().objects.filter(pk=user.pk).update(is_staff=False)
    return user


def is_system_admin(user):
    return bool(user.is_authenticated and (user.is_superuser or profile_for(user).role == StaffProfile.Role.SYSTEM_ADMIN))


def can_write(user):
    return bool(user.is_authenticated and (is_system_admin(user) or profile_for(user).role != StaffProfile.Role.READ_ONLY))


def can_delete(user):
    return is_system_admin(user)


def role_required(*allowed_roles):
    """Require authentication and one of the supplied APED roles."""
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path(), "login")
            if not request.user.is_active or (not request.user.is_superuser and request.user.role not in allowed_roles):
                raise PermissionDenied("Your staff role does not allow this action.")
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


def create_required(view):
    return role_required(StaffProfile.Role.SYSTEM_ADMIN, StaffProfile.Role.PROGRAMME_MANAGER, StaffProfile.Role.DATA_ENTRY)(view)


def edit_required(view):
    return role_required(StaffProfile.Role.SYSTEM_ADMIN, StaffProfile.Role.PROGRAMME_MANAGER)(view)


def approval_required(view):
    return role_required(StaffProfile.Role.SYSTEM_ADMIN, StaffProfile.Role.PROGRAMME_MANAGER)(view)


def system_admin_required(view):
    return role_required(StaffProfile.Role.SYSTEM_ADMIN)(view)


def staff_admin_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), "login")
        if not is_system_admin(request.user):
            raise PermissionDenied("You must be a system administrator to perform this action.")
        return view(request, *args, **kwargs)

    return wrapper
