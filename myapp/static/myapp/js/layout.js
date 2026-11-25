document.addEventListener("DOMContentLoaded", () => {
    const navToggle = document.getElementById("msNavToggle");
    const sidebar = document.getElementById("msSidebar");
    const navGroups = Array.from(document.querySelectorAll(".ms-nav-group"));
    const profileMenu = document.getElementById("msProfileMenu");
    const profileTrigger = document.getElementById("msProfileTrigger");

    function closeAllGroups(exceptGroup = null) {
        navGroups.forEach((group) => {
            if (group !== exceptGroup) {
                group.classList.remove("is-open");
                const trigger = group.querySelector(".ms-nav-trigger");
                if (trigger) {
                    trigger.setAttribute("aria-expanded", "false");
                }
            }
        });
    }

    function closeProfileMenu() {
        if (!profileMenu || !profileTrigger) return;
        profileMenu.classList.remove("is-open");
        profileTrigger.setAttribute("aria-expanded", "false");
    }

    if (navToggle && sidebar) {
        navToggle.addEventListener("click", (event) => {
            event.stopPropagation();
            const isOpen = sidebar.classList.toggle("is-open");
            navToggle.setAttribute("aria-expanded", String(isOpen));
        });
    }

    navGroups.forEach((group) => {
        const trigger = group.querySelector(".ms-nav-trigger");
        if (!trigger) return;

        group.addEventListener("mouseenter", () => {
            closeAllGroups(group);
            trigger.setAttribute("aria-expanded", "true");
        });

        group.addEventListener("mouseleave", () => {
            group.classList.remove("is-open");
            trigger.setAttribute("aria-expanded", "false");
            if (document.activeElement && group.contains(document.activeElement)) {
                document.activeElement.blur();
            }
        });

        trigger.addEventListener("click", (event) => {
            event.stopPropagation();
            const willOpen = !group.classList.contains("is-open");
            closeAllGroups(willOpen ? group : null);
            closeProfileMenu();
            group.classList.toggle("is-open", willOpen);
            trigger.setAttribute("aria-expanded", String(willOpen));
        });
    });

    if (profileMenu && profileTrigger) {
        profileTrigger.addEventListener("click", (event) => {
            event.stopPropagation();
            const willOpen = !profileMenu.classList.contains("is-open");
            closeAllGroups();
            profileMenu.classList.toggle("is-open", willOpen);
            profileTrigger.setAttribute("aria-expanded", String(willOpen));
        });
    }

    document.addEventListener("click", (event) => {
        if (!event.target.closest(".ms-nav-group")) {
            closeAllGroups();
        }

        if (!event.target.closest("#msProfileMenu")) {
            closeProfileMenu();
        }

        if (
            sidebar &&
            navToggle &&
            sidebar.classList.contains("is-open") &&
            !sidebar.contains(event.target) &&
            !navToggle.contains(event.target)
        ) {
            sidebar.classList.remove("is-open");
            navToggle.setAttribute("aria-expanded", "false");
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeAllGroups();
            closeProfileMenu();
            if (sidebar && navToggle && sidebar.classList.contains("is-open")) {
                sidebar.classList.remove("is-open");
                navToggle.setAttribute("aria-expanded", "false");
            }
        }
    });

    document.querySelectorAll(".ms-alert-close").forEach((btn) => {
        btn.addEventListener("click", () => {
            const alertEl = btn.closest(".ms-alert");
            if (alertEl) {
                alertEl.remove();
            }
        });
    });
});