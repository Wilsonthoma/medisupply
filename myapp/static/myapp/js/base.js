document.addEventListener("DOMContentLoaded", () => {
  const navToggle = document.getElementById("msNavToggle");
  const sidebar = document.getElementById("msSidebar");

  if (navToggle && sidebar) {
    navToggle.addEventListener("click", () => {
      const isOpen = sidebar.classList.toggle("is-open");
      navToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });

    document.addEventListener("click", (event) => {
      if (
        sidebar.classList.contains("is-open") &&
        !sidebar.contains(event.target) &&
        !navToggle.contains(event.target)
      ) {
        sidebar.classList.remove("is-open");
        navToggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  document.querySelectorAll(".ms-alert .ms-alert-close").forEach((btn) => {
    btn.addEventListener("click", () => {
      const alertEl = btn.closest(".ms-alert");
      if (alertEl) alertEl.remove();
    });
  });
});

window.MedisupplyUtils = {
  getCsrfToken() {
    const tokenInput = document.querySelector("input[name='csrfmiddlewaretoken']");
    if (tokenInput && tokenInput.value) return tokenInput.value;

    const match = document.cookie
      .split(";")
      .map((part) => part.trim())
      .find((part) => part.startsWith("csrftoken="));
    return match ? decodeURIComponent(match.split("=")[1]) : "";
  },
};