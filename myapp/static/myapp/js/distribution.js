document.addEventListener("DOMContentLoaded", () => {
    const receivedInputs = document.querySelectorAll("input[data-dispatched-qty]");

    receivedInputs.forEach((input) => {
        const recalculate = () => {
            const dispatched = parseInt(input.getAttribute("data-dispatched-qty") || "0", 10);
            const rawReceived = parseInt(input.value || "0", 10);
            const received = Number.isNaN(rawReceived) ? 0 : Math.max(0, rawReceived);
            const discrepancy = Math.max(0, dispatched - received);

            const diffTargetId = input.getAttribute("data-diff-target");
            const diffEl = diffTargetId ? document.getElementById(diffTargetId) : null;
            if (diffEl) {
                diffEl.textContent = String(discrepancy);
                diffEl.classList.toggle("text-danger", discrepancy > 0);
                diffEl.classList.toggle("fw-bold", discrepancy > 0);
            }

            const row = input.closest("tr");
            const reasonInput = row
                ? row.querySelector("input[name^='discrepancy_reason_']")
                : null;
            if (reasonInput) {
                reasonInput.required = discrepancy > 0;
            }
        };

        input.addEventListener("input", recalculate);
        input.addEventListener("change", recalculate);
        recalculate();
    });
});