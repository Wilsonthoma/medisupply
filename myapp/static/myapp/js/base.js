document.addEventListener("DOMContentLoaded", () => {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll(".ms-navbar .nav-link");

    navLinks.forEach((link) => {
        const href = link.getAttribute("href");
        if (!href) return;
        if (href === currentPath || (href !== "/" && currentPath.startsWith(href))) {
            link.classList.add("active");
            link.setAttribute("aria-current", "page");
        }
    });

    const autoDismissAlerts = document.querySelectorAll(".ms-auto-dismiss");
    autoDismissAlerts.forEach((alertEl) => {
        window.setTimeout(() => {
            if (window.bootstrap && window.bootstrap.Alert) {
                const instance = window.bootstrap.Alert.getOrCreateInstance(alertEl);
                instance.close();
            } else {
                alertEl.remove();
            }
        }, 6000);
    });
});