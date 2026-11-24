from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DeliveryConfirmForm, StockTransferDispatchForm
from .models import BranchRequest, Delivery, StockTransfer
from .permissions import can_access_facility, roles_required
from .services import confirm_delivery, dispatch_stock_transfer


@login_required
def transfers_deliveries_view(request):
    user = request.user
    transfers_qs = StockTransfer.objects.select_related(
        "source_hospital", "destination_hospital", "dispatched_by", "request"
    ).order_by("-created_at")
    deliveries_qs = Delivery.objects.select_related(
        "transfer", "receiving_hospital", "confirmed_by"
    ).prefetch_related("items__commodity", "items__batch").order_by("-created_at")

    if user.role and user.role.role_code == "ROLE_BRANCH_OFFICER" and user.hospital_id:
        transfers_qs = transfers_qs.filter(destination_hospital_id=user.hospital_id)
        deliveries_qs = deliveries_qs.filter(receiving_hospital_id=user.hospital_id)

    return render(
        request,
        "myapp/distribution/transfers_deliveries.html",
        {
            "transfers": transfers_qs,
            "deliveries": deliveries_qs,
        },
    )


@login_required
@roles_required("ROLE_ADMIN", "ROLE_HOSPITAL_ADMIN", "ROLE_WAREHOUSE")
def dispatch_transfer_view(request):
    approved_requests = BranchRequest.objects.filter(
        status__in=["APPROVED", "PARTIALLY_APPROVED"]
    ).select_related("branch_hospital", "target_hospital")
    form = StockTransferDispatchForm(request.POST or None, user=request.user)

    if request.method == "POST" and form.is_valid():
        try:
            transfer = dispatch_stock_transfer(
                source_hospital=form.cleaned_data["source_hospital"],
                destination_hospital=form.cleaned_data["destination_hospital"],
                dispatch_date=form.cleaned_data["dispatch_date"],
                branch_request=form.cleaned_data.get("branch_request"),
                notes=form.cleaned_data.get("notes", ""),
                dispatched_by=request.user,
            )
            messages.success(
                request,
                f"Stock transfer {transfer.transfer_number} dispatched via FEFO.",
            )
            return redirect("transfers_deliveries")
        except Exception as exc:
            messages.error(request, str(exc))

    return render(
        request,
        "myapp/distribution/transfers_deliveries.html",
        {
            "dispatch_form": form,
            "approved_requests": approved_requests,
            "transfers": StockTransfer.objects.select_related(
                "source_hospital", "destination_hospital"
            ).order_by("-created_at")[:15],
            "deliveries": Delivery.objects.select_related(
                "transfer", "receiving_hospital"
            ).order_by("-created_at")[:15],
        },
    )


@login_required
def confirm_delivery_view(request, delivery_id):
    delivery = get_object_or_404(
        Delivery.objects.select_related("transfer", "receiving_hospital")
        .prefetch_related("items__commodity", "items__batch"),
        pk=delivery_id,
    )
    if not can_access_facility(request.user, delivery.receiving_hospital_id):
        messages.error(request, "You are not authorized to confirm this delivery.")
        return redirect("transfers_deliveries")

    form = DeliveryConfirmForm(request.POST or None, delivery=delivery)
    if request.method == "POST" and form.is_valid():
        received_quantities = {}
        discrepancy_reasons = {}
        for item in delivery.items.all():
            qty_key = f"received_qty_{item.pk}"
            reason_key = f"discrepancy_reason_{item.pk}"
            if qty_key in form.cleaned_data and form.cleaned_data[qty_key] is not None:
                received_quantities[item.pk] = form.cleaned_data[qty_key]
            if reason_key in form.cleaned_data:
                discrepancy_reasons[item.pk] = form.cleaned_data[reason_key] or ""

        try:
            confirm_delivery(
                delivery=delivery,
                delivery_date=form.cleaned_data["delivery_date"],
                received_quantities=received_quantities,
                discrepancy_reasons=discrepancy_reasons,
                confirmed_by=request.user,
            )
            messages.success(
                request,
                f"Delivery {delivery.delivery_reference} confirmed.",
            )
            return redirect("transfers_deliveries")
        except Exception as exc:
            messages.error(request, str(exc))

    return render(
        request,
        "myapp/distribution/transfers_deliveries.html",
        {
            "active_delivery": delivery,
            "confirm_form": form,
            "transfers": StockTransfer.objects.select_related(
                "source_hospital", "destination_hospital"
            ).order_by("-created_at")[:15],
            "deliveries": Delivery.objects.select_related(
                "transfer", "receiving_hospital"
            ).order_by("-created_at")[:15],
        },
    )