/**
 * SmartExpense - Dashboard JavaScript
 * Developed by Nitish Mishra & Nishant Singh
 */

document.addEventListener('DOMContentLoaded', function() {
    initDashboardCharts();
    initQuickExpenseForm();
});

/**
 * Initialize dashboard-specific charts
 */
function initDashboardCharts() {
    // Charts are initialized in dashboard.html with data from server
}

/**
 * Initialize quick expense form submission
 */
function initQuickExpenseForm() {
    const form = document.getElementById('quickAddForm');
    if (!form) return;

    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Adding...';
        submitBtn.disabled = true;

        try {
            const formData = new FormData(form);
            const response = await fetch('/quick-add-expense/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                }
            });

            const data = await response.json();

            if (data.success) {
                SmartExpense.showToast(data.message, 'success');
                form.reset();
                // Reload page after short delay to show updated data
                setTimeout(() => {
                    location.reload();
                }, 1000);
            } else {
                SmartExpense.showToast(data.error || 'Failed to add expense', 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            SmartExpense.showToast('An error occurred. Please try again.', 'error');
        } finally {
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        }
    });
}

/**
 * Update dashboard data periodically
 */
function startAutoRefresh(interval = 60000) {
    setInterval(async () => {
        try {
            const response = await fetch('/get-monthly-data/?months=6');
            const data = await response.json();

            // Update charts if data changed
            if (data && data.length > 0) {
                // Trigger chart update
                window.dispatchEvent(new CustomEvent('dashboardDataUpdated', { detail: data }));
            }
        } catch (error) {
            console.error('Auto-refresh error:', error);
        }
    }, interval);
}

/**
 * Format large numbers for display
 */
function formatLargeNumber(num) {
    if (num >= 10000000) {
        return (num / 10000000).toFixed(1) + ' Cr';
    } else if (num >= 100000) {
        return (num / 100000).toFixed(1) + ' L';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + ' K';
    }
    return num.toString();
}

/**
 * Calculate savings rate
 */
function calculateSavingsRate(income, expenses) {
    if (income <= 0) return 0;
    const savings = income - expenses;
    return Math.max(0, (savings / income) * 100);
}

// Export functions
window.startAutoRefresh = startAutoRefresh;
window.formatLargeNumber = formatLargeNumber;
window.calculateSavingsRate = calculateSavingsRate;
