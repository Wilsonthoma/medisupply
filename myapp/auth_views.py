from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import LoginForm
from .models import AuditLog, Hospital, PasswordChangeRequest

User = get_user_model()


def _get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    next_url = request.POST.get("next") or request.GET.get("next") or ""
    form = LoginForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data["username"]
        password = form.cleaned_data["password"]
        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_active:
            login(request, user)
            user.save(update_fields=["updated_at"])

            AuditLog.objects.create(
                user=user,
                hospital=user.hospital,
                action="USER_LOGIN",
                entity_name="User",
                entity_id=str(user.pk),
                description=f"User '{user.username}' signed in.",
                ip_address=_get_client_ip(request),
            )

            if next_url and url_has_allowed_host_and_scheme(
                url=next_url, allowed_hosts={request.get_host()}
            ):
                return redirect(next_url)
            return redirect("dashboard")

        messages.error(request, "Invalid username or password, or inactive account.")

    return render(
        request,
        "myapp/auth/login.html",
        {
            "form": form,
            "next": next_url,
            "facilities": Hospital.objects.order_by("name"),
        },
    )


@require_POST
def request_password_change_view(request):
    username = request.POST.get("username", "").strip()
    email = request.POST.get("email", "").strip()
    facility_id = request.POST.get("facility_id", "").strip()
    notes = request.POST.get("notes", "").strip()

    if not username or not email or not notes:
        messages.error(
            request,
            "Please provide your username, contact email, and reason for the password change.",
        )
        form = LoginForm()
        return render(
            request,
            "myapp/auth/login.html",
            {
                "form": form,
                "facilities": Hospital.objects.order_by("name"),
                "support_form_open": True,
                "support_data": {
                    "username": username,
                    "email": email,
                    "facility_id": facility_id,
                    "notes": notes,
                },
            },
        )

    facility = (
        Hospital.objects.filter(pk=facility_id).first()
        if facility_id.isdigit()
        else None
    )

    req_obj = PasswordChangeRequest.objects.create(
        username=username,
        email=email,
        facility=facility,
        notes=notes,
    )

    matched_user = User.objects.filter(username__iexact=username).first()
    if matched_user:
        AuditLog.objects.create(
            user=matched_user,
            hospital=facility or matched_user.hospital,
            action="PASSWORD_RESET_REQUEST",
            entity_name="PasswordChangeRequest",
            entity_id=str(req_obj.pk),
            description=f"Password change requested for '{username}' ({email}).",
            ip_address=_get_client_ip(request),
        )

    messages.success(
        request,
        "Your password change request has been submitted to the administrator.",
    )
    return redirect("login")


@login_required
@require_POST
def logout_view(request):
    user = request.user
    AuditLog.objects.create(
        user=user,
        hospital=user.hospital,
        action="USER_LOGOUT",
        entity_name="User",
        entity_id=str(user.pk),
        description=f"User '{user.username}' signed out.",
        ip_address=_get_client_ip(request),
    )
    logout(request)
    messages.info(request, "You have signed out.")
    return redirect("login")