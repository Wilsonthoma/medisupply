from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import (
    AuditLog,
    BranchRequest,
    BranchRequestItem,
    Commodity,
    Delivery,
    DeliveryItem,
    Hospital,
    Inventory,
    InventoryBatch,
    Notification,
    StockMovement,
    StockTransfer,
    StockTransferItem,
    SupplierReceipt,
    SupplierReceiptItem,
    User,
)


def _generate_code(prefix: str, model_cls, field_name: str) -> str:
    today_str = timezone.localdate().strftime("%Y%m%d")
    base_prefix = f"{prefix}-{today_str}-"
    count = model_cls.objects.filter(**{f"{field_name}__startswith": base_prefix}).count() + 1
    return f"{base_prefix}{count:04d}"


def get_client_ip(request) -> str | None:
    if not request:
        return None
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_audit(
    *,
    user: User | None,
    hospital: Hospital | None,
    action: str,
    entity_name: str,
    entity_id: str | int | None,
    description: str,
    ip_address: str | None = None,
) -> AuditLog:
    return AuditLog.objects.create(
        user=user,
        hospital=hospital,
        action=action,
        entity_name=entity_name,
        entity_id=str(entity_id) if entity_id is not None else None,
        description=description,
        ip_address=ip_address,
    )


def notify_users(
    *,
    recipients,
    hospital: Hospital | None,
    title: str,
    message: str,
    notification_type: str,
    reference_code: str | None = None,
) -> list[Notification]:
    created = []
    seen_ids = set()
    for recipient in recipients:
        if not recipient or recipient.user_id in seen_ids or not recipient.is_active:
            continue
        seen_ids.add(recipient.user_id)
        created.append(
            Notification.objects.create(
                recipient=recipient,
                hospital=hospital,
                title=title,
                message=message,
                notification_type=notification_type,
                reference_code=reference_code,
            )
        )
    return created


def _sync_batch_and_inventory_status(batch: InventoryBatch, inventory: Inventory) -> None:
    today = timezone.localdate()
    if batch.quantity_on_hand <= 0:
        batch.quantity_on_hand = 0
        batch.batch_status = InventoryBatch.BatchStatus.DEPLETED
    elif batch.expiry_date < today:
        batch.batch_status = InventoryBatch.BatchStatus.EXPIRED
    elif batch.batch_status not in (
        InventoryBatch.BatchStatus.QUARANTINED,
        InventoryBatch.BatchStatus.EXPIRED,
    ):
        if batch.available_quantity <= max(1, inventory.reorder_level // 2):
            batch.batch_status = InventoryBatch.BatchStatus.LOW_STOCK
        else:
            batch.batch_status = InventoryBatch.BatchStatus.AVAILABLE
    batch.save(update_fields=["quantity_on_hand", "batch_status", "updated_at"])

    total_on_hand = (
        InventoryBatch.objects.filter(inventory=inventory).aggregate(total=Sum("quantity_on_hand"))["total"]
        or 0
    )
    total_reserved = (
        InventoryBatch.objects.filter(inventory=inventory).aggregate(total=Sum("reserved_quantity"))["total"]
        or 0
    )
    inventory.quantity_on_hand = max(0, total_on_hand)
    inventory.reserved_quantity = max(0, total_reserved)
    inventory.save(update_fields=["quantity_on_hand", "reserved_quantity", "last_updated_at"])


def record_stock_movement(
    *,
    hospital: Hospital,
    commodity: Commodity,
    batch: InventoryBatch | None,
    movement_type: str,
    quantity_change: int,
    balance_after: int,
    reference_type: str,
    reference_code: str,
    performed_by: User,
    remarks: str | None = None,
) -> StockMovement:
    return StockMovement.objects.create(
        hospital=hospital,
        commodity=commodity,
        batch=batch,
        movement_type=movement_type,
        quantity_change=quantity_change,
        balance_after=balance_after,
        reference_type=reference_type,
        reference_code=reference_code,
        performed_by=performed_by,
        remarks=remarks,
    )


@transaction.atomic
def receive_supplier_shipment(
    *,
    receiving_hospital: Hospital,
    received_by: User,
    supplier_name: str,
    receipt_date,
    items_data: list[dict],
    delivery_note_ref: str | None = None,
    remarks: str | None = None,
    ip_address: str | None = None,
) -> SupplierReceipt:
    """
    Records inbound stock from the central supplier into a facility's inventory & batches.
    Each item dict requires: commodity_id, batch_number, expiry_date, quantity_received, optional unit_cost.
    """
    if not items_data:
        raise ValidationError("At least one receipt line item is required.")

    receipt_number = _generate_code("RCPT", SupplierReceipt, "receipt_number")
    receipt = SupplierReceipt.objects.create(
        receipt_number=receipt_number,
        supplier_name=supplier_name or "Central Medical Supply Authority",
        receiving_hospital=receiving_hospital,
        received_by=received_by,
        receipt_date=receipt_date,
        delivery_note_ref=delivery_note_ref,
        remarks=remarks,
    )

    for row in items_data:
        qty = int(row["quantity_received"])
        if qty <= 0:
            raise ValidationError("Quantity received must be greater than zero.")

        commodity = Commodity.objects.select_for_update().get(pk=row["commodity_id"])
        inventory, _ = Inventory.objects.select_for_update().get_or_create(
            hospital=receiving_hospital,
            commodity=commodity,
            defaults={"reorder_level": commodity.minimum_stock_level},
        )

        batch, created = InventoryBatch.objects.select_for_update().get_or_create(
            hospital=receiving_hospital,
            commodity=commodity,
            batch_number=row["batch_number"].strip(),
            defaults={
                "inventory": inventory,
                "manufacture_date": row.get("manufacture_date"),
                "expiry_date": row["expiry_date"],
                "received_date": receipt_date,
                "quantity_on_hand": 0,
                "reserved_quantity": 0,
                "batch_status": InventoryBatch.BatchStatus.AVAILABLE,
            },
        )
        if not created:
            batch.inventory = inventory
            batch.expiry_date = row["expiry_date"]

        batch.quantity_on_hand += qty
        _sync_batch_and_inventory_status(batch, inventory)

        SupplierReceiptItem.objects.create(
            receipt=receipt,
            commodity=commodity,
            batch=batch,
            batch_number=batch.batch_number,
            expiry_date=batch.expiry_date,
            quantity_received=qty,
            unit_cost=Decimal(str(row["unit_cost"])) if row.get("unit_cost") is not None else None,
        )

        record_stock_movement(
            hospital=receiving_hospital,
            commodity=commodity,
            batch=batch,
            movement_type=StockMovement.MovementType.INBOUND_SUPPLIER,
            quantity_change=qty,
            balance_after=inventory.quantity_on_hand,
            reference_type="SUPPLIER_RECEIPT",
            reference_code=receipt.receipt_number,
            performed_by=received_by,
            remarks=f"Batch {batch.batch_number} received from {receipt.supplier_name}",
        )

    log_audit(
        user=received_by,
        hospital=receiving_hospital,
        action="RECEIVE_SUPPLIER_SHIPMENT",
        entity_name="SupplierReceipt",
        entity_id=receipt.receipt_id,
        description=f"Recorded supplier receipt {receipt.receipt_number} with {len(items_data)} item(s).",
        ip_address=ip_address,
    )
    return receipt


@transaction.atomic
def create_branch_request(
    *,
    branch_hospital: Hospital,
    target_hospital: Hospital,
    requested_by: User,
    request_date,
    items_data: list[dict],
    reason: str | None = None,
    ip_address: str | None = None,
) -> BranchRequest:
    """
    Creates a new branch requisition to its parent/target main hospital.
    Each item dict requires: commodity_id, requested_quantity, optional item_remarks.
    """
    if branch_hospital.facility_type != Hospital.FacilityType.BRANCH_HOSPITAL:
        raise ValidationError("Only branch hospitals can submit branch requests.")
    if not items_data:
        raise ValidationError("At least one commodity line item is required.")

    request_number = _generate_code("REQ", BranchRequest, "request_number")
    branch_request = BranchRequest.objects.create(
        request_number=request_number,
        branch_hospital=branch_hospital,
        target_hospital=target_hospital,
        requested_by=requested_by,
        request_date=request_date,
        status=BranchRequest.Status.PENDING,
        reason=reason,
    )

    for row in items_data:
        req_qty = int(row["requested_quantity"])
        if req_qty <= 0:
            raise ValidationError("Requested quantity must be greater than zero.")
        commodity = Commodity.objects.get(pk=row["commodity_id"])
        BranchRequestItem.objects.create(
            request=branch_request,
            commodity=commodity,
            requested_quantity=req_qty,
            approved_quantity=0,
            dispatched_quantity=0,
            received_quantity=0,
            item_status=BranchRequestItem.ItemStatus.PENDING,
            item_remarks=row.get("item_remarks"),
        )

    approvers = User.objects.filter(
        is_active=True,
        role__role_code__in=["ROLE_ADMIN", "ROLE_HOSPITAL_ADMIN", "ROLE_WAREHOUSE"],
    )
    notify_users(
        recipients=approvers,
        hospital=target_hospital,
        title=f"New Branch Request {branch_request.request_number}",
        message=f"{branch_hospital.name} submitted request {branch_request.request_number} ({len(items_data)} item(s)).",
        notification_type=Notification.NotificationType.NEW_REQUEST,
        reference_code=branch_request.request_number,
    )

    log_audit(
        user=requested_by,
        hospital=branch_hospital,
        action="CREATE_BRANCH_REQUEST",
        entity_name="BranchRequest",
        entity_id=branch_request.request_id,
        description=f"Submitted branch request {branch_request.request_number} to {target_hospital.name}.",
        ip_address=ip_address,
    )
    return branch_request


def allocate_batches_fefo(
    *,
    source_hospital: Hospital,
    commodity: Commodity,
    quantity_needed: int,
    performed_by: User,
    reference_code: str,
    reserve_only: bool = True,
) -> list[tuple[InventoryBatch, int]]:
    """
    Allocates stock using First Expiry, First Out (FEFO) across non-expired, non-quarantined batches
    with row-level locking (`select_for_update`).
    """
    if quantity_needed <= 0:
        return []

    today = timezone.localdate()
    inventory = Inventory.objects.select_for_update().filter(
        hospital=source_hospital,
        commodity=commodity,
    ).first()

    if not inventory:
        raise ValidationError(f"No inventory record found for {commodity.name} at {source_hospital.name}.")

    batches = (
        InventoryBatch.objects.select_for_update()
        .filter(
            hospital=source_hospital,
            commodity=commodity,
            expiry_date__gte=today,
            quantity_on_hand__gt=0,
        )
        .exclude(
            batch_status__in=[
                InventoryBatch.BatchStatus.EXPIRED,
                InventoryBatch.BatchStatus.QUARANTINED,
                InventoryBatch.BatchStatus.DEPLETED,
            ]
        )
        .order_by("expiry_date", "received_date", "batch_id")
    )

    total_available = sum(b.available_quantity for b in batches)
    if total_available < quantity_needed:
        raise ValidationError(
            f"Insufficient available FEFO stock for {commodity.name} at {source_hospital.name}: "
            f"needed {quantity_needed}, available {total_available}."
        )

    remaining = quantity_needed
    allocations: list[tuple[InventoryBatch, int]] = []

    for batch in batches:
        if remaining <= 0:
            break
        avail = batch.available_quantity
        if avail <= 0:
            continue
        take = min(avail, remaining)
        if reserve_only:
            batch.reserved_quantity += take
            batch.save(update_fields=["reserved_quantity", "updated_at"])
            _sync_batch_and_inventory_status(batch, inventory)
            record_stock_movement(
                hospital=source_hospital,
                commodity=commodity,
                batch=batch,
                movement_type=StockMovement.MovementType.ALLOCATION_RESERVE,
                quantity_change=0,
                balance_after=inventory.quantity_on_hand,
                reference_type="BRANCH_REQUEST",
                reference_code=reference_code,
                performed_by=performed_by,
                remarks=f"Reserved {take} unit(s) from batch {batch.batch_number} (Exp: {batch.expiry_date}) via FEFO.",
            )
        allocations.append((batch, take))
        remaining -= take

    return allocations


@transaction.atomic
def review_branch_request(
    *,
    branch_request: BranchRequest,
    reviewed_by: User,
    decision: str,
    item_approvals: dict[int, int] | None = None,
    review_notes: str | None = None,
    rejection_reason: str | None = None,
    ip_address: str | None = None,
) -> BranchRequest:
    """
    Approves (full or partial) or rejects a BranchRequest.
    On approval, reserves FEFO stock at target_hospital so approved stock isn't double-allocated.
    `decision` must be 'APPROVE' or 'REJECT'.
    """
    locked_req = BranchRequest.objects.select_for_update().get(pk=branch_request.pk)
    if locked_req.status not in (
        BranchRequest.Status.PENDING,
        BranchRequest.Status.UNDER_REVIEW,
    ):
        raise ValidationError(f"Request {locked_req.request_number} cannot be reviewed in status {locked_req.status}.")

    items = list(BranchRequestItem.objects.select_for_update().filter(request=locked_req))
    now = timezone.now()

    if decision == "REJECT":
        locked_req.status = BranchRequest.Status.REJECTED
        locked_req.reviewed_by = reviewed_by
        locked_req.reviewed_at = now
        locked_req.review_notes = review_notes
        locked_req.rejection_reason = rejection_reason or "Rejected during review."
        locked_req.save()

        for item in items:
            item.approved_quantity = 0
            item.item_status = BranchRequestItem.ItemStatus.REJECTED
            item.save(update_fields=["approved_quantity", "item_status"])

        notify_users(
            recipients=[locked_req.requested_by],
            hospital=locked_req.branch_hospital,
            title=f"Request {locked_req.request_number} Rejected",
            message=f"Your request {locked_req.request_number} was rejected: {locked_req.rejection_reason}",
            notification_type=Notification.NotificationType.REQUEST_REJECTED,
            reference_code=locked_req.request_number,
        )
        log_audit(
            user=reviewed_by,
            hospital=locked_req.target_hospital,
            action="REJECT_BRANCH_REQUEST",
            entity_name="BranchRequest",
            entity_id=locked_req.request_id,
            description=f"Rejected branch request {locked_req.request_number}.",
            ip_address=ip_address,
        )
        return locked_req

    if decision != "APPROVE":
        raise ValidationError("Invalid review decision. Use 'APPROVE' or 'REJECT'.")

    item_approvals = item_approvals or {}
    any_partial = False
    any_approved = False

    for item in items:
        raw_approved = item_approvals.get(item.request_item_id, item.requested_quantity)
        approved_qty = int(raw_approved)
        if approved_qty < 0 or approved_qty > item.requested_quantity:
            raise ValidationError(
                f"Approved quantity ({approved_qty}) for {item.commodity.name} must be between 0 and {item.requested_quantity}."
            )

        if approved_qty > 0:
            allocate_batches_fefo(
                source_hospital=locked_req.target_hospital,
                commodity=item.commodity,
                quantity_needed=approved_qty,
                performed_by=reviewed_by,
                reference_code=locked_req.request_number,
                reserve_only=True,
            )
            any_approved = True

        item.approved_quantity = approved_qty
        if approved_qty == 0:
            item.item_status = BranchRequestItem.ItemStatus.REJECTED
            any_partial = True
        elif approved_qty < item.requested_quantity:
            item.item_status = BranchRequestItem.ItemStatus.PARTIALLY_APPROVED
            any_partial = True
        else:
            item.item_status = BranchRequestItem.ItemStatus.APPROVED

        item.save(update_fields=["approved_quantity", "item_status"])

    if not any_approved:
        raise ValidationError("Cannot approve a request with zero approved quantity across all items; reject it instead.")

    locked_req.status = (
        BranchRequest.Status.PARTIALLY_APPROVED if any_partial else BranchRequest.Status.APPROVED
    )
    locked_req.reviewed_by = reviewed_by
    locked_req.reviewed_at = now
    locked_req.review_notes = review_notes
    locked_req.save()

    notif_type = (
        Notification.NotificationType.REQUEST_PARTIAL
        if any_partial
        else Notification.NotificationType.REQUEST_APPROVED
    )
    notify_users(
        recipients=[locked_req.requested_by],
        hospital=locked_req.branch_hospital,
        title=f"Request {locked_req.request_number} {locked_req.get_status_display()}",
        message=f"Branch request {locked_req.request_number} has been marked {locked_req.get_status_display()}.",
        notification_type=notif_type,
        reference_code=locked_req.request_number,
    )

    log_audit(
        user=reviewed_by,
        hospital=locked_req.target_hospital,
        action="APPROVE_BRANCH_REQUEST",
        entity_name="BranchRequest",
        entity_id=locked_req.request_id,
        description=f"Reviewed request {locked_req.request_number} -> {locked_req.status}.",
        ip_address=ip_address,
    )
    return locked_req


@transaction.atomic
def dispatch_stock_transfer(
    *,
    source_hospital: Hospital,
    destination_hospital: Hospital,
    dispatched_by: User,
    dispatch_date,
    branch_request: BranchRequest | None = None,
    manual_items: list[dict] | None = None,
    notes: str | None = None,
    ip_address: str | None = None,
) -> StockTransfer:
    """
    Dispatches a stock transfer from source_hospital to destination_hospital using FEFO,
    deducts reserved/on-hand stock at source, logs OUTBOUND_TRANSFER movements,
    and creates an awaiting-confirmation Delivery record.
    """
    transfer_number = _generate_code("TRF", StockTransfer, "transfer_number")
    transfer = StockTransfer.objects.create(
        transfer_number=transfer_number,
        request=branch_request,
        source_hospital=source_hospital,
        destination_hospital=destination_hospital,
        dispatched_by=dispatched_by,
        dispatch_date=dispatch_date,
        status=StockTransfer.Status.DISPATCHED,
        notes=notes,
    )

    lines_to_fulfill: list[tuple[Commodity, int, BranchRequestItem | None]] = []

    if branch_request:
        req_locked = BranchRequest.objects.select_for_update().get(pk=branch_request.pk)
        if req_locked.status not in (
            BranchRequest.Status.APPROVED,
            BranchRequest.Status.PARTIALLY_APPROVED,
            BranchRequest.Status.PROCESSING,
        ):
            raise ValidationError(f"Request {req_locked.request_number} is not ready for dispatch ({req_locked.status}).")

        req_items = BranchRequestItem.objects.select_for_update().filter(request=req_locked)
        for req_item in req_items:
            remaining_to_dispatch = req_item.approved_quantity - req_item.dispatched_quantity
            if remaining_to_dispatch > 0:
                lines_to_fulfill.append((req_item.commodity, remaining_to_dispatch, req_item))

        if not lines_to_fulfill:
            raise ValidationError("No remaining approved quantities to dispatch for this request.")
    else:
        if not manual_items:
            raise ValidationError("Provide either a branch_request or manual_items to dispatch.")
        for row in manual_items:
            qty = int(row["quantity"])
            if qty <= 0:
                raise ValidationError("Transfer quantity must be greater than zero.")
            commodity = Commodity.objects.get(pk=row["commodity_id"])
            lines_to_fulfill.append((commodity, qty, None))

    for commodity, qty_needed, req_item in lines_to_fulfill:
        inventory = Inventory.objects.select_for_update().get(
            hospital=source_hospital,
            commodity=commodity,
        )
        allocations = allocate_batches_fefo(
            source_hospital=source_hospital,
            commodity=commodity,
            quantity_needed=qty_needed,
            performed_by=dispatched_by,
            reference_code=transfer.transfer_number,
            reserve_only=False,
        )

        for batch, qty_take in allocations:
            # Release matching reservation if it was reserved during approval
            release_amt = min(batch.reserved_quantity, qty_take)
            if release_amt > 0:
                batch.reserved_quantity -= release_amt

            if batch.quantity_on_hand < qty_take:
                raise ValidationError(f"Insufficient batch stock on hand for {batch.batch_number}.")

            batch.quantity_on_hand -= qty_take
            _sync_batch_and_inventory_status(batch, inventory)

            StockTransferItem.objects.create(
                transfer=transfer,
                request_item=req_item,
                commodity=commodity,
                batch=batch,
                quantity_transferred=qty_take,
            )

            record_stock_movement(
                hospital=source_hospital,
                commodity=commodity,
                batch=batch,
                movement_type=StockMovement.MovementType.OUTBOUND_TRANSFER,
                quantity_change=-qty_take,
                balance_after=inventory.quantity_on_hand,
                reference_type="STOCK_TRANSFER",
                reference_code=transfer.transfer_number,
                performed_by=dispatched_by,
                remarks=f"Dispatched {qty_take} ({batch.batch_number}) to {destination_hospital.name}",
            )

        if req_item:
            req_item.dispatched_quantity += qty_needed
            req_item.item_status = BranchRequestItem.ItemStatus.DISPATCHED
            req_item.save(update_fields=["dispatched_quantity", "item_status"])

    if branch_request:
        branch_request.status = BranchRequest.Status.DISPATCHED
        branch_request.save(update_fields=["status", "updated_at"])

    delivery_ref = _generate_code("DLV", Delivery, "delivery_reference")
    delivery = Delivery.objects.create(
        delivery_reference=delivery_ref,
        transfer=transfer,
        receiving_hospital=destination_hospital,
        status=Delivery.Status.AWAITING_CONFIRMATION,
    )

    branch_officers = User.objects.filter(
        is_active=True,
        hospital=destination_hospital,
        role__role_code="ROLE_BRANCH_OFFICER",
    )
    notify_users(
        recipients=branch_officers,
        hospital=destination_hospital,
        title=f"Transfer {transfer.transfer_number} Dispatched",
        message=f"Shipment {transfer.transfer_number} ({delivery.delivery_reference}) has been dispatched to {destination_hospital.name}.",
        notification_type=Notification.NotificationType.ORDER_DISPATCHED,
        reference_code=transfer.transfer_number,
    )

    log_audit(
        user=dispatched_by,
        hospital=source_hospital,
        action="DISPATCH_STOCK_TRANSFER",
        entity_name="StockTransfer",
        entity_id=transfer.transfer_id,
        description=f"Dispatched transfer {transfer.transfer_number} to {destination_hospital.name}.",
        ip_address=ip_address,
    )
    return transfer


@transaction.atomic
def confirm_delivery(
    *,
    delivery: Delivery,
    confirmed_by: User,
    delivery_date,
    received_quantities: dict[int, int],
    discrepancy_reasons: dict[int, str] | None = None,
    ip_address: str | None = None,
) -> Delivery:
    """
    Confirms receipt of a delivery at the receiving facility, updates destination inventory & batches,
    records discrepancy quantities, logs INBOUND_TRANSFER movements, and updates request/transfer status.
    `received_quantities` maps `delivery_item.delivery_item_id` -> received integer quantity.
    """
    locked_delivery = Delivery.objects.select_for_update().get(pk=delivery.pk)
    if locked_delivery.status != Delivery.Status.AWAITING_CONFIRMATION:
        raise ValidationError(f"Delivery {locked_delivery.delivery_reference} is already confirmed.")

    transfer = StockTransfer.objects.select_for_update().get(pk=locked_delivery.transfer_id)
    discrepancy_reasons = discrepancy_reasons or {}
    has_discrepancy = False
    discrepancy_notes = []

    for d_item in DeliveryItem.objects.select_for_update().filter(delivery=locked_delivery):
        if d_item.delivery_item_id not in received_quantities:
            raise ValidationError(f"Missing received quantity for {d_item.commodity.name} ({d_item.batch.batch_number}).")

        rec_qty = int(received_quantities[d_item.delivery_item_id])
        if rec_qty < 0 or rec_qty > d_item.dispatched_quantity:
            raise ValidationError(
                f"Received quantity ({rec_qty}) for {d_item.commodity.name} must be between 0 and {d_item.dispatched_quantity}."
            )

        diff = d_item.dispatched_quantity - rec_qty
        d_item.received_quantity = rec_qty
        d_item.discrepancy_quantity = diff
        if diff > 0:
            has_discrepancy = True
            reason_text = discrepancy_reasons.get(d_item.delivery_item_id) or "Shortage / damage reported on arrival"
            d_item.discrepancy_reason = reason_text
            discrepancy_notes.append(
                f"{d_item.commodity.name} (Batch {d_item.batch.batch_number}): missing {diff} ({reason_text})"
            )
        d_item.save(
            update_fields=[
                "received_quantity",
                "discrepancy_quantity",
                "discrepancy_reason",
            ]
        )

        if rec_qty > 0:
            dest_inv, _ = Inventory.objects.select_for_update().get_or_create(
                hospital=locked_delivery.receiving_hospital,
                commodity=d_item.commodity,
                defaults={"reorder_level": d_item.commodity.minimum_stock_level},
            )
            dest_batch, created = InventoryBatch.objects.select_for_update().get_or_create(
                hospital=locked_delivery.receiving_hospital,
                commodity=d_item.commodity,
                batch_number=d_item.batch.batch_number,
                defaults={
                    "inventory": dest_inv,
                    "manufacture_date": d_item.batch.manufacture_date,
                    "expiry_date": d_item.batch.expiry_date,
                    "received_date": delivery_date,
                    "quantity_on_hand": 0,
                    "reserved_quantity": 0,
                    "batch_status": InventoryBatch.BatchStatus.AVAILABLE,
                },
            )
            if not created:
                dest_batch.inventory = dest_inv
            dest_batch.quantity_on_hand += rec_qty
            _sync_batch_and_inventory_status(dest_batch, dest_inv)

            record_stock_movement(
                hospital=locked_delivery.receiving_hospital,
                commodity=d_item.commodity,
                batch=dest_batch,
                movement_type=StockMovement.MovementType.INBOUND_TRANSFER,
                quantity_change=rec_qty,
                balance_after=dest_inv.quantity_on_hand,
                reference_type="DELIVERY",
                reference_code=locked_delivery.delivery_reference,
                performed_by=confirmed_by,
                remarks=f"Confirmed {rec_qty} from transfer {transfer.transfer_number}",
            )

        if d_item.transfer_item and d_item.transfer_item.request_item:
            req_item = d_item.transfer_item.request_item
            req_item.received_quantity += rec_qty
            req_item.item_status = BranchRequestItem.ItemStatus.RECEIVED
            req_item.save(update_fields=["received_quantity", "item_status"])

    now = timezone.now()
    locked_delivery.confirmed_by = confirmed_by
    locked_delivery.delivery_date = delivery_date
    locked_delivery.confirmed_at = now
    if has_discrepancy:
        locked_delivery.status = Delivery.Status.CONFIRMED_WITH_DISCREPANCY
        locked_delivery.discrepancy_summary = "; ".join(discrepancy_notes)
    else:
        locked_delivery.status = Delivery.Status.CONFIRMED_COMPLETE
    locked_delivery.save()

    transfer.status = StockTransfer.Status.COMPLETED
    transfer.save(update_fields=["status", "updated_at"])

    if transfer.request:
        transfer.request.status = BranchRequest.Status.COMPLETED
        transfer.request.save(update_fields=["status", "updated_at"])

    recipients = [transfer.dispatched_by]
    if transfer.request and transfer.request.reviewed_by:
        recipients.append(transfer.request.reviewed_by)

    if has_discrepancy:
        notify_users(
            recipients=recipients,
            hospital=locked_delivery.receiving_hospital,
            title=f"Discrepancy on Delivery {locked_delivery.delivery_reference}",
            message=f"Confirmed with discrepancy at {locked_delivery.receiving_hospital.name}: {locked_delivery.discrepancy_summary}",
            notification_type=Notification.NotificationType.DISCREPANCY_ALERT,
            reference_code=locked_delivery.delivery_reference,
        )
    else:
        notify_users(
            recipients=recipients,
            hospital=locked_delivery.receiving_hospital,
            title=f"Delivery {locked_delivery.delivery_reference} Confirmed",
            message=f"Delivery {locked_delivery.delivery_reference} confirmed complete at {locked_delivery.receiving_hospital.name}.",
            notification_type=Notification.NotificationType.DELIVERY_CONFIRMATION,
            reference_code=locked_delivery.delivery_reference,
        )

    log_audit(
        user=confirmed_by,
        hospital=locked_delivery.receiving_hospital,
        action="CONFIRM_DELIVERY",
        entity_name="Delivery",
        entity_id=locked_delivery.delivery_id,
        description=f"Confirmed delivery {locked_delivery.delivery_reference} ({locked_delivery.status}).",
        ip_address=ip_address,
    )
    return locked_delivery