/**
 * EcoTrack — main.js
 * Global utilities: alerts, helpers, active nav link.
 */

// ---- Active nav link highlight ----
document.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname;
    document.querySelectorAll('.navbar-links a').forEach(link => {
        if (link.getAttribute('href') === path) {
            link.classList.add('active');
        }
    });

    // Set default month input to current month
    document.querySelectorAll('input[type="month"]').forEach(input => {
        if (!input.value) {
            const now = new Date();
            const y = now.getFullYear();
            const m = String(now.getMonth() + 1).padStart(2, '0');
            input.value = `${y}-${m}`;
        }
    });
});

// ---- Alert helpers ----

/**
 * Show an alert message inside #alert-container.
 * @param {string} message
 * @param {'success'|'error'|'warning'|'info'} type
 */
function showAlert(message, type = 'info') {
    const container = document.getElementById('alert-container');
    if (!container) return;

    const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
    container.innerHTML = `
    <div class="alert alert-${type}">
      ${icons[type] || 'ℹ️'} ${message}
    </div>`;

    // Auto-clear after 6 seconds
    setTimeout(() => { container.innerHTML = ''; }, 6000);
}

function clearAlert() {
    const container = document.getElementById('alert-container');
    if (container) container.innerHTML = '';
}

// ---- Number formatting ----
function fmt(value, decimals = 1) {
    const num = parseFloat(value);
    if (isNaN(num)) return '—';
    return num.toFixed(decimals);
}

// ---- Quality badge HTML ----
function qualityBadgeHTML(rating) {
    const map = {
        'High': { cls: 'quality-high', icon: '✅' },
        'Medium': { cls: 'quality-medium', icon: '⚡' },
        'Low': { cls: 'quality-low', icon: '⚠️' }
    };
    const { cls, icon } = map[rating] || { cls: 'quality-medium', icon: '—' };
    return `<span class="quality-badge ${cls}">${icon} ${rating}</span>`;
}
