/**
 * SmartExpense - Dashboard JavaScript
 * Developed by Nitish Mishra & Nishant Singh
 */

document.addEventListener('DOMContentLoaded', function() {
    initDashboardCharts();
    initQuickExpenseForm();
    initQuickAddVoice();
});

function initQuickAddVoice() {
    if (typeof VoiceInput !== 'undefined') {
        const btn = VoiceInput.createButton({
            categorySelector: '[name="category"]',
            mode: 'quick',
            onResult: function(result) {
                console.log('Voice result:', result);
                const amountInput = document.querySelector('[name="amount"]');
                const descInput = document.querySelector('[name="description"]');
                const catSelect = document.querySelector('[name="category"]');
                
                if (result.amount && amountInput) {
                    amountInput.value = result.amount;
                    amountInput.dispatchEvent(new Event('input', { bubbles: true }));
                }
                if (result.description && descInput) {
                    descInput.value = result.description;
                    descInput.dispatchEvent(new Event('input', { bubbles: true }));
                }
                if (result.categoryValue && catSelect) {
                    catSelect.value = result.categoryValue;
                    catSelect.dispatchEvent(new Event('change', { bubbles: true }));
                }
                if (result.amount || result.description) {
                    SmartExpense.showToast('Voice input applied!', 'success');
                }
            }
        });
        const container = document.getElementById('dashVoiceBtnContainer');
        if (container && btn) {
            btn.style.background = 'rgba(255,255,255,0.2)';
            btn.style.boxShadow = 'none';
            btn.style.border = '1px solid rgba(255,255,255,0.4)';
            container.appendChild(btn);
        }
    }
}

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

    let isSubmitting = false;

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        e.stopPropagation();

        if (isSubmitting) {
            console.log('Already submitting, ignoring duplicate');
            return;
        }
        isSubmitting = true;

        const submitBtn = form.querySelector('button[type="submit"]');
        if (!submitBtn) {
            isSubmitting = false;
            return;
        }
        
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
                setTimeout(() => {
                    if (data.transaction_id) {
                        window.location.href = window.location.pathname + '?added=' + data.transaction_id;
                    } else {
                        window.location.reload();
                    }
                }, 1200);
            } else {
                SmartExpense.showToast(data.error || 'Failed to add expense', 'error');
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
                isSubmitting = false;
            }
        } catch (error) {
            console.error('Error:', error);
            SmartExpense.showToast('An error occurred. Please try again.', 'error');
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
            isSubmitting = false;
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

            if (data && data.length > 0) {
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
