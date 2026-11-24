from django import forms
from django.utils import timezone

from .models import (
    BranchRequest,
    Commodity,
    CommodityCategory,
    Delivery,
    Hospital,
    Inventory,
    StockTransfer,
    SupplierReceipt,
)


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=60,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter username"}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Enter password"}),
    )


class CommodityCategoryForm(forms.ModelForm):
    class Meta:
        model = CommodityCategory
        fields = ["category_code", "name", "description", "is_active"]
        widgets = {
            "category_code": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class CommodityForm(forms.ModelForm):
    class Meta:
        model = Commodity
        fields = [
            "commodity_code",
            "category",
            "name",
            "description",
            "unit_of_measure",
            "minimum_stock_level",
            "status",
        ]
        widgets = {
            "commodity_code": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "unit_of_measure": forms.TextInput(attrs={"class": "form-control"}),
            "minimum_stock_level": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }


class InventoryReorderForm(forms.ModelForm):
    class Meta:
        model = Inventory
        fields = ["reorder_level"]
        widgets = {
            "reorder_level": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
        }


class SupplierReceiptForm(forms.ModelForm):
    class Meta:
        model = SupplierReceipt
        fields = ["receiving_hospital", "supplier_name", "receipt_date", "delivery_note_ref", "remarks"]
        widgets = {
            "receiving_hospital": forms.Select(attrs={"class": "form-select"}),
            "supplier_name": forms.TextInput(attrs={"class": "form-control"}),
            "receipt_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "delivery_note_ref": forms.TextInput(attrs={"class": "form-control"}),
            "remarks": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get("receipt_date"):
            self.initial["receipt_date"] = timezone.localdate().isoformat()


class SupplierReceiptItemForm(forms.Form):
    commodity = forms.ModelChoiceField(
        queryset=Commodity.objects.filter(status=Commodity.Status.ACTIVE).order_by("name"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    batch_number = forms.CharField(
        max_length=60,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. BATCH-2026-01"}),
    )
    manufacture_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    expiry_date = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    quantity_received = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 1}),
    )
    unit_cost = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        max_digits=12,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )

    def clean_expiry_date(self):
        exp = self.cleaned_data["expiry_date"]
        if exp < timezone.localdate():
            raise forms.ValidationError("Cannot receive a batch that is already expired.")
        return exp


class BranchRequestForm(forms.ModelForm):
    class Meta:
        model = BranchRequest
        fields = ["branch_hospital", "target_hospital", "request_date", "reason"]
        widgets = {
            "branch_hospital": forms.Select(attrs={"class": "form-select"}),
            "target_hospital": forms.Select(attrs={"class": "form-select"}),
            "request_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "reason": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get("request_date"):
            self.initial["request_date"] = timezone.localdate().isoformat()
        self.fields["branch_hospital"].queryset = Hospital.objects.filter(
            facility_type=Hospital.FacilityType.BRANCH_HOSPITAL,
            is_active=True,
        )
        self.fields["target_hospital"].queryset = Hospital.objects.filter(
            facility_type=Hospital.FacilityType.MAIN_HOSPITAL,
            is_active=True,
        )


class BranchRequestItemForm(forms.Form):
    commodity = forms.ModelChoiceField(
        queryset=Commodity.objects.filter(status=Commodity.Status.ACTIVE).order_by("name"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    requested_quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 1}),
    )
    item_remarks = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Optional notes"}),
    )


class BranchRequestReviewForm(forms.Form):
    DECISION_CHOICES = [
        ("APPROVE", "Approve (Full or Partial)"),
        ("REJECT", "Reject Request"),
    ]
    decision = forms.ChoiceField(
        choices=DECISION_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    review_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Optional review notes"}),
    )
    rejection_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={"class": "form-control", "rows": 2, "placeholder": "Required when rejecting a request"}
        ),
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("decision") == "REJECT" and not (cleaned.get("rejection_reason") or "").strip():
            self.add_error("rejection_reason", "Provide a rejection reason when rejecting a branch request.")
        return cleaned


class StockTransferDispatchForm(forms.ModelForm):
    class Meta:
        model = StockTransfer
        fields = ["source_hospital", "destination_hospital", "dispatch_date", "notes"]
        widgets = {
            "source_hospital": forms.Select(attrs={"class": "form-select"}),
            "destination_hospital": forms.Select(attrs={"class": "form-select"}),
            "dispatch_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get("dispatch_date"):
            self.initial["dispatch_date"] = timezone.localdate().isoformat()


class DeliveryConfirmForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = ["delivery_date"]
        widgets = {
            "delivery_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get("delivery_date"):
            self.initial["delivery_date"] = timezone.localdate().isoformat()