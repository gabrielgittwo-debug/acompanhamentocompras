/**
 * SENAI Morvan Figueiredo - Sistema de Aquisições
 * Main JavaScript application file
 */

// Global application configuration
const SenaiApp = {
    config: {
        dateFormat: 'DD/MM/YYYY',
        currencyFormat: 'R$ #,##0.00',
        timeoutDuration: 300000, // 5 minutes
        maxFileSize: 16 * 1024 * 1024 // 16MB
    },
    
    // Initialize the application
    init: function() {
        this.setupEventListeners();
        this.initializeTooltips();
        this.setupFormValidation();
        this.initializeCurrencyInputs();
        this.setupFileUploadValidation();
        this.initializeSessionTimeout();
        console.log('SENAI Sistema de Aquisições initialized');
    },
    
    // Setup global event listeners
    setupEventListeners: function() {
        // Auto-dismiss alerts after 5 seconds
        document.querySelectorAll('.alert-dismissible').forEach(alert => {
            setTimeout(() => {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, 5000);
        });
        
        // Smooth scrolling for anchor links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
        
        // Loading states for forms
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', function() {
                const submitBtn = this.querySelector('button[type="submit"]');
                if (submitBtn) {
                    submitBtn.disabled = true;
                    const originalText = submitBtn.innerHTML;
                    submitBtn.innerHTML = '<span class="loading-spinner me-2"></span>Processando...';
                    
                    // Re-enable after 10 seconds as fallback
                    setTimeout(() => {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalText;
                    }, 10000);
                }
            });
        });
        
        // Enhanced table interactions
        this.setupTableEnhancements();
        
        // Search functionality
        this.setupSearchFeatures();
    },
    
    // Initialize Bootstrap tooltips
    initializeTooltips: function() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    },
    
    // Setup form validation
    setupFormValidation: function() {
        // Custom validation for required fields
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', function(event) {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                    
                    // Focus on first invalid field
                    const firstInvalid = form.querySelector(':invalid');
                    if (firstInvalid) {
                        firstInvalid.focus();
                        firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                }
                form.classList.add('was-validated');
            });
        });
        
        // Real-time validation feedback
        document.querySelectorAll('input[required], textarea[required], select[required]').forEach(field => {
            field.addEventListener('blur', function() {
                this.classList.add('was-validated');
            });
            
            field.addEventListener('input', function() {
                if (this.checkValidity()) {
                    this.classList.remove('is-invalid');
                    this.classList.add('is-valid');
                } else {
                    this.classList.remove('is-valid');
                    this.classList.add('is-invalid');
                }
            });
        });
    },
    
    // Initialize currency input formatting
    initializeCurrencyInputs: function() {
        document.querySelectorAll('input[type="number"][step="0.01"]').forEach(input => {
            input.addEventListener('blur', function() {
                if (this.value) {
                    const value = parseFloat(this.value);
                    if (!isNaN(value)) {
                        this.value = value.toFixed(2);
                    }
                }
            });
            
            input.addEventListener('input', function() {
                // Remove non-numeric characters except decimal point
                this.value = this.value.replace(/[^0-9.]/g, '');
                
                // Ensure only one decimal point
                const parts = this.value.split('.');
                if (parts.length > 2) {
                    this.value = parts[0] + '.' + parts.slice(1).join('');
                }
            });
        });
    },
    
    // Setup file upload validation
    setupFileUploadValidation: function() {
        document.querySelectorAll('input[type="file"]').forEach(input => {
            input.addEventListener('change', function() {
                const file = this.files[0];
                if (file) {
                    // Check file size
                    if (file.size > SenaiApp.config.maxFileSize) {
                        alert('Arquivo muito grande. Tamanho máximo: 16MB');
                        this.value = '';
                        return;
                    }
                    
                    // Check file type (basic validation)
                    const allowedTypes = [
                        'application/pdf',
                        'application/msword',
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        'application/vnd.ms-excel',
                        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        'image/jpeg',
                        'image/png',
                        'image/gif'
                    ];
                    
                    if (!allowedTypes.includes(file.type)) {
                        alert('Tipo de arquivo não permitido. Use: PDF, DOC, DOCX, XLS, XLSX, JPG, PNG, GIF');
                        this.value = '';
                        return;
                    }
                    
                    // Show file info
                    const fileInfo = document.createElement('small');
                    fileInfo.className = 'text-muted mt-1 d-block';
                    fileInfo.textContent = `Arquivo: ${file.name} (${this.formatFileSize(file.size)})`;
                    
                    // Remove existing file info
                    const existingInfo = this.parentNode.querySelector('small.text-muted');
                    if (existingInfo) existingInfo.remove();
                    
                    this.parentNode.appendChild(fileInfo);
                }
            });
        });
    },
    
    // Format file size for display
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    // Setup table enhancements
    setupTableEnhancements: function() {
        // Add hover effects and click handlers for table rows
        document.querySelectorAll('table tbody tr').forEach(row => {
            row.addEventListener('click', function(e) {
                // Don't trigger if clicking on buttons or links
                if (e.target.closest('button, a')) return;
                
                // Look for a view link in the row
                const viewLink = this.querySelector('a[href*="/acquisitions/"]');
                if (viewLink && !e.ctrlKey && !e.metaKey) {
                    window.location.href = viewLink.href;
                }
            });
            
            // Add title attribute for accessibility
            const viewLink = row.querySelector('a[href*="/acquisitions/"]');
            if (viewLink) {
                row.style.cursor = 'pointer';
                row.title = 'Clique para ver detalhes';
            }
        });
        
        // Sort functionality for table headers
        document.querySelectorAll('th[data-sort]').forEach(header => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', function() {
                this.sortTable(this);
            });
        });
    },
    
    // Setup search features
    setupSearchFeatures: function() {
        // Quick search in tables
        document.querySelectorAll('[data-search-table]').forEach(input => {
            const tableId = input.getAttribute('data-search-table');
            const table = document.getElementById(tableId);
            
            if (table) {
                input.addEventListener('input', function() {
                    this.searchTable(table, this.value);
                });
            }
        });
    },
    
    // Search within table
    searchTable: function(table, searchTerm) {
        const rows = table.querySelectorAll('tbody tr');
        const term = searchTerm.toLowerCase();
        
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            if (text.includes(term)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    },
    
    // Session timeout management
    initializeSessionTimeout: function() {
        let timeoutWarning;
        let timeoutRedirect;
        
        const resetTimeout = () => {
            clearTimeout(timeoutWarning);
            clearTimeout(timeoutRedirect);
            
            // Show warning 1 minute before timeout
            timeoutWarning = setTimeout(() => {
                if (confirm('Sua sessão expirará em 1 minuto. Deseja continuar?')) {
                    resetTimeout();
                }
            }, this.config.timeoutDuration - 60000);
            
            // Redirect to login after timeout
            timeoutRedirect = setTimeout(() => {
                alert('Sua sessão expirou. Você será redirecionado para a página de login.');
                window.location.href = '/auth/login';
            }, this.config.timeoutDuration);
        };
        
        // Reset timeout on user activity
        ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'].forEach(event => {
            document.addEventListener(event, resetTimeout, true);
        });
        
        resetTimeout();
    },
    
    // Utility functions
    utils: {
        // Format currency for display
        formatCurrency: function(value) {
            return new Intl.NumberFormat('pt-BR', {
                style: 'currency',
                currency: 'BRL'
            }).format(value);
        },
        
        // Format date for display
        formatDate: function(date) {
            return new Intl.DateTimeFormat('pt-BR').format(new Date(date));
        },
        
        // Show notification
        showNotification: function(message, type = 'info') {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
            alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
            alertDiv.innerHTML = `
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-triangle' : 'info-circle'} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            
            document.body.appendChild(alertDiv);
            
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, 5000);
        },
        
        // Confirm dialog with custom styling
        confirmAction: function(message, callback) {
            if (confirm(message)) {
                callback();
            }
        },
        
        // Copy text to clipboard
        copyToClipboard: function(text) {
            navigator.clipboard.writeText(text).then(() => {
                this.showNotification('Texto copiado para a área de transferência!', 'success');
            }).catch(() => {
                this.showNotification('Erro ao copiar texto', 'error');
            });
        }
    }
};

// Chart color schemes
const ChartColors = {
    senai: '#1e4a6b',
    success: '#198754',
    info: '#0dcaf0',
    warning: '#ffc107',
    danger: '#dc3545',
    secondary: '#6c757d',
    
    getColorPalette: function(count) {
        const colors = [this.senai, this.success, this.info, this.warning, this.danger, this.secondary];
        const palette = [];
        
        for (let i = 0; i < count; i++) {
            palette.push(colors[i % colors.length]);
        }
        
        return palette;
    }
};

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    SenaiApp.init();
});

// Export for use in other scripts
window.SenaiApp = SenaiApp;
window.ChartColors = ChartColors;

// Service Worker registration for offline support (optional)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        // Uncomment to enable service worker
        // navigator.serviceWorker.register('/sw.js').then(function(registration) {
        //     console.log('SW registered: ', registration);
        // }).catch(function(registrationError) {
        //     console.log('SW registration failed: ', registrationError);
        // });
    });
}
