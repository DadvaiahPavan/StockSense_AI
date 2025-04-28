/**
 * Main JavaScript file for StockSense AI
 * Handles common functionality across the application
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Stock search functionality
    initStockSearch();

    // Add animation to cards
    animateOnScroll();
});

/**
 * Initialize stock search functionality
 */
function initStockSearch() {
    const stockSearchLink = document.getElementById('stockSearchLink');
    const stockSearchInput = document.getElementById('stockSearchInput');
    const stockSearchResults = document.getElementById('stockSearchResults');

    if (stockSearchLink) {
        stockSearchLink.addEventListener('click', function(e) {
            e.preventDefault();
            const modal = new bootstrap.Modal(document.getElementById('stockSearchModal'));
            modal.show();
        });
    }

    if (stockSearchInput) {
        stockSearchInput.addEventListener('input', function() {
            const query = this.value.trim();
            const searchLoadingIndicator = document.getElementById('searchLoadingIndicator');
            
            if (query.length < 2) {
                stockSearchResults.innerHTML = '';
                searchLoadingIndicator.classList.add('d-none');
                return;
            }
            
            // Show loading indicator
            searchLoadingIndicator.classList.remove('d-none');
            stockSearchResults.innerHTML = '';
            
            // Fetch stock search results
            fetch(`/api/stock/search?query=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    // Hide loading indicator
                    searchLoadingIndicator.classList.add('d-none');
                    stockSearchResults.innerHTML = '';
                    
                    data.forEach(stock => {
                        const item = document.createElement('a');
                        item.href = `/stock/${stock.symbol}`;
                        item.className = 'list-group-item list-group-item-action';
                        item.innerHTML = `
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <strong>${stock.symbol}</strong>
                                    <div class="text-muted small">${stock.name}</div>
                                </div>
                                <button class="btn btn-sm btn-outline-primary add-to-watchlist" 
                                        data-symbol="${stock.symbol}" 
                                        data-name="${stock.name}">
                                    <i class="fas fa-plus"></i>
                                </button>
                            </div>
                        `;
                        
                        stockSearchResults.appendChild(item);
                    });
                    
                    // Add event listeners to the "Add to Watchlist" buttons
                    document.querySelectorAll('.add-to-watchlist').forEach(button => {
                        button.addEventListener('click', function(e) {
                            e.preventDefault();
                            e.stopPropagation();
                            
                            const symbol = this.dataset.symbol;
                            const name = this.dataset.name;
                            
                            // Add to watchlist via API
                            fetch('/api/watchlist/add', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({
                                    symbol: symbol,
                                    name: name
                                })
                            })
                            .then(response => response.json())
                            .then(data => {
                                if (data.success) {
                                    // Show success message
                                    showToast(`${symbol} added to watchlist`, 'success');
                                    
                                    // Update button
                                    this.innerHTML = '<i class="fas fa-check"></i>';
                                    this.classList.remove('btn-outline-primary');
                                    this.classList.add('btn-success');
                                    this.disabled = true;
                                }
                            })
                            .catch(error => {
                                console.error('Error:', error);
                                showToast('Error adding to watchlist', 'danger');
                            });
                        });
                    });
                })
                .catch(error => {
                    console.error('Error:', error);
                    // Hide loading indicator on error
                    searchLoadingIndicator.classList.add('d-none');
                    stockSearchResults.innerHTML = '<div class="p-3 text-center text-muted">Error fetching results</div>';
                });
        });
    }
}

/**
 * Add animation to elements when they scroll into view
 */
function animateOnScroll() {
    const animatedElements = document.querySelectorAll('.animate-on-scroll');
    
    if (animatedElements.length === 0) return;
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animated');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });
    
    animatedElements.forEach(element => {
        observer.observe(element);
    });
}

/**
 * Format a number as currency
 * @param {number} number - The number to format
 * @param {string} currency - The currency symbol (default: $)
 * @returns {string} Formatted currency string
 */
function formatCurrency(number, currency = '$') {
    return `${currency}${number.toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    })}`;
}

/**
 * Format a number as percentage
 * @param {number} number - The number to format
 * @returns {string} Formatted percentage string
 */
function formatPercentage(number) {
    return `${number.toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    })}%`;
}

/**
 * Format a large number with K, M, B suffixes
 * @param {number} number - The number to format
 * @returns {string} Formatted number string
 */
function formatLargeNumber(number) {
    if (number >= 1000000000) {
        return `${(number / 1000000000).toFixed(1)}B`;
    } else if (number >= 1000000) {
        return `${(number / 1000000).toFixed(1)}M`;
    } else if (number >= 1000) {
        return `${(number / 1000).toFixed(1)}K`;
    }
    return number.toString();
}

/**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {string} type - The type of toast (success, danger, warning, info)
 */
function showToast(message, type = 'info') {
    // Check if toast container exists, if not create it
    let toastContainer = document.querySelector('.toast-container');
    
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center text-white bg-${type} border-0`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toastEl);
    
    // Initialize and show the toast
    const toast = new bootstrap.Toast(toastEl, {
        autohide: true,
        delay: 3000
    });
    
    toast.show();
    
    // Remove toast element after it's hidden
    toastEl.addEventListener('hidden.bs.toast', function() {
        toastEl.remove();
    });
}

/**
 * Create a responsive chart that updates on window resize
 * @param {HTMLElement} canvas - The canvas element
 * @param {object} config - Chart.js configuration
 * @returns {Chart} Chart instance
 */
function createResponsiveChart(canvas, config) {
    const chart = new Chart(canvas, config);
    
    const resizeHandler = () => {
        chart.resize();
    };
    
    window.addEventListener('resize', resizeHandler);
    
    // Return the chart instance and a function to remove the event listener
    return {
        chart,
        destroy: () => {
            window.removeEventListener('resize', resizeHandler);
            chart.destroy();
        }
    };
}

/**
 * Format a date string
 * @param {string} dateString - The date string to format
 * @param {string} format - The format to use (short, medium, long)
 * @returns {string} Formatted date string
 */
function formatDate(dateString, format = 'medium') {
    const date = new Date(dateString);
    
    switch (format) {
        case 'short':
            return date.toLocaleDateString();
        case 'long':
            return date.toLocaleDateString(undefined, {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        case 'time':
            return date.toLocaleTimeString(undefined, {
                hour: '2-digit',
                minute: '2-digit'
            });
        case 'datetime':
            return date.toLocaleString();
        default: // medium
            return date.toLocaleDateString(undefined, {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
    }
}

/**
 * Debounce function to limit how often a function can be called
 * @param {Function} func - The function to debounce
 * @param {number} wait - The time to wait in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(func, wait = 300) {
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
