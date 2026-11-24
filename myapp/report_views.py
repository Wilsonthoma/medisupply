from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import AuditLog, Notification, StockMovement
from .permissions import roles_required


@login_required
def reports_analytics_view(request):
    user = request.user
    movements_qs = StockMovement.objects.select_related(
        "hospital", "commodity", "batch", "performed_by"
    )
    if user.role and user.role.role_code == "ROLE_BRANCH_OFFICER" and user.hospital_id:
        movements_qs = movements_qs.filter(hospital_id=user.hospital_id)

    movement_type = request.GET.get("movement_type")
    if movement_type:
        movements_qs = movements_qs.filter(movement_type=movement_type)

    return render(
        request,
        "myapp/reports/reports_analytics.html",
        {
            "movements": movements_qs.order_by("-created_at")[:100],
            "movement_types": StockMovement.MovementType.choices,
            "selected_movement_type": movement_type or "",
        },
    )


@login_required
def stock_movements_view(request):
    return reports_analytics_view(request)


@login_required
def notifications_view(request):
    user_notifications = Notification.objects.filter(
        recipient=request.user
    ).select_related("hospital").order_by("-created_at")
    return render(
        request,
        "myapp/reports/reports_analytics.html",
        {"notifications": user_notifications},
    )


@login_required
@require_POST
def mark_notification_read_view(request, notification_id):
    notif = get_object_or_404(
        Notification, pk=notification_id, recipient=request.user
    )
    if not notif.is_read:
        notif.is_read = True
        notif.read_at = timezone.now()
        notif.save(update_fields=["is_read", "read_at"])
        messages.success(request, "Notification marked as read.")
    return redirect("dashboard")


@login_required
@roles_required("ROLE_ADMIN", "ROLE_HOSPITAL_ADMIN")
def audit_logs_view(request):
    logs = AuditLog.objects.select_related("user", "hospital").order_by("-created_at")[:200]
    return render(
        request,
        "myapp/reports/reports_analytics.html",
        {"audit_logs": logs},
    )