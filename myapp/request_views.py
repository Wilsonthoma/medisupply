from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import BranchRequestForm, BranchRequestItemFormSet, RequestReviewForm
from .models import BranchRequest
from .permissions import roles_required
from .services import create_branch_request, review_branch_request


@login_required
def request_list_view(request):
    user = request.user
    qs = BranchRequest.objects.select_related(
        "branch_hospital",
        "target_hospital",
        "requested_by",
        "reviewed_by",
    ).prefetch_related("items__commodity").order_by("-created_at")

    if user.role and user.role.role_code == "ROLE_BRANCH_OFFICER" and user.hospital_id:
        qs = qs.filter(branch_hospital_id=user.hospital_id)

    return render(
        request,
        "myapp/requests/branch_requests.html",
        {"branch_requests": qs},
    )


@login_required
@roles_required("ROLE_ADMIN", "ROLE_BRANCH_OFFICER")
def create_request_view(request):
    header_form = BranchRequestForm(request.POST or None, user=request.user)
    item_formset = BranchRequestItemFormSet(request.POST or None)

    if request.method == "POST" and header_form.is_valid() and item_formset.is_valid():
        items_payload = []
        for form_item in item_formset:
            if not form_item.cleaned_data or form_item.cleaned_data.get("DELETE"):
                continue
            items_payload.append(form_item.cleaned_data)

        if not items_payload:
            messages.error(request, "Include at least one commodity item in the request.")
        else:
            try:
                branch_req = create_branch_request(
                    branch_hospital=header_form.cleaned_data["branch_hospital"],
                    target_hospital=header_form.cleaned_data["target_hospital"],
                    request_date=header_form.cleaned_data["request_date"],
                    reason=header_form.cleaned_data.get("reason", ""),
                    items=items_payload,
                    requested_by=request.user,
                )
                messages.success(
                    request,
                    f"Branch request {branch_req.request_number} submitted.",
                )
                return redirect("requests_list")
            except Exception as exc:
                messages.error(request, str(exc))

    return render(
        request,
        "myapp/requests/branch_requests.html",
        {
            "header_form": header_form,
            "item_formset": item_formset,
            "branch_requests": BranchRequest.objects.select_related(
                "branch_hospital", "target_hospital", "requested_by"
            ).order_by("-created_at")[:10],
        },
    )


@login_required
@roles_required("ROLE_ADMIN", "ROLE_HOSPITAL_ADMIN", "ROLE_WAREHOUSE")
def review_request_view(request, request_id):
    branch_request = get_object_or_404(
        BranchRequest.objects.select_related("branch_hospital", "target_hospital")
        .prefetch_related("items__commodity"),
        pk=request_id,
    )
    form = RequestReviewForm(request.POST or None, branch_request=branch_request)

    if request.method == "POST" and form.is_valid():
        decision = form.cleaned_data["decision"]
        approved_quantities = {}
        for item in branch_request.items.all():
            field_name = f"approved_qty_{item.pk}"
            if field_name in form.cleaned_data and form.cleaned_data[field_name] is not None:
                approved_quantities[item.pk] = form.cleaned_data[field_name]

        try:
            review_branch_request(
                branch_request=branch_request,
                decision=decision,
                approved_quantities=approved_quantities,
                review_notes=form.cleaned_data.get("review_notes", ""),
                rejection_reason=form.cleaned_data.get("rejection_reason", ""),
                reviewed_by=request.user,
            )
            messages.success(
                request,
                f"Request {branch_request.request_number} processed ({decision}).",
            )
            return redirect("requests_list")
        except Exception as exc:
            messages.error(request, str(exc))

    return render(
        request,
        "myapp/requests/request_approvals.html",
        {
            "branch_request": branch_request,
            "form": form,
        },
    )