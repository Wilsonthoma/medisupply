from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Role(models.Model):
    role_id = models.BigAutoField(primary_key=True)
    role_code = models.CharField(max_length=40, unique=True)
    role_name = models.CharField(max_length=80, unique=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "roles"

    def __str__(self):
        return f"{self.role_name} ({self.role_code})"


class Hospital(models.Model):
    class FacilityType(models.TextChoices):
        MAIN_HOSPITAL = "MAIN_HOSPITAL", "Main Hospital"
        BRANCH_HOSPITAL = "BRANCH_HOSPITAL", "Branch Hospital"

    hospital_id = models.BigAutoField(primary_key=True)
    hospital_code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=150)
    facility_type = models.CharField(max_length=20, choices=FacilityType.choices)
    parent_hospital = models.ForeignKey(
        "self",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column="parent_hospital_id",
        related_name="branches",
    )
    county = models.CharField(max_length=80, default="Nakuru")
    sub_county = models.CharField(max_length=80, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=40, blank=True, null=True)
    email = models.CharField(max_length=120, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hospitals"

    def clean(self):
        if self.facility_type == self.FacilityType.BRANCH_HOSPITAL and not self.parent_hospital:
            raise ValidationError("A branch hospital must be linked to a main hospital.")
        if self.facility_type == self.FacilityType.MAIN_HOSPITAL and self.parent_hospital:
            raise ValidationError("A main hospital cannot have a parent hospital.")

    def __str__(self):
        return f"{self.name} ({self.hospital_code})"


class UserManager(BaseUserManager):
    def create_user(self, username, email, full_name, role=None, password=None, hospital=None, **extra_fields):
        if not username:
            raise ValueError("Username is required")
        if not email:
            raise ValueError("Email is required")
        if role is None:
            role, _ = Role.objects.get_or_create(
                role_code="ROLE_BRANCH_OFFICER",
                defaults={"role_name": "Branch Hospital Officer", "description": "Branch supply officer"},
            )
        email = self.normalize_email(email)
        user = self.model(
            username=username,
            email=email,
            full_name=full_name,
            role=role,
            hospital=hospital,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, full_name="System Administrator", password=None, **extra_fields):
        admin_role, _ = Role.objects.get_or_create(
            role_code="ROLE_ADMIN",
            defaults={"role_name": "System Administrator", "description": "Full system access"},
        )
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_staff", True)
        return self.create_user(
            username=username,
            email=email,
            full_name=full_name,
            role=admin_role,
            password=password,
            hospital=None,
            **extra_fields,
        )


class User(AbstractBaseUser, PermissionsMixin):
    user_id = models.BigAutoField(primary_key=True)
    role = models.ForeignKey(Role, on_delete=models.RESTRICT, db_column="role_id", related_name="users")
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column="hospital_id",
        related_name="users",
    )
    full_name = models.CharField(max_length=120)
    username = models.CharField(max_length=60, unique=True)
    email = models.CharField(max_length=120, unique=True)
    phone = models.CharField(max_length=40, blank=True, null=True)
    password = models.CharField(max_length=255, db_column="password_hash")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True, db_column="last_login_at")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email", "full_name"]

    class Meta:
        db_table = "users"

    @property
    def id(self):
        return self.user_id

    def __str__(self):
        return f"{self.full_name} [{self.role.role_code}]"


class CommodityCategory(models.Model):
    category_id = models.BigAutoField(primary_key=True)
    category_code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "commodity_categories"
        verbose_name_plural = "Commodity Categories"

    def __str__(self):
        return self.name


class Commodity(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        DISCONTINUED = "DISCONTINUED", "Discontinued"

    commodity_id = models.BigAutoField(primary_key=True)
    commodity_code = models.CharField(max_length=40, unique=True)
    category = models.ForeignKey(
        CommodityCategory,
        on_delete=models.RESTRICT,
        db_column="category_id",
        related_name="commodities",
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    unit_of_measure = models.CharField(max_length=40)
    minimum_stock_level = models.IntegerField(default=10)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "commodities"

    def __str__(self):
        return f"{self.commodity_code} - {self.name}"


class Inventory(models.Model):
    inventory_id = models.BigAutoField(primary_key=True)
    hospital = models.ForeignKey(Hospital, on_delete=models.RESTRICT, db_column="hospital_id", related_name="inventories")
    commodity = models.ForeignKey(
        Commodity,
        on_delete=models.RESTRICT,
        db_column="commodity_id",
        related_name="inventories",
    )
    quantity_on_hand = models.IntegerField(default=0)
    reserved_quantity = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=10)
    last_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventory"
        unique_together = ("hospital", "commodity")

    @property
    def available_quantity(self):
        return max(0, self.quantity_on_hand - self.reserved_quantity)

    def __str__(self):
        return f"{self.hospital.name} | {self.commodity.name}: {self.quantity_on_hand}"


class InventoryBatch(models.Model):
    class BatchStatus(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        LOW_STOCK = "LOW_STOCK", "Low Stock"
        EXPIRED = "EXPIRED", "Expired"
        DEPLETED = "DEPLETED", "Depleted"
        QUARANTINED = "QUARANTINED", "Quarantined"

    batch_id = models.BigAutoField(primary_key=True)
    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.CASCADE,
        db_column="inventory_id",
        related_name="batches",
    )
    hospital = models.ForeignKey(Hospital, on_delete=models.RESTRICT, db_column="hospital_id", related_name="batches")
    commodity = models.ForeignKey(Commodity, on_delete=models.RESTRICT, db_column="commodity_id", related_name="batches")
    batch_number = models.CharField(max_length=60)
    manufacture_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField()
    received_date = models.DateField()
    quantity_on_hand = models.IntegerField(default=0)
    reserved_quantity = models.IntegerField(default=0)
    batch_status = models.CharField(max_length=20, choices=BatchStatus.choices, default=BatchStatus.AVAILABLE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventory_batches"
        unique_together = ("hospital", "commodity", "batch_number")

    @property
    def available_quantity(self):
        return max(0, self.quantity_on_hand - self.reserved_quantity)

    @property
    def is_expired(self):
        return self.expiry_date < timezone.localdate()

    def __str__(self):
        return f"{self.batch_number} (Exp: {self.expiry_date}, Qty: {self.quantity_on_hand})"


class SupplierReceipt(models.Model):
    receipt_id = models.BigAutoField(primary_key=True)
    receipt_number = models.CharField(max_length=50, unique=True)
    supplier_name = models.CharField(max_length=150, default="Central Medical Supply Authority")
    receiving_hospital = models.ForeignKey(
        Hospital,
        on_delete=models.RESTRICT,
        db_column="receiving_hospital_id",
        related_name="supplier_receipts",
    )
    received_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        db_column="received_by_user_id",
        related_name="recorded_receipts",
    )
    receipt_date = models.DateField()
    delivery_note_ref = models.CharField(max_length=80, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "supplier_receipts"


class SupplierReceiptItem(models.Model):
    receipt_item_id = models.BigAutoField(primary_key=True)
    receipt = models.ForeignKey(
        SupplierReceipt,
        on_delete=models.CASCADE,
        db_column="receipt_id",
        related_name="items",
    )
    commodity = models.ForeignKey(Commodity, on_delete=models.RESTRICT, db_column="commodity_id")
    batch = models.ForeignKey(
        InventoryBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="batch_id",
    )
    batch_number = models.CharField(max_length=60)
    expiry_date = models.DateField()
    quantity_received = models.IntegerField()
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "supplier_receipt_items"


class BranchRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
        APPROVED = "APPROVED", "Approved"
        PARTIALLY_APPROVED = "PARTIALLY_APPROVED", "Partially Approved"
        REJECTED = "REJECTED", "Rejected"
        PROCESSING = "PROCESSING", "Processing"
        DISPATCHED = "DISPATCHED", "Dispatched"
        DELIVERED = "DELIVERED", "Delivered"
        COMPLETED = "COMPLETED", "Completed"

    request_id = models.BigAutoField(primary_key=True)
    request_number = models.CharField(max_length=50, unique=True)
    branch_hospital = models.ForeignKey(
        Hospital,
        on_delete=models.RESTRICT,
        db_column="branch_hospital_id",
        related_name="branch_requests",
    )
    target_hospital = models.ForeignKey(
        Hospital,
        on_delete=models.RESTRICT,
        db_column="target_hospital_id",
        related_name="incoming_branch_requests",
    )
    requested_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        db_column="requested_by_user_id",
        related_name="submitted_requests",
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column="reviewed_by_user_id",
        related_name="reviewed_requests",
    )
    request_date = models.DateField()
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.PENDING)
    reason = models.TextField(blank=True, null=True)
    review_notes = models.TextField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "branch_requests"


class BranchRequestItem(models.Model):
    class ItemStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        PARTIALLY_APPROVED = "PARTIALLY_APPROVED", "Partially Approved"
        REJECTED = "REJECTED", "Rejected"
        DISPATCHED = "DISPATCHED", "Dispatched"
        RECEIVED = "RECEIVED", "Received"

    request_item_id = models.BigAutoField(primary_key=True)
    request = models.ForeignKey(
        BranchRequest,
        on_delete=models.CASCADE,
        db_column="request_id",
        related_name="items",
    )
    commodity = models.ForeignKey(Commodity, on_delete=models.RESTRICT, db_column="commodity_id")
    requested_quantity = models.IntegerField()
    approved_quantity = models.IntegerField(default=0)
    dispatched_quantity = models.IntegerField(default=0)
    received_quantity = models.IntegerField(default=0)
    item_status = models.CharField(max_length=25, choices=ItemStatus.choices, default=ItemStatus.PENDING)
    item_remarks = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = "branch_request_items"
        unique_together = ("request", "commodity")


class StockTransfer(models.Model):
    class Status(models.TextChoices):
        PREPARING = "PREPARING", "Preparing"
        DISPATCHED = "DISPATCHED", "Dispatched"
        IN_TRANSIT = "IN_TRANSIT", "In Transit"
        DELIVERED = "DELIVERED", "Delivered"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    transfer_id = models.BigAutoField(primary_key=True)
    transfer_number = models.CharField(max_length=50, unique=True)
    request = models.ForeignKey(
        BranchRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="request_id",
        related_name="transfers",
    )
    source_hospital = models.ForeignKey(
        Hospital,
        on_delete=models.RESTRICT,
        db_column="source_hospital_id",
        related_name="outgoing_transfers",
    )
    destination_hospital = models.ForeignKey(
        Hospital,
        on_delete=models.RESTRICT,
        db_column="destination_hospital_id",
        related_name="incoming_transfers",
    )
    dispatched_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        db_column="dispatched_by_user_id",
        related_name="dispatched_transfers",
    )
    dispatch_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DISPATCHED)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "stock_transfers"


class StockTransferItem(models.Model):
    transfer_item_id = models.BigAutoField(primary_key=True)
    transfer = models.ForeignKey(
        StockTransfer,
        on_delete=models.CASCADE,
        db_column="transfer_id",
        related_name="items",
    )
    request_item = models.ForeignKey(
        BranchRequestItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="request_item_id",
    )
    commodity = models.ForeignKey(Commodity, on_delete=models.RESTRICT, db_column="commodity_id")
    batch = models.ForeignKey(InventoryBatch, on_delete=models.RESTRICT, db_column="batch_id")
    quantity_transferred = models.IntegerField()

    class Meta:
        db_table = "stock_transfer_items"


class Delivery(models.Model):
    class Status(models.TextChoices):
        AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION", "Awaiting Confirmation"
        CONFIRMED_COMPLETE = "CONFIRMED_COMPLETE", "Confirmed Complete"
        CONFIRMED_WITH_DISCREPANCY = "CONFIRMED_WITH_DISCREPANCY", "Confirmed With Discrepancy"

    delivery_id = models.BigAutoField(primary_key=True)
    delivery_reference = models.CharField(max_length=50, unique=True)
    transfer = models.OneToOneField(
        StockTransfer,
        on_delete=models.CASCADE,
        db_column="transfer_id",
        related_name="delivery",
    )
    receiving_hospital = models.ForeignKey(
        Hospital,
        on_delete=models.RESTRICT,
        db_column="receiving_hospital_id",
        related_name="deliveries",
    )
    confirmed_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column="confirmed_by_user_id",
        related_name="confirmed_deliveries",
    )
    delivery_date = models.DateField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.AWAITING_CONFIRMATION)
    discrepancy_summary = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "deliveries"


class DeliveryItem(models.Model):
    delivery_item_id = models.BigAutoField(primary_key=True)
    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        db_column="delivery_id",
        related_name="items",
    )
    transfer_item = models.OneToOneField(
        StockTransferItem,
        on_delete=models.RESTRICT,
        db_column="transfer_item_id",
    )
    commodity = models.ForeignKey(Commodity, on_delete=models.RESTRICT, db_column="commodity_id")
    batch = models.ForeignKey(InventoryBatch, on_delete=models.RESTRICT, db_column="batch_id")
    dispatched_quantity = models.IntegerField()
    received_quantity = models.IntegerField(default=0)
    discrepancy_quantity = models.IntegerField(editable=False)
    discrepancy_reason = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = "delivery_items"


class StockMovement(models.Model):
    class MovementType(models.TextChoices):
        INBOUND_SUPPLIER = "INBOUND_SUPPLIER", "Inbound Supplier"
        ALLOCATION_RESERVE = "ALLOCATION_RESERVE", "Allocation Reserve"
        ALLOCATION_RELEASE = "ALLOCATION_RELEASE", "Allocation Release"
        OUTBOUND_TRANSFER = "OUTBOUND_TRANSFER", "Outbound Transfer"
        INBOUND_TRANSFER = "INBOUND_TRANSFER", "Inbound Transfer"
        ADJUSTMENT_PLUS = "ADJUSTMENT_PLUS", "Adjustment Plus"
        ADJUSTMENT_MINUS = "ADJUSTMENT_MINUS", "Adjustment Minus"
        EXPIRED_WRITE_OFF = "EXPIRED_WRITE_OFF", "Expired Write-Off"

    movement_id = models.BigAutoField(primary_key=True)
    hospital = models.ForeignKey(Hospital, on_delete=models.RESTRICT, db_column="hospital_id", related_name="movements")
    commodity = models.ForeignKey(Commodity, on_delete=models.RESTRICT, db_column="commodity_id")
    batch = models.ForeignKey(
        InventoryBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="batch_id",
    )
    movement_type = models.CharField(max_length=25, choices=MovementType.choices)
    quantity_change = models.IntegerField()
    balance_after = models.IntegerField()
    reference_type = models.CharField(max_length=40)
    reference_code = models.CharField(max_length=60)
    performed_by = models.ForeignKey(User, on_delete=models.RESTRICT, db_column="performed_by_user_id")
    remarks = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "stock_movements"


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        NEW_REQUEST = "NEW_REQUEST", "New Request"
        REQUEST_APPROVED = "REQUEST_APPROVED", "Request Approved"
        REQUEST_PARTIAL = "REQUEST_PARTIAL", "Request Partially Approved"
        REQUEST_REJECTED = "REQUEST_REJECTED", "Request Rejected"
        ORDER_DISPATCHED = "ORDER_DISPATCHED", "Order Dispatched"
        DELIVERY_CONFIRMATION = "DELIVERY_CONFIRMATION", "Delivery Confirmation"
        DISCREPANCY_ALERT = "DISCREPANCY_ALERT", "Discrepancy Alert"
        LOW_STOCK = "LOW_STOCK", "Low Stock"
        EXPIRY_ALERT = "EXPIRY_ALERT", "Expiry Alert"

    notification_id = models.BigAutoField(primary_key=True)
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="recipient_user_id",
        related_name="notifications",
    )
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="hospital_id",
    )
    title = models.CharField(max_length=140)
    message = models.CharField(max_length=500)
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices)
    reference_code = models.CharField(max_length=60, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"


class AuditLog(models.Model):
    audit_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="user_id",
    )
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="hospital_id",
    )
    action = models.CharField(max_length=80)
    entity_name = models.CharField(max_length=60)
    entity_id = models.CharField(max_length=60, blank=True, null=True)
    description = models.CharField(max_length=500)
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_logs"