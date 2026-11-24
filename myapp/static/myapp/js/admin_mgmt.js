document.addEventListener("DOMContentLoaded", () => {
    const sectionHeadings = document.querySelectorAll("h2.h6");
    sectionHeadings.forEach((heading) => {
        heading.classList.add("ms-admin-section-title");
    });

    const statusCells = document.querySelectorAll("tbody tr td:last-child");
    statusCells.forEach((cell) => {
        const text = cell.textContent.trim();
        if (text === "Active" || text === "Inactive") {
            cell.classList.add("fw-semibold");
            cell.classList.add(text === "Active" ? "text-success" : "text-muted");
        }
    });
});