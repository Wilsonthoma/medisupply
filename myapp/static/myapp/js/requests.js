document.addEventListener("DOMContentLoaded", () => {
  const statusFilter = document.getElementById("msRequisitionStatusFilter");
  const searchInput = document.getElementById("msRequisitionSearch");
  const rows = document.querySelectorAll("tbody tr[data-req-row]");

  const filterRequisitions = () => {
    const query = searchInput ? searchInput.value.trim().toLowerCase() : "";
    const status = statusFilter ? statusFilter.value.toLowerCase() : "all";

    rows.forEach((row) => {
      const textMatch = row.textContent.toLowerCase().includes(query);
      const rowStatus = (row.getAttribute("data-req-status") || "").toLowerCase();
      const statusMatch = status === "all" || rowStatus === status;
      row.style.display = textMatch && statusMatch ? "" : "none";
    });
  };

  if (statusFilter) statusFilter.addEventListener("change", filterRequisitions);
  if (searchInput) searchInput.addEventListener("input", filterRequisitions);

  document.querySelectorAll("form[data-confirm-action]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const message = form.getAttribute("data-confirm-action") || "Confirm this requisition action?";
      if (!window.confirm(message)) {
        event.preventDefault();
      }
    });
  });
});