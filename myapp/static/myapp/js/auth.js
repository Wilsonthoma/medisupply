document.addEventListener("DOMContentLoaded", () => {
    const toggleButtons = document.querySelectorAll(".ms-toggle-password");

    toggleButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-target");
            const input = targetId ? document.getElementById(targetId) : null;
            if (!input) return;

            const reveal = input.type === "password";
            input.type = reveal ? "text" : "password";
            btn.textContent = reveal ? "Hide" : "Show";
            btn.setAttribute("aria-pressed", reveal ? "true" : "false");
        });
    });

    const loginForm = document.querySelector("form[action*='login']");
    if (loginForm) {
        loginForm.addEventListener("submit", (event) => {
            const usernameInput = loginForm.querySelector("input[name='username']");
            const passwordInput = loginForm.querySelector("input[name='password']");
            const hasUsername = usernameInput && usernameInput.value.trim().length > 0;
            const hasPassword = passwordInput && passwordInput.value.length > 0;

            if (!hasUsername || !hasPassword) {
                event.preventDefault();
                if (usernameInput && !hasUsername) usernameInput.classList.add("is-invalid");
                if (passwordInput && !hasPassword) passwordInput.classList.add("is-invalid");
            }
        });
    }
});