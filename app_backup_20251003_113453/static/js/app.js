// Shark Authentication Test - JavaScript Module

class SharkAPI {
    constructor() {
        this.baseURL = window.location.origin;
    }

    // Fetch user information
    async getUserInfo() {
        try {
            const response = await axios.get(`${this.baseURL}/api/whoami`);
            return response.data;
        } catch (error) {
            console.error('Error fetching user info:', error);
            throw error;
        }
    }

    // Fetch health status
    async getHealthStatus() {
        try {
            const response = await axios.get(`${this.baseURL}/health`);
            return response.data;
        } catch (error) {
            console.error('Error fetching health status:', error);
            throw error;
        }
    }

    // Fetch headers information
    async getHeaders() {
        try {
            const response = await axios.get(`${this.baseURL}/api/headers`);
            return response.data;
        } catch (error) {
            console.error('Error fetching headers:', error);
            throw error;
        }
    }

    // Fetch logs
    async getLogs() {
        try {
            const response = await axios.get(`${this.baseURL}/api/logs`);
            return response.data;
        } catch (error) {
            console.error('Error fetching logs:', error);
            throw error;
        }
    }
}

// Initialize API instance
const sharkAPI = new SharkAPI();

// Utility functions
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '<div class="loading"></div> Loading...';
    }
}

function formatTimestamp(timestamp) {
    return new Date(timestamp).toLocaleString();
}

function updateUserInfo() {
    showLoading('user-info-content');
    
    sharkAPI.getUserInfo()
        .then(data => {
            const content = `
                <div class="info-item">
                    <span class="info-label">Authenticated as:</span>
                    <span class="info-value">${data.email}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Your IP Address:</span>
                    <span class="info-value">${data.ip_address}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Access Time:</span>
                    <span class="info-value">${formatTimestamp(data.timestamp)}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Host:</span>
                    <span class="info-value">${data.host || 'localhost'}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Authenticated:</span>
                    <span class="info-value">${data.authenticated ? 'Yes' : 'No'}</span>
                </div>
            `;
            document.getElementById('user-info-content').innerHTML = content;
        })
        .catch(error => {
            document.getElementById('user-info-content').innerHTML = 
                '<div style="color: #dc3545;">Error loading user information</div>';
        });
}

function updateHealthStatus() {
    const statusElement = document.getElementById('health-status');
    if (!statusElement) return;

    showLoading('health-status');
    
    sharkAPI.getHealthStatus()
        .then(data => {
            statusElement.innerHTML = `
                <div class="info-card">
                    <h3>System Health</h3>
                    <div class="info-item">
                        <span class="info-label">Status:</span>
                        <span class="info-value" style="color: #28a745;">${data.status}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Service:</span>
                        <span class="info-value">${data.service}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Version:</span>
                        <span class="info-value">${data.version}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Last Check:</span>
                        <span class="info-value">${formatTimestamp(data.timestamp)}</span>
                    </div>
                </div>
            `;
        })
        .catch(error => {
            statusElement.innerHTML = 
                '<div style="color: #dc3545;">Error loading health status</div>';
        });
}

// Navigation functions
function navigateToHeaders() {
    window.location.href = '/headers';
}

function navigateToLogs() {
    window.location.href = '/logs';
}

function navigateToHealth() {
    window.location.href = '/health-page';
}

function navigateToWhoami() {
    window.location.href = '/api/whoami';
}

function refreshLogs() {
    const logsContainer = document.getElementById('logs-container');
    if (!logsContainer) return;

    showLoading('logs-container');
    
    sharkAPI.getLogs()
        .then(data => {
            logsContainer.innerHTML = data.logs || 'No logs available';
            // Update log count if element exists
            const logInfo = document.querySelector('.log-info p');
            if (logInfo && data.log_count !== undefined) {
                logInfo.innerHTML = `<strong>Log Entries:</strong> Showing last ${data.log_count} entries`;
            }
        })
        .catch(error => {
            logsContainer.innerHTML = 'Error loading logs';
            console.error('Error refreshing logs:', error);
        });
}

// Auto-refresh functionality
function startAutoRefresh(intervalSeconds = 30) {
    setInterval(() => {
        if (document.getElementById('user-info-content')) {
            updateUserInfo();
        }
        if (document.getElementById('health-status')) {
            updateHealthStatus();
        }
        if (document.getElementById('logs-container')) {
            refreshLogs();
        }
    }, intervalSeconds * 1000);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Update user info if element exists
    if (document.getElementById('user-info-content')) {
        updateUserInfo();
    }
    
    // Update health status if element exists
    if (document.getElementById('health-status')) {
        updateHealthStatus();
    }
    
    // Add click handlers for navigation buttons
    const navButtons = document.querySelectorAll('.nav-item[data-action]');
    navButtons.forEach(button => {
        button.addEventListener('click', function() {
            const action = this.getAttribute('data-action');
            switch(action) {
                case 'whoami':
                    navigateToWhoami();
                    break;
                case 'headers':
                    navigateToHeaders();
                    break;
                case 'logs':
                    navigateToLogs();
                    break;
                case 'health':
                    navigateToHealth();
                    break;
            }
        });
    });
    
    // Start auto-refresh for dynamic pages
    if (window.location.pathname === '/' || 
        window.location.pathname === '/logs' || 
        window.location.pathname === '/health-page') {
        startAutoRefresh(30);
    }
});

// Export for use in other scripts
window.SharkAPI = SharkAPI;
window.sharkAPI = sharkAPI;
