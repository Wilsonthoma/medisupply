document.addEventListener("DOMContentLoaded", () => {
    const filterInput = document.getElementById("msFacilityFilterInput");
    if (!filterInput) return;

    const rows = document.querySelectorAll("tbody tr[data-facility-name]");
    filterInput.addEventListener("input", () => {
        const query = filterInput.value.trim().toLowerCase();
        rows.forEach((row) => {
            const label = (row.getAttribute("data-facility-name") || "").toLowerCase();
            row.style.display = !query || label.includes(query) ? "" : "none";
        });
    });
});