from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import LoginForm
from .models import AuditLog


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
            user.last_login_at = timezone.now()
            user.save(update_fields=["last_login_at", "updated_at"])

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
        },
    )


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