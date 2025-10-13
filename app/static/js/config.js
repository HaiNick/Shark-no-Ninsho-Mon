/**
 * Configuration constants for Shark-no-Ninsho-Mon
 */

window.Config = {
    // API Configuration
    API: {
        BASE_URL: '',
        ENDPOINTS: {
            ROUTES: '/api/routes',
            EMAILS: '/api/emails',
            LOGS: '/api/logs'
        },
        TIMEOUT: 10000,
        RETRY_ATTEMPTS: 3
    },
    
    // UI Configuration
    UI: {
        TOAST_DURATION: 3000,
        DEBOUNCE_DELAY: 300,
        CACHE_DURATION: 5 * 60 * 1000, // 5 minutes
        PARTICLE_COUNT: 50,
        MAX_LOG_ENTRIES: 200
    },
    
    // Validation Rules
    VALIDATION: {
        EMAIL_REGEX: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
        IP_REGEX: /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/,
        PORT_MIN: 1,
        PORT_MAX: 65535,
        ROUTE_PATH_REGEX: /^\/[a-z0-9\-_\/]*$/
    },
    
    // Status Types
    STATUS: {
        ONLINE: 'online',
        OFFLINE: 'offline',
        SLOW: 'slow',
        UNKNOWN: 'unknown'
    },
    
    // Toast Types
    TOAST_TYPES: {
        SUCCESS: 'success',
        ERROR: 'error',
        INFO: 'info',
        WARNING: 'warning'
    },
    
    // Local Storage Keys
    STORAGE_KEYS: {
        THEME: 'shark_theme',
        USER_PREFERENCES: 'shark_preferences',
        LAST_REFRESH: 'shark_last_refresh'
    }
};