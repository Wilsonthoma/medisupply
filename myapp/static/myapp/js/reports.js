document.addEventListener("DOMContentLoaded", () => {
    const reportTables = document.querySelectorAll(".table");
    reportTables.forEach((table) => {
        table.classList.add("ms-report-table");
    });

    const filterForm = document.querySelector("form[method='get']");
    const movementSelect = filterForm
        ? filterForm.querySelector("select[name='movement_type']")
        : null;
    if (filterForm && movementSelect) {
        movementSelect.addEventListener("change", () => {
            filterForm.submit();
        });
    }
});