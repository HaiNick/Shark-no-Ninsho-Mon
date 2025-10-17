/**
 * Setup Wizard JavaScript
 * Handles system checks, configuration, and Docker controls
 */

// ============================================================================
// API Helpers
// ============================================================================

/**
 * Make an API request with error handling
 * @param {string} endpoint - The API endpoint
 * @param {string} method - HTTP method (GET, POST, etc.)
 * @param {Object|null} data - Request data
 * @returns {Promise<Object>} - Response data
 */
async function apiRequest(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    const response = await fetch(endpoint, options);
    return await response.json();
}

// ============================================================================
// System Checks
// ============================================================================

/**
 * Run system requirement checks
 */
async function runSystemChecks() {
    const container = document.getElementById('system-checks-container');
    const warningsContainer = document.getElementById('warnings-container');
    
    try {
        const checks = await apiRequest('/api/system-check');
        
        container.innerHTML = '';
        let warnings = [];
        
        // Python check
        const pythonCard = createCheckCard(
            'Python',
            checks.python.compatible ? 'success' : 'error',
            `Version: ${checks.python.version}`,
            checks.python.compatible ? 'Compatible' : 'Incompatible (Need 3.8+)'
        );
        container.appendChild(pythonCard);
        
        // Admin check
        const adminCard = createCheckCard(
            'Privileges',
            checks.is_admin ? 'success' : 'warning',
            `Running as: ${checks.is_admin ? 'Admin/Sudo' : 'Normal User'}`,
            checks.is_admin ? 'Elevated' : 'Limited'
        );
        container.appendChild(adminCard);
        if (!checks.is_admin) {
            warnings.push('Not running with admin/sudo privileges - Docker and Tailscale commands may fail');
        }
        
        // Docker check
        const dockerCard = createCheckCard(
            'Docker',
            checks.docker.installed && checks.docker.running ? 'success' : 'error',
            checks.docker.installed ? `${checks.docker.version}` : 'Not installed',
            checks.docker.running ? 'Running' : checks.docker.installed ? 'Not Running' : 'Not Found'
        );
        container.appendChild(dockerCard);
        if (!checks.docker.installed) {
            warnings.push('Docker is not installed - Install from https://docker.com');
        } else if (!checks.docker.running) {
            warnings.push('Docker is not running - Please start Docker Desktop');
        }
        
        // Docker Compose check
        const composeCard = createCheckCard(
            'Docker Compose',
            checks.docker_compose.installed ? 'success' : 'warning',
            checks.docker_compose.installed ? `${checks.docker_compose.version}` : 'Not installed',
            checks.docker_compose.installed ? 'Installed' : 'Not Found'
        );
        container.appendChild(composeCard);
        
        // Tailscale check
        const tailscaleCard = createCheckCard(
            'Tailscale',
            checks.tailscale.installed && checks.tailscale.running ? 'success' : 'warning',
            checks.tailscale.installed ? `${checks.tailscale.version}` : 'Not installed',
            checks.tailscale.running ? 'Running' : checks.tailscale.installed ? 'Not Running' : 'Not Found'
        );
        container.appendChild(tailscaleCard);
        if (!checks.tailscale.installed) {
            warnings.push('Tailscale is not installed - Install from https://tailscale.com');
        } else if (!checks.tailscale.running) {
            warnings.push('Tailscale is not running - Please start Tailscale');
        }
        
        // Display warnings
        displayWarnings(warningsContainer, warnings);
        
    } catch (error) {
        container.innerHTML = `<div class="alert alert-danger">Error checking system: ${error.message}</div>`;
    }
}

/**
 * Create a system check card
 * @param {string} title - Card title
 * @param {string} status - Status type (success, warning, error)
 * @param {string} info - Information text
 * @param {string} statusText - Status badge text
 * @returns {HTMLElement} - The created card element
 */
function createCheckCard(title, status, info, statusText) {
    const card = document.createElement('div');
    card.className = `check-card ${status === 'success' ? '' : status}`;
    card.innerHTML = `
        <h3>${title}</h3>
        <p>${info}</p>
        <span class="status-badge ${status}">${statusText}</span>
    `;
    return card;
}

/**
 * Display system warnings
 * @param {HTMLElement} container - Container element
 * @param {Array<string>} warnings - Array of warning messages
 */
function displayWarnings(container, warnings) {
    if (warnings.length > 0) {
        container.innerHTML = `
            <div class="alert alert-warning">
                <strong>Warnings:</strong>
                <ul style="margin: 10px 0 0 20px;">
                    ${warnings.map(w => `<li>${w}</li>`).join('')}
                </ul>
            </div>
        `;
    } else {
        container.innerHTML = `
            <div class="alert alert-success">
                <strong>All system checks passed!</strong> Your system is ready for setup.
            </div>
        `;
    }
}

// ============================================================================
// Configuration Management
// ============================================================================

/**
 * Generate secrets for OAuth and Flask
 */
async function generateSecrets() {
    try {
        const secrets = await apiRequest('/api/generate-secrets', 'POST');
        document.getElementById('oauth-cookie-secret').value = secrets.oauth_cookie_secret;
        document.getElementById('flask-secret-key').value = secrets.flask_secret_key;
        
        showAlert('save-result', 'Secrets generated successfully!', 'success');
    } catch (error) {
        showAlert('save-result', `Error generating secrets: ${error.message}`, 'danger');
    }
}

/**
 * Load existing configuration
 */
async function loadExistingConfig() {
    try {
        const config = await apiRequest('/api/load-config');
        
        // Populate form fields with existing config
        const fieldMappings = {
            'oauth-client-id': config.OAUTH2_PROXY_CLIENT_ID,
            'oauth-client-secret': config.OAUTH2_PROXY_CLIENT_SECRET,
            'oauth-cookie-secret': config.OAUTH2_PROXY_COOKIE_SECRET,
            'tailscale-hostname': config.FUNNEL_HOSTNAME,
            'flask-secret-key': config.SECRET_KEY
        };
        
        Object.entries(fieldMappings).forEach(([fieldId, value]) => {
            if (value) {
                document.getElementById(fieldId).value = value;
            }
        });
        
        if (config.DEV_MODE === 'true') {
            document.getElementById('dev-mode').checked = true;
        }
        
        showAlert('save-result', 'Existing configuration loaded!', 'info');
    } catch (error) {
        showAlert('save-result', `Error loading config: ${error.message}`, 'danger');
    }
}

/**
 * Save configuration
 * @param {Event} e - Form submit event
 */
async function saveConfiguration(e) {
    e.preventDefault();
    
    const devMode = document.getElementById('dev-mode').checked;
    
    const config = {
        oauth_client_id: document.getElementById('oauth-client-id').value,
        oauth_client_secret: document.getElementById('oauth-client-secret').value,
        oauth_cookie_secret: document.getElementById('oauth-cookie-secret').value,
        cookie_expire: document.getElementById('cookie-expire').value,
        cookie_refresh: document.getElementById('cookie-refresh').value,
        tailscale_hostname: document.getElementById('tailscale-hostname').value,
        authorized_email: document.getElementById('authorized-email').value,
        flask_secret_key: document.getElementById('flask-secret-key').value,
        permanent_session_lifetime: document.getElementById('flask-session-lifetime').value,
        session_cookie_secure: 'true',
        session_cookie_httponly: 'true',
        session_cookie_samesite: 'Lax',
        dev_mode: devMode ? 'true' : 'false',
        flask_env: devMode ? 'development' : 'production',
        debug: devMode ? 'true' : 'false'
    };
    
    try {
        const result = await apiRequest('/api/save-config', 'POST', config);
        showAlert('save-result', result.message, 'success');
    } catch (error) {
        showAlert('save-result', `Error saving configuration: ${error.message}`, 'danger');
    }
}

// ============================================================================
// Validation
// ============================================================================

/**
 * Validate OAuth Client ID
 * @param {Event} e - Input blur event
 */
async function validateOAuthClientId(e) {
    const value = e.target.value;
    if (!value) return;
    
    try {
        const result = await apiRequest('/api/validate-oauth', 'POST', { client_id: value });
        const errorDiv = document.getElementById('oauth-client-id-error');
        
        if (result.valid) {
            e.target.classList.remove('invalid');
            e.target.classList.add('valid');
            errorDiv.textContent = '';
        } else {
            e.target.classList.remove('valid');
            e.target.classList.add('invalid');
            errorDiv.textContent = result.message;
        }
    } catch (error) {
        console.error('Validation error:', error);
    }
}

/**
 * Validate Tailscale hostname
 * @param {Event} e - Input blur event
 */
async function validateTailscaleHostname(e) {
    const value = e.target.value;
    if (!value) return;
    
    try {
        const result = await apiRequest('/api/validate-tailscale', 'POST', { hostname: value });
        const errorDiv = document.getElementById('tailscale-hostname-error');
        
        if (result.valid) {
            e.target.classList.remove('invalid');
            e.target.classList.add('valid');
            errorDiv.textContent = '';
        } else {
            e.target.classList.remove('valid');
            e.target.classList.add('invalid');
            errorDiv.textContent = result.message;
        }
    } catch (error) {
        console.error('Validation error:', error);
    }
}

// ============================================================================
// Docker Controls
// ============================================================================

/**
 * Start Docker containers
 */
async function startDockerContainers() {
    const btn = document.getElementById('docker-start-btn');
    btn.disabled = true;
    btn.textContent = 'Starting...';
    
    try {
        const result = await apiRequest('/api/docker/start', 'POST');
        showAlert('docker-result', result.message, 'success');
    } catch (error) {
        const errorData = await error;
        showAlert('docker-result', errorData.message || 'Error starting Docker', 'danger');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Start Docker Containers';
    }
}

/**
 * Stop Docker containers
 */
async function stopDockerContainers() {
    const btn = document.getElementById('docker-stop-btn');
    btn.disabled = true;
    btn.textContent = 'Stopping...';
    
    try {
        const result = await apiRequest('/api/docker/stop', 'POST');
        showAlert('docker-result', result.message, 'success');
    } catch (error) {
        const errorData = await error;
        showAlert('docker-result', errorData.message || 'Error stopping Docker', 'danger');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Stop Docker Containers';
    }
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Show alert message
 * @param {string} containerId - Container element ID
 * @param {string} message - Alert message
 * @param {string} type - Alert type (success, warning, danger, info)
 */
function showAlert(containerId, message, type) {
    const container = document.getElementById(containerId);
    container.className = `alert alert-${type}`;
    container.textContent = message;
    container.classList.remove('hidden');
    
    setTimeout(() => {
        container.classList.add('hidden');
    }, 5000);
}

// ============================================================================
// Event Listeners Setup
// ============================================================================

/**
 * Setup all event listeners
 */
function setupEventListeners() {
    // Generate secrets button
    document.getElementById('generate-secrets-btn').addEventListener('click', generateSecrets);
    
    // Load config button
    document.getElementById('load-config-btn').addEventListener('click', loadExistingConfig);
    
    // Form submission
    document.getElementById('config-form').addEventListener('submit', saveConfiguration);
    
    // Validation events
    document.getElementById('oauth-client-id').addEventListener('blur', validateOAuthClientId);
    document.getElementById('tailscale-hostname').addEventListener('blur', validateTailscaleHostname);
    
    // Docker controls
    document.getElementById('docker-start-btn').addEventListener('click', startDockerContainers);
    document.getElementById('docker-stop-btn').addEventListener('click', stopDockerContainers);
}

// ============================================================================
// Initialization
// ============================================================================

/**
 * Initialize the setup wizard
 */
function initialize() {
    // Run system checks
    runSystemChecks();
    
    // Auto-generate secrets on load
    apiRequest('/api/generate-secrets', 'POST')
        .then(secrets => {
            document.getElementById('oauth-cookie-secret').value = secrets.oauth_cookie_secret;
            document.getElementById('flask-secret-key').value = secrets.flask_secret_key;
        })
        .catch(error => {
            console.error('Failed to auto-generate secrets:', error);
        });
    
    // Setup event listeners
    setupEventListeners();
}

// Initialize when DOM is loaded
window.addEventListener('DOMContentLoaded', initialize);