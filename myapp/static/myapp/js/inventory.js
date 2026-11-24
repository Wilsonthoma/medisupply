document.addEventListener("DOMContentLoaded", () => {
  const searchInput = document.getElementById("msInventorySearch");
  const statusSelect = document.getElementById("msExpiryFilter");
  const rows = document.querySelectorAll("tbody tr[data-batch-row]");

  const applyFilters = () => {
    const query = searchInput ? searchInput.value.trim().toLowerCase() : "";
    const expiryState = statusSelect ? statusSelect.value : "all";

    rows.forEach((row) => {
      const textMatch = row.textContent.toLowerCase().includes(query);
      const rowState = row.getAttribute("data-expiry-status") || "ok";
      const statusMatch = expiryState === "all" || rowState === expiryState;
      row.style.display = textMatch && statusMatch ? "" : "none";
    });
  };

  if (searchInput) searchInput.addEventListener("input", applyFilters);
  if (statusSelect) statusSelect.addEventListener("change", applyFilters);
});