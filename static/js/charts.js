/**
 * SENAI Morvan Figueiredo - Sistema de Aquisições
 * Chart.js configurations and utilities
 */

// Global Chart.js defaults
Chart.defaults.font.family = "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif";
Chart.defaults.font.size = 12;
Chart.defaults.color = '#333';
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.boxWidth = 20;

// Custom chart configurations
const ChartConfigs = {
    // Common options for all charts
    commonOptions: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom',
                labels: {
                    padding: 20,
                    font: {
                        size: 11
                    }
                }
            },
            tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                titleColor: '#fff',
                bodyColor: '#fff',
                borderColor: '#1e4a6b',
                borderWidth: 1,
                cornerRadius: 6,
                displayColors: true
            }
        },
        animation: {
            duration: 1000,
            easing: 'easeInOutQuart'
        }
    },
    
    // Pie/Doughnut chart options
    pieOptions: {
        cutout: '60%',
        plugins: {
            legend: {
                position: 'bottom',
                labels: {
                    generateLabels: function(chart) {
                        const data = chart.data;
                        if (data.labels.length && data.datasets.length) {
                            const dataset = data.datasets[0];
                            const total = dataset.data.reduce((a, b) => a + b, 0);
                            
                            return data.labels.map((label, i) => {
                                const value = dataset.data[i];
                                const percentage = ((value / total) * 100).toFixed(1);
                                
                                return {
                                    text: `${label} (${percentage}%)`,
                                    fillStyle: dataset.backgroundColor[i],
                                    hidden: false,
                                    index: i
                                };
                            });
                        }
                        return [];
                    }
                }
            },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                        const percentage = ((context.parsed / total) * 100).toFixed(1);
                        const value = typeof context.parsed === 'number' ? 
                            context.parsed.toLocaleString('pt-BR') : context.parsed;
                        return `${context.label}: ${value} (${percentage}%)`;
                    }
                }
            }
        }
    },
    
    // Line chart options
    lineOptions: {
        scales: {
            x: {
                grid: {
                    display: false
                },
                ticks: {
                    font: {
                        size: 11
                    }
                }
            },
            y: {
                beginAtZero: true,
                grid: {
                    color: 'rgba(0, 0, 0, 0.1)'
                },
                ticks: {
                    font: {
                        size: 11
                    }
                }
            }
        },
        elements: {
            line: {
                tension: 0.4,
                borderWidth: 3
            },
            point: {
                radius: 5,
                hoverRadius: 8
            }
        }
    },
    
    // Bar chart options
    barOptions: {
        scales: {
            x: {
                grid: {
                    display: false
                },
                ticks: {
                    font: {
                        size: 11
                    }
                }
            },
            y: {
                beginAtZero: true,
                grid: {
                    color: 'rgba(0, 0, 0, 0.1)'
                },
                ticks: {
                    font: {
                        size: 11
                    }
                }
            }
        },
        elements: {
            bar: {
                borderRadius: 4,
                borderSkipped: false
            }
        }
    }
};

// Chart creation functions
const ChartFactory = {
    // Create a type distribution pie chart
    createTypeChart: function(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        
        const config = {
            type: 'doughnut',
            data: data,
            options: {
                ...ChartConfigs.commonOptions,
                ...ChartConfigs.pieOptions,
                plugins: {
                    ...ChartConfigs.commonOptions.plugins,
                    ...ChartConfigs.pieOptions.plugins,
                    title: {
                        display: false
                    }
                }
            }
        };
        
        return new Chart(ctx, config);
    },
    
    // Create a status distribution chart
    createStatusChart: function(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        
        // Assign colors based on status
        const statusColors = {
            'Em Analise': '#ffc107',
            'Aprovado': '#198754',
            'Em Cotacao': '#0dcaf0',
            'Pedido Realizado': '#1e4a6b',
            'Recebido': '#28a745',
            'Fechado': '#6c757d'
        };
        
        data.datasets[0].backgroundColor = data.labels.map(label => 
            statusColors[label] || ChartColors.senai
        );
        
        const config = {
            type: 'bar',
            data: data,
            options: {
                ...ChartConfigs.commonOptions,
                ...ChartConfigs.barOptions,
                plugins: {
                    ...ChartConfigs.commonOptions.plugins,
                    legend: {
                        display: false
                    },
                    tooltip: {
                        ...ChartConfigs.commonOptions.plugins.tooltip,
                        callbacks: {
                            label: function(context) {
                                return `${context.label}: ${context.parsed.y} solicitações`;
                            }
                        }
                    }
                },
                scales: {
                    ...ChartConfigs.barOptions.scales,
                    y: {
                        ...ChartConfigs.barOptions.scales.y,
                        ticks: {
                            ...ChartConfigs.barOptions.scales.y.ticks,
                            stepSize: 1,
                            callback: function(value) {
                                return Number.isInteger(value) ? value : '';
                            }
                        }
                    }
                }
            }
        };
        
        return new Chart(ctx, config);
    },
    
    // Create a monthly spending line chart
    createMonthlyChart: function(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        
        const config = {
            type: 'line',
            data: data,
            options: {
                ...ChartConfigs.commonOptions,
                ...ChartConfigs.lineOptions,
                plugins: {
                    ...ChartConfigs.commonOptions.plugins,
                    tooltip: {
                        ...ChartConfigs.commonOptions.plugins.tooltip,
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                const value = context.parsed.y;
                                const formatted = value.toLocaleString('pt-BR', {
                                    style: 'currency',
                                    currency: 'BRL'
                                });
                                return `${context.dataset.label}: ${formatted}`;
                            }
                        }
                    }
                },
                scales: {
                    ...ChartConfigs.lineOptions.scales,
                    y: {
                        ...ChartConfigs.lineOptions.scales.y,
                        ticks: {
                            ...ChartConfigs.lineOptions.scales.y.ticks,
                            callback: function(value) {
                                return value.toLocaleString('pt-BR', {
                                    style: 'currency',
                                    currency: 'BRL',
                                    minimumFractionDigits: 0,
                                    maximumFractionDigits: 0
                                });
                            }
                        }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        };
        
        return new Chart(ctx, config);
    },
    
    // Create a cost center comparison chart
    createCostCenterChart: function(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        
        // Use color palette for multiple categories
        if (data.datasets && data.datasets[0]) {
            data.datasets[0].backgroundColor = ChartColors.getColorPalette(data.labels.length);
        }
        
        const config = {
            type: 'doughnut',
            data: data,
            options: {
                ...ChartConfigs.commonOptions,
                ...ChartConfigs.pieOptions,
                plugins: {
                    ...ChartConfigs.commonOptions.plugins,
                    ...ChartConfigs.pieOptions.plugins,
                    tooltip: {
                        ...ChartConfigs.pieOptions.plugins.tooltip,
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.parsed / total) * 100).toFixed(1);
                                const value = context.parsed.toLocaleString('pt-BR', {
                                    style: 'currency',
                                    currency: 'BRL'
                                });
                                return `${context.label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        };
        
        return new Chart(ctx, config);
    }
};

// Chart utility functions
const ChartUtils = {
    // Update chart data
    updateChartData: function(chart, newData) {
        chart.data = newData;
        chart.update('active');
    },
    
    // Animate chart on scroll
    animateOnScroll: function(chartId) {
        const chart = Chart.getChart(chartId);
        if (!chart) return;
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    chart.update('active');
                    observer.unobserve(entry.target);
                }
            });
        });
        
        observer.observe(chart.canvas);
    },
    
    // Export chart as image
    exportChart: function(chartId, filename = 'chart.png') {
        const chart = Chart.getChart(chartId);
        if (!chart) return;
        
        const url = chart.toBase64Image();
        const link = document.createElement('a');
        link.download = filename;
        link.href = url;
        link.click();
    },
    
    // Print chart
    printChart: function(chartId) {
        const chart = Chart.getChart(chartId);
        if (!chart) return;
        
        const url = chart.toBase64Image();
        const windowContent = `
            <!DOCTYPE html>
            <html>
            <head>
                <title>Gráfico - SENAI Morvan Figueiredo</title>
                <style>
                    body { margin: 0; padding: 20px; text-align: center; }
                    img { max-width: 100%; height: auto; }
                    .header { margin-bottom: 20px; }
                    .footer { margin-top: 20px; font-size: 12px; color: #666; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>SENAI Morvan Figueiredo</h1>
                    <h2>Sistema de Acompanhamento de Aquisições</h2>
                </div>
                <img src="${url}" alt="Gráfico">
                <div class="footer">
                    Gerado em: ${new Date().toLocaleString('pt-BR')}
                </div>
            </body>
            </html>
        `;
        
        const printWindow = window.open('', '_blank');
        printWindow.document.write(windowContent);
        printWindow.document.close();
        printWindow.focus();
        printWindow.print();
        printWindow.close();
    }
};

// Global functions for easy access
window.initTypeChart = ChartFactory.createTypeChart;
window.initStatusChart = ChartFactory.createStatusChart;
window.initMonthlyChart = ChartFactory.createMonthlyChart;
window.initCostCenterChart = ChartFactory.createCostCenterChart;

// Auto-initialize charts on page load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize any charts that have data attributes
    document.querySelectorAll('canvas[data-chart-type]').forEach(canvas => {
        const chartType = canvas.dataset.chartType;
        const chartData = canvas.dataset.chartData;
        
        if (chartData) {
            try {
                const data = JSON.parse(chartData);
                switch (chartType) {
                    case 'type':
                        ChartFactory.createTypeChart(canvas.id, data);
                        break;
                    case 'status':
                        ChartFactory.createStatusChart(canvas.id, data);
                        break;
                    case 'monthly':
                        ChartFactory.createMonthlyChart(canvas.id, data);
                        break;
                    case 'cost-center':
                        ChartFactory.createCostCenterChart(canvas.id, data);
                        break;
                }
            } catch (error) {
                console.error('Error parsing chart data:', error);
            }
        }
    });
    
    // Setup chart export buttons
    document.querySelectorAll('[data-chart-export]').forEach(button => {
        button.addEventListener('click', function() {
            const chartId = this.dataset.chartExport;
            const filename = this.dataset.filename || 'chart.png';
            ChartUtils.exportChart(chartId, filename);
        });
    });
    
    // Setup chart print buttons
    document.querySelectorAll('[data-chart-print]').forEach(button => {
        button.addEventListener('click', function() {
            const chartId = this.dataset.chartPrint;
            ChartUtils.printChart(chartId);
        });
    });
});

// Export for use in other scripts
window.ChartFactory = ChartFactory;
window.ChartUtils = ChartUtils;
window.ChartConfigs = ChartConfigs;
