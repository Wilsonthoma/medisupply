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

  const loginForm = document.getElementById("msLoginForm");
  if (!loginForm) return;

  loginForm.addEventListener("submit", (event) => {
    const usernameInput = loginForm.querySelector("input[name='username']");
    const passwordInput = loginForm.querySelector("input[name='password']");
    const hasUsername = Boolean(usernameInput && usernameInput.value.trim().length > 0);
    const hasPassword = Boolean(passwordInput && passwordInput.value.length > 0);

    if (!hasUsername || !hasPassword) {
      event.preventDefault();
      if (usernameInput && !hasUsername) usernameInput.classList.add("is-invalid");
      if (passwordInput && !hasPassword) passwordInput.classList.add("is-invalid");
    }
  });

  loginForm.querySelectorAll("input").forEach((input) => {
    input.addEventListener("input", () => {
      input.classList.remove("is-invalid");
    });
  });
});