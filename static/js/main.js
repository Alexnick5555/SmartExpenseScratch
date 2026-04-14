/**
 * SmartExpense - Main JavaScript
 * Developed by Nitish Mishra & Nishant Singh
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize components
    initSidebar();
    initDateDisplay();
    initToastAutoClose();
    initNumberAnimations();
    initFormValidation();
    initPasswordValidation();
});

/**
 * Sidebar Toggle functionality
 */
function initSidebar() {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebarClose = document.getElementById('sidebarClose');
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const sidebarOverlay = document.getElementById('sidebarOverlay');

    // Toggle sidebar
    const toggleSidebar = () => {
        sidebar.classList.toggle('open');
        sidebar.classList.toggle('active');
        if (sidebarOverlay) sidebarOverlay.classList.toggle('active');
    };

    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', toggleSidebar);
    }
    
    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', toggleSidebar);
    }

    if (sidebarClose) {
        sidebarClose.addEventListener('click', () => {
            sidebar.classList.remove('open', 'active');
            if (sidebarOverlay) sidebarOverlay.classList.remove('active');
        });
    }
    
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', () => {
            sidebar.classList.remove('open', 'active');
            sidebarOverlay.classList.remove('active');
        });
    }

    // Close sidebar on outside click (mobile)
    document.addEventListener('click', function(e) {
        if (window.innerWidth <= 991) {
            if (!sidebar.contains(e.target) && (!mobileMenuBtn || !mobileMenuBtn.contains(e.target))) {
                sidebar.classList.remove('open', 'active');
                if (sidebarOverlay) sidebarOverlay.classList.remove('active');
            }
            }
        }
    });
}

/**
 * Display current date in header
 */
function initDateDisplay() {
    const dateElement = document.getElementById('currentDate');
    if (dateElement) {
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        const today = new Date().toLocaleDateString('en-US', options);
        dateElement.textContent = today;
    }
}

/**
 * Auto-close toast notifications
 */
function initToastAutoClose() {
    const toasts = document.querySelectorAll('.toast');
    toasts.forEach(toast => {
        setTimeout(() => {
            const bsToast = bootstrap.Toast.getOrCreateInstance(toast);
            bsToast.hide();
        }, 5000);
    });
}

/**
 * Animate number counters
 */
function initNumberAnimations() {
    const counters = document.querySelectorAll('[data-count]');

    counters.forEach(counter => {
        const target = parseFloat(counter.dataset.count);
        const duration = 1500;
        const increment = target / (duration / 16);
        let current = 0;

        const updateCounter = () => {
            current += increment;
            if (current < target) {
                counter.textContent = '₹' + Math.floor(current).toLocaleString('en-IN');
                requestAnimationFrame(updateCounter);
            } else {
                counter.textContent = '₹' + Math.floor(target).toLocaleString('en-IN');
            }
        };

        // Start animation when element is in view
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    updateCounter();
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });

        observer.observe(counter);
    });
}

/**
 * Form validation enhancement
 */
function initFormValidation() {
    const forms = document.querySelectorAll('form');

    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const container = document.querySelector('.toast-container') || createToastContainer();
    const toast = document.createElement('div');
    toast.className = `toast show align-items-center text-bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    container.appendChild(toast);

    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();

    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

/**
 * Create toast container if it doesn't exist
 */
function createToastContainer() {
    const container = document.createElement('div');
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    document.body.appendChild(container);
    return container;
}

/**
 * Format currency
 */
function formatCurrency(amount, currency = 'INR') {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: currency
    }).format(amount);
}

/**
 * Format date
 */
function formatDate(date, format = 'short') {
    const d = new Date(date);
    const options = format === 'short'
        ? { day: 'numeric', month: 'short', year: 'numeric' }
        : { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    return d.toLocaleDateString('en-US', options);
}

/**
 * Debounce function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * API request helper
 */
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                ...options.headers
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

/**
 * Password strength checker
 */
function checkPasswordStrength(password) {
    let strength = 0;
    const checks = [
        { regex: /.{8,}/, score: 1 },
        { regex: /[a-z]/, score: 1 },
        { regex: /[A-Z]/, score: 1 },
        { regex: /[0-9]/, score: 1 },
        { regex: /[^a-zA-Z0-9]/, score: 1 }
    ];
    
    checks.forEach(check => {
        if (check.regex.test(password)) {
            strength += check.score;
        }
    });
    
    return Math.min(strength, 5);
}

function updatePasswordStrengthUI(password) {
    const bar = document.getElementById('passwordStrengthBar');
    const text = document.getElementById('passwordStrengthText');
    
    if (!bar || !text) return;
    
    const strength = checkPasswordStrength(password);
    const percentage = (strength / 5) * 100;
    const colors = ['#dc3545', '#ffc107', '#ffc107', '#28a745', '#198754', '#198754'];
    const labels = ['', 'Weak', 'Fair', 'Good', 'Strong', 'Very Strong'];
    
    bar.style.width = percentage + '%';
    bar.style.backgroundColor = colors[strength];
    bar.className = 'progress-bar' + (strength >= 3 ? ' bg-success' : strength >= 2 ? ' bg-warning' : ' bg-danger');
    text.textContent = labels[strength] ? labels[strength] : '';
    text.className = 'text-muted' + (strength >= 3 ? ' text-success' : strength >= 2 ? ' text-warning' : ' text-danger');
}

function validatePasswordMatch() {
    const password1 = document.getElementById('id_password1') || document.querySelector('input[name="password1"]');
    const password2 = document.getElementById('id_password2') || document.querySelector('input[name="password2"]');
    const feedback = document.getElementById('passwordMatchFeedback');
    
    if (!password1 || !password2 || !feedback) return;
    
    if (password2.value && password1.value !== password2.value) {
        feedback.textContent = 'Passwords do not match';
        feedback.className = 'text-danger';
        password2.setCustomValidity('Passwords do not match');
    } else if (password2.value) {
        feedback.textContent = 'Passwords match';
        feedback.className = 'text-success';
        password2.setCustomValidity('');
    } else {
        feedback.textContent = '';
        password2.setCustomValidity('');
    }
}

function initPasswordValidation() {
    const password1 = document.getElementById('id_password1') || document.querySelector('input[name="password1"]');
    const password2 = document.getElementById('id_password2') || document.querySelector('input[name="password2"]');
    
    if (password1) {
        password1.addEventListener('input', function() {
            updatePasswordStrengthUI(this.value);
        });
    }
    
    if (password2) {
        password2.addEventListener('input', validatePasswordMatch);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    initPasswordValidation();
});

// Export functions for use in other scripts
window.SmartExpense = {
    showToast,
    formatCurrency,
    formatDate,
    debounce,
    apiRequest,
    checkPasswordStrength,
    updatePasswordStrengthUI,
    validatePasswordMatch
};
