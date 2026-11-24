from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    CommodityForm,
    ReorderLevelForm,
    SupplierReceiptForm,
    SupplierReceiptItemFormSet,
)
from .models import (
    AuditLog,
    Commodity,
    CommodityCategory,
    Hospital,
    Inventory,
    InventoryBatch,
)
from .permissions import can_access_facility, roles_required
from .services import receive_supplier_shipment


@login_required
def inventory_list_view(request):
    user = request.user
    qs = Inventory.objects.select_related("hospital", "commodity", "commodity__category")

    if user.role and user.role.role_code == "ROLE_BRANCH_OFFICER" and user.hospital_id:
        qs = qs.filter(hospital_id=user.hospital_id)
    else:
        facility_id = request.GET.get("facility")
        if facility_id:
            qs = qs.filter(hospital_id=facility_id)

    category_id = request.GET.get("category")
    if category_id:
        qs = qs.filter(commodity__category_id=category_id)

    if request.GET.get("low_stock") == "1":
        qs = qs.filter(quantity_on_hand__lte=F("reorder_level"))

    hospitals = Hospital.objects.filter(is_active=True).order_by("name")
    categories = CommodityCategory.objects.filter(is_active=True).order_by("name")

    return render(
        request,
        "myapp/inventory/main_hospital_inventory.html",
        {
            "inventory_items": qs.order_by("hospital__name", "commodity__name"),
            "hospitals": hospitals,
            "categories": categories,
            "selected_facility": request.GET.get("facility", ""),
            "selected_category": category_id or "",
            "low_stock_only": request.GET.get("low_stock") == "1",
        },
    )


@login_required
@roles_required("ROLE_ADMIN", "ROLE_HOSPITAL_ADMIN", "ROLE_WAREHOUSE")
@require_POST
def update_reorder_level_view(request, inventory_id):
    inv = get_object_or_404(Inventory, pk=inventory_id)
    if not can_access_facility(request.user, inv.hospital_id):
        messages.error(request, "You do not have access to this facility's inventory.")
        return redirect("inventory_list")

    form = ReorderLevelForm(request.POST, instance=inv)
    if form.is_valid():
        with transaction.atomic():
            locked_inv = Inventory.objects.select_for_update().get(pk=inv.pk)
            old_level = locked_inv.reorder_level
            locked_inv.reorder_level = form.cleaned_data["reorder_level"]
            locked_inv.save(update_fields=["reorder_level", "last_updated_at"])

            AuditLog.objects.create(
                user=request.user,
                hospital=locked_inv.hospital,
                action="UPDATE_REORDER_LEVEL",
                entity_name="Inventory",
                entity_id=str(locked_inv.pk),
                description=(
                    f"Updated reorder level for {locked_inv.commodity.name} at "
                    f"{locked_inv.hospital.name} from {old_level} to {locked_inv.reorder_level}."
                ),
            )
        messages.success(request, "Reorder level updated.")
    else:
        messages.error(request, "Invalid reorder level value.")

    return redirect("inventory_list")


@login_required
@roles_required("ROLE_ADMIN", "ROLE_HOSPITAL_ADMIN", "ROLE_WAREHOUSE")
def receive_shipment_view(request):
    header_form = SupplierReceiptForm(request.POST or None, user=request.user)
    item_formset = SupplierReceiptItemFormSet(request.POST or None)

    if request.method == "POST" and header_form.is_valid() and item_formset.is_valid():
        items_payload = []
        for item_form in item_formset:
            if not item_form.cleaned_data or item_form.cleaned_data.get("DELETE"):
                continue
            items_payload.append(item_form.cleaned_data)

        if not items_payload:
            messages.error(request, "Add at least one commodity item to record a shipment.")
        else:
            try:
                receipt = receive_supplier_shipment(
                    hospital=header_form.cleaned_data["receiving_hospital"],
                    supplier_name=header_form.cleaned_data["supplier_name"],
                    receipt_date=header_form.cleaned_data["receipt_date"],
                    delivery_note_ref=header_form.cleaned_data.get("delivery_note_ref", ""),
                    remarks=header_form.cleaned_data.get("remarks", ""),
                    items=items_payload,
                    performed_by=request.user,
                )
                messages.success(
                    request,
                    f"Supplier shipment recorded under receipt {receipt.receipt_number}.",
                )
                return redirect("inventory_list")
            except Exception as exc:
                messages.error(request, str(exc))

    return render(
        request,
        "myapp/inventory/warehouse_inventory.html",
        {
            "header_form": header_form,
            "item_formset": item_formset,
        },
    )


@login_required
def batch_list_view(request):
    user = request.user
    today = timezone.localdate()
    qs = InventoryBatch.objects.select_related("hospital", "commodity").order_by(
        "expiry_date", "batch_id"
    )

    if user.role and user.role.role_code == "ROLE_BRANCH_OFFICER" and user.hospital_id:
        qs = qs.filter(hospital_id=user.hospital_id)

    status_filter = request.GET.get("status")
    if status_filter:
        qs = qs.filter(batch_status=status_filter)

    expiring_days = request.GET.get("expiring_within")
    if expiring_days and expiring_days.isdigit():
        cutoff = today + timedelta(days=int(expiring_days))
        qs = qs.filter(expiry_date__gte=today, expiry_date__lte=cutoff)

    return render(
        request,
        "myapp/inventory/branch_inventory.html",
        {
            "batches": qs,
            "today": today,
            "status_filter": status_filter or "",
            "expiring_within": expiring_days or "",
        },
    )


@login_required
def commodity_list_view(request):
    commodities = Commodity.objects.select_related("category").order_by("name")
    return render(
        request,
        "myapp/inventory/commodities.html",
        {"commodities": commodities},
    )


@login_required
@roles_required("ROLE_ADMIN", "ROLE_HOSPITAL_ADMIN", "ROLE_WAREHOUSE")
def create_commodity_view(request):
    form = CommodityForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        commodity = form.save()
        AuditLog.objects.create(
            user=request.user,
            hospital=request.user.hospital,
            action="CREATE_COMMODITY",
            entity_name="Commodity",
            entity_id=str(commodity.pk),
            description=f"Created commodity '{commodity.name}' ({commodity.commodity_code}).",
        )
        messages.success(request, f"Commodity '{commodity.name}' added.")
        return redirect("commodity_list")

    return render(
        request,
        "myapp/inventory/commodities.html",
        {
            "form": form,
            "commodities": Commodity.objects.select_related("category").order_by("name"),
        },
    )