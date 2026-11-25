document.addEventListener("DOMContentLoaded", () => {
    const toggleBtn = document.getElementById("msTogglePasswordSupport");
    const supportBox = document.getElementById("msPasswordSupportBox");
    const supportForm = document.getElementById("msPasswordSupportForm");

    if (toggleBtn && supportBox) {
        toggleBtn.addEventListener("click", () => {
            const isHidden = supportBox.classList.toggle("d-none");
            toggleBtn.setAttribute("aria-expanded", String(!isHidden));
            if (!isHidden) {
                const usernameInput = document.getElementById("id_support_username");
                if (usernameInput) {
                    usernameInput.focus();
                }
            }
        });
    }

    if (supportForm) {
        supportForm.addEventListener("submit", (event) => {
            const username = document.getElementById("id_support_username");
            const email = document.getElementById("id_support_email");
            const notes = document.getElementById("id_support_notes");

            let valid = true;
            [username, email, notes].forEach((field) => {
                if (!field) return;
                const empty = !field.value.trim();
                field.classList.toggle("is-invalid", empty);
                if (empty) {
                    valid = false;
                }
            });

            if (!valid) {
                event.preventDefault();
            }
        });
    }
});