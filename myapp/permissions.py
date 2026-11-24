from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect


def roles_required(*allowed_roles):
    """Restrict a view to authenticated users whose role_code is in allowed_roles."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())

            role_code = getattr(getattr(request.user, "role", None), "role_code", None)
            if request.user.is_superuser or role_code in allowed_roles:
                return view_func(request, *args, **kwargs)

            messages.error(request, "You do not have permission to perform this action.")
            return redirect("dashboard")

        return _wrapped_view

    return decorator


def can_access_facility(user, hospital_id):
    """Enforce strict facility scoping for branch officers while allowing network-wide roles."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True

    role_code = getattr(getattr(user, "role", None), "role_code", None)
    if role_code == "ROLE_BRANCH_OFFICER":
        return user.hospital_id is not None and user.hospital_id == hospital_id

    return role_code in {"ROLE_ADMIN", "ROLE_HOSPITAL_ADMIN", "ROLE_WAREHOUSE"}