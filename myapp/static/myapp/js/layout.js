document.addEventListener("DOMContentLoaded", () => {
    const tables = document.querySelectorAll(".table");
    tables.forEach((table) => {
        if (!table.closest(".table-responsive")) {
            const wrapper = document.createElement("div");
            wrapper.className = "table-responsive";
            table.parentNode.insertBefore(wrapper, table);
            wrapper.appendChild(table);
        }
    });
});