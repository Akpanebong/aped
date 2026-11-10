from django.core.exceptions import PermissionDenied

from .permissions import can_delete, can_write


class RoleEnforcementMiddleware:
    """Enforce write/delete rules even when a user bypasses the rendered UI."""

    exempt_prefixes = ("/accounts/login/", "/accounts/logout/", "/accounts/profile/", "/accounts/password/", "/admin/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and not request.path.startswith(self.exempt_prefixes):
            if request.user.is_authenticated:
                if not can_write(request.user):
                    raise PermissionDenied("Your role is read-only.")
                if (request.method == "DELETE" or "/delete/" in request.path or request.path.endswith("/delete")) and not can_delete(request.user):
                    raise PermissionDenied("Only a System Administrator can delete records.")
        return self.get_response(request)
