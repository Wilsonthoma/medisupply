document.addEventListener("DOMContentLoaded", () => {
  const filterInput = document.getElementById("msDashboardFilter");
  const rows = document.querySelectorAll("[data-dash-row]");

  if (filterInput && rows.length) {
    filterInput.addEventListener("input", () => {
      const term = filterInput.value.trim().toLowerCase();
      rows.forEach((row) => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(term) ? "" : "none";
      });
    });
  }

  document.querySelectorAll("[data-mark-read-url]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const url = btn.getAttribute("data-mark-read-url");
      const csrfToken = window.MedisupplyUtils ? window.MedisupplyUtils.getCsrfToken() : "";
      if (!url || !csrfToken) return;

      try {
        const response = await fetch(url, {
          method: "POST",
          headers: {
            "X-CSRFToken": csrfToken,
            "X-Requested-With": "XMLHttpRequest",
          },
        });
        if (response.ok) {
          const item = btn.closest(".ms-notif-item");
          if (item) item.classList.remove("is-unread");
          btn.disabled = true;
          btn.textContent = "Read";
        }
      } catch (error) {
        console.error("Failed to mark notification as read:", error);
      }
    });
  });
});