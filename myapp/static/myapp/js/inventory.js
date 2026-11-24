document.addEventListener("DOMContentLoaded", () => {
    const expiryInputs = document.querySelectorAll("input[type='date'][name$='expiry_date']");
    const hintBox = document.getElementById("msExpiryWarningHint");

    const checkExpiryDates = () => {
        if (!hintBox) return;
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const soonLimit = new Date(today);
        soonLimit.setDate(today.getDate() + 30);

        let expiredCount = 0;
        let soonCount = 0;

        expiryInputs.forEach((input) => {
            if (!input.value) return;
            const expDate = new Date(`${input.value}T00:00:00`);
            if (Number.isNaN(expDate.getTime())) return;

            if (expDate < today) {
                expiredCount += 1;
            } else if (expDate <= soonLimit) {
                soonCount += 1;
            }
        });

        if (expiredCount > 0) {
            hintBox.className = "form-text text-danger fw-semibold mb-2";
            hintBox.textContent = `Notice: ${expiredCount} batch row(s) have an expiry date in the past.`;
        } else if (soonCount > 0) {
            hintBox.className = "form-text text-warning mb-2";
            hintBox.textContent = `Notice: ${soonCount} batch row(s) expire within 30 days.`;
        } else {
            hintBox.className = "form-text text-muted mb-2";
            hintBox.textContent = "Batches are tracked by expiry date for First Expiry, First Out (FEFO) allocation.";
        }
    };

    expiryInputs.forEach((input) => {
        input.addEventListener("change", checkExpiryDates);
    });
    checkExpiryDates();
});