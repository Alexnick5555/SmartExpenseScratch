/**
 * SmartExpense - Chart Configurations
 * Using Chart.js
 * Developed by Nitish Mishra & Nishant Singh
 */

// Chart.js default configurations
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.color = '#6B7280';

/**
 * Initialize Trend Chart (Line Chart)
 */
let trendChartInstance = null;

function initTrendChart(data) {
    const ctx = document.getElementById('trendChart');
    if (!ctx) return;
    
    // Destroy existing chart instance before creating new one
    if (trendChartInstance) {
        trendChartInstance.destroy();
        trendChartInstance = null;
    }

    if (!data || data.length === 0) {
        ctx.parentElement.innerHTML = '<div class="empty-state"><p>No trend data available</p></div>';
        return;
    }

    const labels = data.map(d => d.month);
    const incomeData = data.map(d => d.income);
    const expenseData = data.map(d => d.expense);

    // Gradient backgrounds
    const ctxIncome = ctx.getContext('2d');
    const incomeGradient = ctxIncome.createLinearGradient(0, 0, 0, 300);
    incomeGradient.addColorStop(0, 'rgba(46, 125, 50, 0.25)');
    incomeGradient.addColorStop(1, 'rgba(46, 125, 50, 0.02)');

    const expenseGradient = ctxIncome.createLinearGradient(0, 0, 0, 300);
    expenseGradient.addColorStop(0, 'rgba(229, 57, 53, 0.25)');
    expenseGradient.addColorStop(1, 'rgba(229, 57, 53, 0.02)');

    trendChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Income',
                    data: incomeData,
                    borderColor: '#10B981',
                    backgroundColor: incomeGradient,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#10B981',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 5,
                    pointHoverRadius: 8
                },
                {
                    label: 'Expenses',
                    data: expenseData,
                    borderColor: '#EF4444',
                    backgroundColor: expenseGradient,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#EF4444',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 5,
                    pointHoverRadius: 8
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 20,
                        font: { family: "'DM Sans', sans-serif", size: 12 }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(26, 26, 46, 0.95)',
                    titleFont: { family: "'DM Sans', sans-serif", size: 13, weight: '600' },
                    bodyFont: { family: "'Space Mono', monospace", size: 12 },
                    padding: 12,
                    cornerRadius: 10,
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ₹' + context.raw.toLocaleString('en-IN');
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        callback: function(value) {
                            return '₹' + value.toLocaleString('en-IN');
                        }
                    }
                }
            }
        }
    });
}

/**
 * Initialize Category Chart (Doughnut/Pie Chart)
 */
let categoryChartInstance = null;

function initCategoryChart(data) {
    const ctx = document.getElementById('categoryChart');
    if (!ctx) return;
    
    // Destroy existing chart instance before creating new one
    if (categoryChartInstance) {
        categoryChartInstance.destroy();
        categoryChartInstance = null;
    }

    // Handle null/undefined/empty data
    if (!data || !Array.isArray(data) || data.length === 0) {
        // Show empty state
        const parent = ctx.parentElement;
        if (parent) parent.innerHTML = '<div class="empty-state"><p>No expense data available</p></div>';
        return;
    }

    const labels = data.map(d => d.category__name);
    const values = data.map(d => parseFloat(d.total));
    
    // Modern color palette
    const colorPalette = [
        '#6366F1', '#8B5CF6', '#EC4899', '#EF4444', '#F59E0B', 
        '#10B981', '#06B6D4', '#3B82F6', '#84CC16', '#F97316'
    ];
    
    const colors = data.map((d, i) => d.category__color || colorPalette[i % colorPalette.length]);

    categoryChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderColor: '#fff',
                borderWidth: 3,
                hoverOffset: 15
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '60%',
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(26, 26, 46, 0.95)',
                    titleFont: { family: "'DM Sans', sans-serif", size: 13, weight: '600' },
                    bodyFont: { family: "'Space Mono', monospace", size: 12 },
                    padding: 12,
                    cornerRadius: 10,
                    callbacks: {
                        label: function(context) {
                            const value = context.raw;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return context.label + ': ₹' + value.toLocaleString('en-IN') + ' (' + percentage + '%)';
                        }
                    }
                }
            }
        }
    });
}

/**
 * Initialize Report Charts
 */
function initReportCharts(dailyData, expenseData, incomeData) {
    // Trend chart for reports page
    const trendCtx = document.getElementById('trendChart');
    if (trendCtx && dailyData && dailyData.length > 0) {
        const labels = dailyData.map(d => new Date(d.day).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
        const incomeValues = dailyData.map(d => d.income || 0);
        const expenseValues = dailyData.map(d => d.expense || 0);

        new Chart(trendCtx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Income',
                        data: incomeValues,
                        backgroundColor: 'rgba(46, 125, 50, 0.8)',
                        borderRadius: 4
                    },
                    {
                        label: 'Expenses',
                        data: expenseValues,
                        backgroundColor: 'rgba(229, 57, 53, 0.8)',
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ₹' + (context.raw || 0).toLocaleString('en-IN');
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '₹' + value.toLocaleString('en-IN');
                            }
                        }
                    }
                }
            }
        });
    }

    // Income chart
    const incomeCtx = document.getElementById('incomeChart');
    if (incomeCtx && incomeData && incomeData.length > 0) {
        const labels = incomeData.map(d => d.category__name);
        const values = incomeData.map(d => parseFloat(d.total));
        const colors = incomeData.map(d => d.category__color || '#43A047');

        new Chart(incomeCtx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            boxWidth: 12,
                            padding: 10
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.label + ': ₹' + context.raw.toLocaleString('en-IN');
                            }
                        }
                    }
                }
            }
        });
    }
}

/**
 * Create horizontal bar chart for budgets
 */
function createBudgetChart(canvasId, budgetData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: budgetData.map(b => b.category),
            datasets: [{
                label: 'Spent',
                data: budgetData.map(b => b.spent),
                backgroundColor: budgetData.map(b =>
                    b.percentage > 100 ? '#E53935' :
                    b.percentage > 80 ? '#FFC107' : '#43A047'
                ),
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '₹' + value.toLocaleString('en-IN');
                        }
                    }
                }
            }
        }
    });
}

// Export for use in other scripts
window.initTrendChart = initTrendChart;
window.initCategoryChart = initCategoryChart;
window.initReportCharts = initReportCharts;
window.createBudgetChart = createBudgetChart;
