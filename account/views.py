import secrets
import string

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import MyProfileForm, StaffCreateForm, StaffUpdateForm
from .models import CustomUser
from .permissions import is_system_admin, staff_admin_required, sync_role_permissions


def generated_password(length=12):
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def send_onboarding_email(request, user, temporary_password):
    login_url = request.build_absolute_uri(reverse("login"))
    profile_url = request.build_absolute_uri(reverse("password_change"))
    message = f"""Hello {user.get_full_name() or user.username},

Your APED Monitoring staff account has been created.

Staff ID: {user.staff_id}
Username: {user.username}
Temporary password: {temporary_password}

Sign in here: {login_url}
After signing in, change your username and password from your profile: {profile_url}

Please keep these credentials private and change the temporary password immediately.
"""
    return send_mail("Your APED Monitoring account", message, None, [user.email], fail_silently=False)


@staff_admin_required
@login_required
def staff_list(request):
    staff_members = CustomUser.objects.exclude(username='j').order_by(
        "last_name",
        "first_name",
        "username",
    )

    summary = staff_members.aggregate(
        total=Count("pk"),
        active=Count("pk", filter=Q(is_active=True)),
        inactive=Count("pk", filter=Q(is_active=False)),
    )

    context = {
        "staff_members": staff_members,
        "total_count": summary["total"],
        "active_count": summary["active"],
        "inactive_count": summary["inactive"],
    }

    return render(request, "account/staff_list.html", context)


@staff_admin_required
def staff_create(request):
    form = StaffCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        temporary_password = generated_password()
        user = form.save(commit=False)
        user.username = f"pending-{secrets.token_hex(6)}"
        user.set_password(temporary_password)
        user.save()
        user.username = user.staff_id
        user.save(update_fields=["username"])
        user.is_staff = user.is_system_admin
        user.save(update_fields=["is_staff"])
        sync_role_permissions(user)
        try:
            send_onboarding_email(request, user, temporary_password)
            messages.success(request, f"Staff account {user.staff_id} created. Login credentials were sent to {user.email}.")
        except Exception:
            messages.warning(request, f"Staff account {user.staff_id} was created, but the onboarding email could not be sent. Configure SMTP and resend credentials securely.")
        return redirect("staff_detail", user.pk)
    return render(request, "account/staff_form.html", {"form": form, "page_title": "Create staff account"})


@staff_admin_required
def staff_detail(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    return render(request, "account/staff_detail.html", {"staff_member": user})


@staff_admin_required
def staff_update(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    form = StaffUpdateForm(request.POST or None, instance=user)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        user.is_staff = user.is_system_admin
        user.save(update_fields=["is_staff"])
        sync_role_permissions(user)
        messages.success(request, "Staff account updated.")
        return redirect("staff_detail", user.pk)
    return render(request, "account/staff_form.html", {"form": form, "page_title": "Update staff account", "staff_member": user})


@staff_admin_required
def staff_toggle_active(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    if request.method == "POST" and user != request.user:
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        messages.success(request, f"{user.get_username()} is now {'active' if user.is_active else 'inactive'}.")
    return redirect("staff_detail", user.pk)


@login_required
def my_profile(request):
    return render(request, "account/my_profile.html", {"staff_member": request.user, "profile": request.user, "is_system_admin": is_system_admin(request.user)})


@login_required
def my_profile_update(request):
    form = MyProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("my_profile")
    return render(request, "account/profile_form.html", {"form": form, "page_title": "Update my profile"})


@login_required
def password_change(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    for field in form.fields.values():
        field.widget.attrs["class"] = "form-control form-control-lg"
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Your password has been changed.")
        return redirect("my_profile")
    return render(request, "account/password_form.html", {"form": form})
