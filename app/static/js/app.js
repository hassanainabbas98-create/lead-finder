/**
 * Business Opportunity Finder - Client Application Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // Sidebar toggle handling
    const sidebar = document.getElementById('appSidebar');
    const mainWrapper = document.getElementById('mainWrapper');
    const toggleBtn = document.getElementById('sidebarToggleBtn');

    if (toggleBtn && sidebar && mainWrapper) {
        // Restore sidebar state from localStorage
        const isCollapsed = localStorage.getItem('sidebar_collapsed') === 'true';
        if (isCollapsed && window.innerWidth > 991) {
            sidebar.classList.add('collapsed');
            mainWrapper.classList.add('expanded');
        }

        toggleBtn.addEventListener('click', () => {
            if (window.innerWidth <= 991) {
                sidebar.classList.toggle('show');
            } else {
                sidebar.classList.toggle('collapsed');
                mainWrapper.classList.toggle('expanded');
                localStorage.setItem('sidebar_collapsed', sidebar.classList.contains('collapsed'));
            }
        });
    }

    // Auto-dismiss alerts after 5s
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) bsAlert.close();
        }, 5000);
    });

    // Theme toggle handling (Light / Dark Mode)
    const themeBtn = document.getElementById('themeToggleBtn');
    const themeIcon = document.getElementById('themeToggleIcon');

    function updateThemeIcon(theme) {
        if (!themeIcon) return;
        if (theme === 'dark') {
            themeIcon.className = 'bi bi-sun-fill text-warning';
        } else {
            themeIcon.className = 'bi bi-moon-stars text-secondary';
        }
    }

    const currentTheme = localStorage.getItem('leadfinder_theme') || 'light';
    updateThemeIcon(currentTheme);

    if (themeBtn) {
        themeBtn.addEventListener('click', () => {
            const activeTheme = document.documentElement.getAttribute('data-bs-theme') || 'light';
            const nextTheme = activeTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-bs-theme', nextTheme);
            localStorage.setItem('leadfinder_theme', nextTheme);
            updateThemeIcon(nextTheme);
        });
    }
});


/**
 * Trigger a modern Bootstrap toast notification
 * @param {string} title - Header text
 * @param {string} message - Body text
 * @param {string} type - 'success', 'danger', 'warning', 'info'
 */
function showToast(title, message, type = 'success') {
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) return;

    const bgClass = type === 'success' ? 'bg-success text-white' :
                    type === 'danger' ? 'bg-danger text-white' :
                    type === 'warning' ? 'bg-warning text-dark' : 'bg-primary text-white';

    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center ${bgClass} border-0 shadow-sm mb-2`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <strong>${title}</strong><br>${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;

    toastContainer.appendChild(toastEl);
    const toast = new bootstrap.Toast(toastEl, { delay: 4500 });
    toast.show();

    toastEl.addEventListener('hidden.bs.toast', () => {
        toastEl.remove();
    });
}

/**
 * Display a confirmation modal for destructive or major actions
 */
let confirmCallback = null;

function showConfirm(title, message, onConfirm) {
    const modalEl = document.getElementById('confirmActionModal');
    if (!modalEl) {
        if (confirm(`${title}\n\n${message}`)) {
            onConfirm();
        }
        return;
    }

    document.getElementById('confirmModalTitle').textContent = title;
    document.getElementById('confirmModalBody').textContent = message;
    confirmCallback = onConfirm;

    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
}

document.addEventListener('DOMContentLoaded', () => {
    const confirmBtn = document.getElementById('confirmModalActionBtn');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', () => {
            if (typeof confirmCallback === 'function') {
                confirmCallback();
                confirmCallback = null;
            }
            const modalEl = document.getElementById('confirmActionModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
        });
    }
});
