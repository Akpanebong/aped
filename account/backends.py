from django.contrib.auth import get_user_model
from django.db.models import Q


class StaffIdentifierBackend:
    """Authenticate with username, immutable staff ID, email address or phone."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = (username or kwargs.get("identifier") or "").strip()
        if not identifier or not password:
            return None
        User = get_user_model()
        user = User.objects.filter(
            Q(username__iexact=identifier)
            | Q(email__iexact=identifier)
            | Q(staff_id__iexact=identifier)
            | Q(phone=identifier)
        ).first()
        if user and user.check_password(password) and user.is_active:
            return user
        return None

    def get_user(self, user_id):
        User = get_user_model()
        return User.objects.filter(pk=user_id).first()
