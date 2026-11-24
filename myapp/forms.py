from django import forms
from django.forms import BaseFormSet, formset_factory
from django.utils import timezone

from .models import (
    BranchRequest,
    Commodity,
    Hospital,
    Inventory,
)


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter username",
                "autocomplete": "username",
            }
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter password",
                "autocomplete": "current-password",
            }
        ),
    )


class ReorderLevelForm(forms.ModelForm):
    class Meta:
        model = Inventory
        fields = ["reorder_level"]
        widgets = {
            "reorder_level": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-sm ms-reorder-input",
                    "min": 0,
                }
            )
        }


class CommodityForm(forms.ModelForm):
    class Meta:
        model = Commodity
        fields = [
            "category",
            "commodity_code",
            "name",
            "unit_of_measure",
            "minimum_stock_level",
            "description",
            "status",
        ]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "commodity_code": forms.TextInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "placeholder": "e.g., MED-AMX-500",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "placeholder": "Commodity name",
                }
            ),
            "unit_of_measure": forms.TextInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "placeholder": "e.g., Pack, Box, Vial, Bottle",
                }
            ),
            "minimum_stock_level": forms.NumberInput(
                attrs={"class": "form-control form-control-sm", "min": 0}
            ),
            "description": forms.Textarea(
                attrs={"class": "form-control form-control-sm", "rows": 2}
            ),
            "status": forms.Select(attrs={"class": "form-select form-select-sm"}),
        }


class SupplierReceiptForm(forms.Form):
    receiving_hospital = forms.ModelChoiceField(
        queryset=Hospital.objects.none(),
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    supplier_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-sm",
                "placeholder": "e.g., KEMSA Central Medical Stores",
            }
        ),
    )
    receipt_date = forms.DateField(
        initial=timezone.localdate,
        widget=forms.DateInput(
            attrs={"type": "date", "class": "form-control form-control-sm"}
        ),
    )
    delivery_note_ref = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-sm",
                "placeholder": "Delivery note / waybill reference",
            }
        ),
    )
    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={"class": "form-control form-control-sm", "rows": 2}
        ),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Hospital.objects.filter(is_active=True).order_by("name")
        if (
            user
            and getattr(user, "role", None)
            and user.role.role_code == "ROLE_BRANCH_OFFICER"
            and user.hospital_id
        ):
            qs = qs.filter(pk=user.hospital_id)
        self.fields["receiving_hospital"].queryset = qs


class SupplierReceiptItemForm(forms.Form):
    commodity = forms.ModelChoiceField(
        queryset=Commodity.objects.filter(status="ACTIVE").order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    batch_number = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-sm",
                "placeholder": "Batch / Lot #",
            }
        ),
    )
    expiry_date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={"type": "date", "class": "form-control form-control-sm"}
        ),
    )
    quantity_received = forms.IntegerField(
        min_value=1,
        required=False,
        widget=forms.NumberInput(
            attrs={"class": "form-control form-control-sm", "min": 1}
        ),
    )
    unit_cost = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        required=False,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control form-control-sm",
                "step": "0.01",
                "min": 0,
            }
        ),
    )


class _BaseReceiptItemFormSet(BaseFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            commodity = form.cleaned_data.get("commodity")
            batch_number = (form.cleaned_data.get("batch_number") or "").strip()
            expiry_date = form.cleaned_data.get("expiry_date")
            qty = form.cleaned_data.get("quantity_received")
            if any([commodity, batch_number, expiry_date, qty]):
                if not all([commodity, batch_number, expiry_date, qty]):
                    raise forms.ValidationError(
                        "Each populated shipment row requires commodity, batch number, expiry date, and quantity."
                    )


SupplierReceiptItemFormSet = formset_factory(
    SupplierReceiptItemForm,
    formset=_BaseReceiptItemFormSet,
    extra=3,
    can_delete=True,
)


class BranchRequestForm(forms.Form):
    branch_hospital = forms.ModelChoiceField(
        queryset=Hospital.objects.none(),
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    target_hospital = forms.ModelChoiceField(
        queryset=Hospital.objects.none(),
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    request_date = forms.DateField(
        initial=timezone.localdate,
        widget=forms.DateInput(
            attrs={"type": "date", "class": "form-control form-control-sm"}
        ),
    )
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={"class": "form-control form-control-sm", "rows": 2}
        ),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        active_hospitals = Hospital.objects.filter(is_active=True).order_by("name")
        branch_qs = active_hospitals.filter(facility_type="BRANCH_HOSPITAL")
        target_qs = active_hospitals.filter(facility_type="MAIN_HOSPITAL")

        if (
            user
            and getattr(user, "role", None)
            and user.role.role_code == "ROLE_BRANCH_OFFICER"
            and user.hospital_id
        ):
            branch_qs = active_hospitals.filter(pk=user.hospital_id)
            user_hospital = user.hospital
            if user_hospital and user_hospital.parent_hospital_id:
                target_qs = active_hospitals.filter(pk=user_hospital.parent_hospital_id)

        self.fields["branch_hospital"].queryset = branch_qs
        self.fields["target_hospital"].queryset = target_qs


class BranchRequestItemForm(forms.Form):
    commodity = forms.ModelChoiceField(
        queryset=Commodity.objects.filter(status="ACTIVE").order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    requested_quantity = forms.IntegerField(
        min_value=1,
        required=False,
        widget=forms.NumberInput(
            attrs={"class": "form-control form-control-sm", "min": 1}
        ),
    )
    item_remarks = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control form-control-sm"}),
    )


class _BaseRequestItemFormSet(BaseFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            commodity = form.cleaned_data.get("commodity")
            qty = form.cleaned_data.get("requested_quantity")
            if (commodity and not qty) or (qty and not commodity):
                raise forms.ValidationError(
                    "Select both a commodity and requested quantity for each line item."
                )


BranchRequestItemFormSet = formset_factory(
    BranchRequestItemForm,
    formset=_BaseRequestItemFormSet,
    extra=3,
    can_delete=True,
)


class RequestReviewForm(forms.Form):
    DECISION_CHOICES = [
        ("APPROVE", "Approve"),
        ("REJECT", "Reject"),
    ]
    decision = forms.ChoiceField(
        choices=DECISION_CHOICES,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    review_notes = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control form-control-sm"}),
    )
    rejection_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={"class": "form-control form-control-sm", "rows": 2}
        ),
    )

    def __init__(self, *args, branch_request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.branch_request = branch_request
        if branch_request is not None:
            for item in branch_request.items.all():
                field_name = f"approved_qty_{item.pk}"
                self.fields[field_name] = forms.IntegerField(
                    min_value=0,
                    max_value=item.requested_quantity,
                    initial=(
                        item.approved_quantity
                        if item.approved_quantity is not None
                        else item.requested_quantity
                    ),
                    required=False,
                    widget=forms.NumberInput(
                        attrs={
                            "class": "form-control form-control-sm",
                            "min": 0,
                            "max": item.requested_quantity,
                        }
                    ),
                )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("decision") == "REJECT" and not (
            cleaned.get("rejection_reason") or ""
        ).strip():
            self.add_error(
                "rejection_reason",
                "Provide a rejection reason when rejecting a request.",
            )
        return cleaned


class StockTransferDispatchForm(forms.Form):
    source_hospital = forms.ModelChoiceField(
        queryset=Hospital.objects.none(),
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    destination_hospital = forms.ModelChoiceField(
        queryset=Hospital.objects.none(),
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    branch_request = forms.ModelChoiceField(
        queryset=BranchRequest.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    dispatch_date = forms.DateField(
        initial=timezone.localdate,
        widget=forms.DateInput(
            attrs={"type": "date", "class": "form-control form-control-sm"}
        ),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={"class": "form-control form-control-sm", "rows": 2}
        ),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        active_hospitals = Hospital.objects.filter(is_active=True).order_by("name")
        self.fields["source_hospital"].queryset = active_hospitals.filter(
            facility_type="MAIN_HOSPITAL"
        )
        self.fields["destination_hospital"].queryset = active_hospitals.filter(
            facility_type="BRANCH_HOSPITAL"
        )
        self.fields["branch_request"].queryset = BranchRequest.objects.filter(
            status__in=["APPROVED", "PARTIALLY_APPROVED"]
        ).order_by("-created_at")


class DeliveryConfirmForm(forms.Form):
    delivery_date = forms.DateField(
        initial=timezone.localdate,
        widget=forms.DateInput(
            attrs={"type": "date", "class": "form-control form-control-sm"}
        ),
    )

    def __init__(self, *args, delivery=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.delivery = delivery
        if delivery is not None:
            for item in delivery.items.all():
                qty_field = f"received_qty_{item.pk}"
                reason_field = f"discrepancy_reason_{item.pk}"
                self.fields[qty_field] = forms.IntegerField(
                    min_value=0,
                    max_value=item.dispatched_quantity,
                    initial=item.dispatched_quantity,
                    widget=forms.NumberInput(
                        attrs={
                            "class": "form-control form-control-sm",
                            "min": 0,
                            "max": item.dispatched_quantity,
                        }
                    ),
                )
                self.fields[reason_field] = forms.CharField(
                    max_length=255,
                    required=False,
                    widget=forms.TextInput(
                        attrs={"class": "form-control form-control-sm"}
                    ),
                )

    def clean(self):
        cleaned = super().clean()
        if self.delivery is not None:
            for item in self.delivery.items.all():
                qty_val = cleaned.get(f"received_qty_{item.pk}")
                reason_val = (
                    cleaned.get(f"discrepancy_reason_{item.pk}") or ""
                ).strip()
                if (
                    qty_val is not None
                    and qty_val < item.dispatched_quantity
                    and not reason_val
                ):
                    self.add_error(
                        f"discrepancy_reason_{item.pk}",
                        "Reason is required when received quantity is less than dispatched quantity.",
                    )
        return cleaned