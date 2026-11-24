from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import F, Sum
from django.shortcuts import render
from django.utils import timezone

from .models import (
    BranchRequest,
    Delivery,
    Hospital,
    Inventory,
    InventoryBatch,
    Notification,
    StockTransfer,
    User,
)
from .permissions import roles_required


@login_required
def dashboard_view(request):
    user = request.user
    today = timezone.localdate()
    soon_cutoff = today + timedelta(days=30)

    inventory_qs = Inventory.objects.select_related("hospital", "commodity")
    batches_qs = InventoryBatch.objects.select_related("hospital", "commodity")
    requests_qs = BranchRequest.objects.select_related(
        "branch_hospital", "target_hospital", "requested_by"
    )
    transfers_qs = StockTransfer.objects.select_related(
        "source_hospital", "destination_hospital", "dispatched_by"
    )
    deliveries_qs = Delivery.objects.select_related("transfer", "receiving_hospital")

    is_branch_scoped = (
        user.role
        and user.role.role_code == "ROLE_BRANCH_OFFICER"
        and user.hospital_id is not None
    )

    if is_branch_scoped:
        inventory_qs = inventory_qs.filter(hospital_id=user.hospital_id)
        batches_qs = batches_qs.filter(hospital_id=user.hospital_id)
        requests_qs = requests_qs.filter(branch_hospital_id=user.hospital_id)
        transfers_qs = transfers_qs.filter(destination_hospital_id=user.hospital_id)
        deliveries_qs = deliveries_qs.filter(receiving_hospital_id=user.hospital_id)

    total_stock_units = (
        inventory_qs.aggregate(total=Sum("quantity_on_hand")).get("total") or 0
    )
    low_stock_count = inventory_qs.filter(
        quantity_on_hand__lte=F("reorder_level")
    ).count()
    expiring_soon_count = batches_qs.filter(
        quantity_on_hand__gt=0,
        expiry_date__gte=today,
        expiry_date__lte=soon_cutoff,
    ).exclude(batch_status__in=["EXPIRED", "QUARANTINED", "DEPLETED"]).count()
    expired_stock_count = batches_qs.filter(
        quantity_on_hand__gt=0,
        expiry_date__lt=today,
    ).count()
    pending_requests_count = requests_qs.filter(
        status__in=["PENDING", "UNDER_REVIEW"]
    ).count()
    active_transfers_count = transfers_qs.filter(
        status__in=["PREPARING", "DISPATCHED", "IN_TRANSIT", "DELIVERED"]
    ).count()
    awaiting_deliveries_count = deliveries_qs.filter(
        status="AWAITING_CONFIRMATION"
    ).count()

    unread_notifications = Notification.objects.filter(
        recipient=user, is_read=False
    ).order_by("-created_at")[:8]

    facilities = Hospital.objects.select_related("parent_hospital").filter(
        is_active=True
    ).order_by("facility_type", "name")
    if is_branch_scoped:
        facilities = facilities.filter(pk=user.hospital_id)

    context = {
        "total_stock_units": total_stock_units,
        "low_stock_count": low_stock_count,
        "expiring_soon_count": expiring_soon_count,
        "expired_stock_count": expired_stock_count,
        "pending_requests_count": pending_requests_count,
        "active_transfers_count": active_transfers_count,
        "awaiting_deliveries_count": awaiting_deliveries_count,
        "recent_requests": requests_qs.order_by("-created_at")[:8],
        "recent_transfers": transfers_qs.order_by("-created_at")[:8],
        "unread_notifications": unread_notifications,
        "facilities": facilities,
        "today": today,
    }

    role_code = user.role.role_code if user.role else ""
    if role_code == "ROLE_ADMIN":
        template_name = "myapp/dashboards/admin_dashboard.html"
    elif role_code == "ROLE_HOSPITAL_ADMIN":
        template_name = "myapp/dashboards/hospital_admin_dashboard.html"
    elif role_code == "ROLE_WAREHOUSE":
        template_name = "myapp/dashboards/warehouse_dashboard.html"
    else:
        template_name = "myapp/dashboards/branch_dashboard.html"

    return render(request, template_name, context)


@login_required
@roles_required("ROLE_ADMIN")
def users_hospitals_view(request):
    hospitals = Hospital.objects.select_related("parent_hospital").order_by(
        "facility_type", "name"
    )
    users = User.objects.select_related("role", "hospital").order_by("username")
    return render(
        request,
        "myapp/admin_mgmt/users_hospitals.html",
        {
            "hospitals": hospitals,
            "users": users,
        },
    )