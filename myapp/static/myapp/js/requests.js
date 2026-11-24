document.addEventListener("DOMContentLoaded", () => {
    const decisionSelect = document.getElementById("id_decision");
    const rejectionGroup = document.getElementById("msRejectionReasonGroup");
    const rejectionTextarea = document.getElementById("id_rejection_reason");

    if (!decisionSelect || !rejectionGroup) return;

    const syncRejectionVisibility = () => {
        const isReject = decisionSelect.value === "REJECT";
        rejectionGroup.style.display = isReject ? "block" : "none";
        if (rejectionTextarea) {
            rejectionTextarea.required = isReject;
        }
    };

    decisionSelect.addEventListener("change", syncRejectionVisibility);
    syncRejectionVisibility();
});