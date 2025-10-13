/**
 * Shared JavaScript Utilities for Shark-no-Ninsho-Mon
 * Common functions used across multiple pages
 */

// ============================================================================
// Toast/Notification System
// ============================================================================

/**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {string} type - The type of toast (success, error, info, warning)
 * @param {number} duration - Duration in milliseconds (default: 3000)
 */
function showToast(message, type = 'info', duration = 3000) {
    // Remove any existing toasts
    const existingToast = document.getElementById('toast');
    if (existingToast && existingToast.classList.contains('show')) {
        existingToast.classList.remove('show');
    }
    
    // Get or create toast element
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        toast.className = 'toast';
        document.body.appendChild(toast);
    }
    
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    
    // Auto-hide after duration
    setTimeout(() => {
        toast.classList.remove('show');
    }, duration);
}

/**
 * Show a notification (alternative implementation)
 * @param {string} message - The message to display
 * @param {string} type - The type of notification (success, error, info)
 */
function showNotification(message, type = 'info') {
    showToast(message, type, 3000);
}

// ============================================================================
// API Utilities
// ============================================================================

/**
 * Make an API request with error handling
 * @param {string} url - The API endpoint
 * @param {object} options - Fetch options
 * @returns {Promise} - The response data
 */
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

// ============================================================================
// Form Utilities
// ============================================================================

/**
 * Debounce function for search inputs
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} - Debounced function
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
 * Validate email address
 * @param {string} email - Email to validate
 * @returns {boolean} - True if valid
 */
function validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * Validate IP address
 * @param {string} ip - IP address to validate
 * @returns {boolean} - True if valid
 */
function validateIP(ip) {
    const ipRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
    return ipRegex.test(ip);
}

// ============================================================================
// UI Utilities
// ============================================================================

/**
 * Show loading state on an element
 * @param {HTMLElement} element - Element to show loading on
 * @param {string} originalText - Original text to restore later
 */
function showLoading(element, originalText = '') {
    element.disabled = true;
    element.dataset.originalText = originalText || element.textContent;
    element.innerHTML = '<span class="spinner"><svg width="16" height="16" viewBox="0 0 24 24"><path d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z" opacity=".25"/><path d="M12,4a8,8,0,0,1,7.89,6.7A1.53,1.53,0,0,0,21.38,12h0a1.5,1.5,0,0,0,1.48-1.75,11,11,0,0,0-21.72,0A1.5,1.5,0,0,0,2.62,12h0a1.53,1.53,0,0,0,1.49-1.3A8,8,0,0,1,12,4Z" fill="currentColor"/></svg></span> Loading...';
}

/**
 * Hide loading state on an element
 * @param {HTMLElement} element - Element to hide loading on
 */
function hideLoading(element) {
    element.disabled = false;
    element.textContent = element.dataset.originalText || '';
    delete element.dataset.originalText;
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 * @returns {Promise<boolean>} - True if successful
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Copied to clipboard!', 'success', 1500);
        return true;
    } catch (error) {
        console.error('Failed to copy to clipboard:', error);
        showToast('Failed to copy to clipboard', 'error');
        return false;
    }
}

// ============================================================================
// Animation Utilities
// ============================================================================

/**
 * Smooth scroll to element
 * @param {string|HTMLElement} target - CSS selector or element
 * @param {number} offset - Offset from top (default: 0)
 */
function smoothScrollTo(target, offset = 0) {
    const element = typeof target === 'string' ? document.querySelector(target) : target;
    if (!element) return;
    
    const targetPosition = element.offsetTop - offset;
    window.scrollTo({
        top: targetPosition,
        behavior: 'smooth'
    });
}

// ============================================================================
// Cache System (Simple)
// ============================================================================

const cache = new Map();

/**
 * Get item from cache
 * @param {string} key - Cache key
 * @param {number} maxAge - Max age in milliseconds (default: 5 minutes)
 * @returns {any|null} - Cached value or null
 */
function getCache(key, maxAge = 5 * 60 * 1000) {
    const item = cache.get(key);
    if (!item) return null;
    
    if (Date.now() - item.timestamp > maxAge) {
        cache.delete(key);
        return null;
    }
    
    return item.data;
}

/**
 * Set item in cache
 * @param {string} key - Cache key
 * @param {any} data - Data to cache
 */
function setCache(key, data) {
    cache.set(key, {
        data,
        timestamp: Date.now()
    });
}

/**
 * Clear cache
 * @param {string} key - Optional key to clear, or clear all if not provided
 */
function clearCache(key = null) {
    if (key) {
        cache.delete(key);
    } else {
        cache.clear();
    }
}

// ============================================================================
// Error Handling
// ============================================================================

/**
 * Global error handler for API calls
 * @param {Error} error - The error object
 * @param {string} context - Context where error occurred
 */
function handleError(error, context = 'Operation') {
    console.error(`${context} failed:`, error);
    
    let message = `${context} failed`;
    
    if (error.message.includes('Failed to fetch')) {
        message = 'Network error. Please check your connection.';
    } else if (error.message.includes('401')) {
        message = 'Authentication required. Please refresh the page.';
    } else if (error.message.includes('403')) {
        message = 'Access denied. You do not have permission.';
    } else if (error.message.includes('404')) {
        message = 'Resource not found.';
    } else if (error.message.includes('500')) {
        message = 'Server error. Please try again later.';
    }
    
    showToast(message, 'error');
}

// ============================================================================
// Export to window for global access
// ============================================================================

// Make utilities available globally
window.Utils = {
    showToast,
    showNotification,
    apiRequest,
    debounce,
    validateEmail,
    validateIP,
    showLoading,
    hideLoading,
    copyToClipboard,
    smoothScrollTo,
    getCache,
    setCache,
    clearCache,
    handleError
};

// Backwards compatibility
window.showToast = showToast;
window.showNotification = showNotification;