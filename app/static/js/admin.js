/**
 * Admin Page JavaScript - Route Management
 */

// State
let routes = [];
let currentEditRoute = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadRoutes();
    setupEventListeners();
});

// Event Listeners
function setupEventListeners() {
    // Modal close on background click
    const modal = document.getElementById('route-modal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeModal();
            }
        });
    }
    
    // ESC key to close modal
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal.classList.contains('show')) {
            closeModal();
        }
    });
}

// Load Routes with caching
async function loadRoutes() {
    try {
        // Check cache first
        const cacheKey = 'routes';
        const cachedData = Utils.getCache(cacheKey, Config.UI.CACHE_DURATION);
        
        if (cachedData) {
            routes = cachedData;
            renderRoutes(routes);
            updateStats(routes);
            return;
        }
        
        // Show loading state for fresh data
        const tbody = document.getElementById('routes-tbody');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; padding: 2rem;">
                        <div class="spinner"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg></div>
                        <div style="margin-top: 0.5rem;">Loading routes...</div>
                    </td>
                </tr>
            `;
        }
        
        // Fetch from API
        const data = await Utils.apiRequest(Config.API.ENDPOINTS.ROUTES);
        routes = data;
        
        // Cache the result
        Utils.setCache(cacheKey, routes);
        
        renderRoutes(routes);
        updateStats(routes);
    } catch (error) {
        Utils.handleError(error, 'Loading routes');
        
        // Show error state in UI
        const tbody = document.getElementById('routes-tbody');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; padding: 2rem;">
                        <div style="color: var(--text-secondary);">
                            <div style="font-size: 3rem; margin-bottom: 1rem;">⚠️</div>
                            <p>Failed to load routes. Please refresh the page.</p>
                        </div>
                    </td>
                </tr>
            `;
        }
    }
}

// Render Routes Table
function renderRoutes(routesList) {
    const tbody = document.getElementById('routes-tbody');
    
    if (routesList.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: 2rem;">
                    <div style="color: var(--text-secondary);">
                        <div style="font-size: 3rem; margin-bottom: 1rem;">—</div>
                        <p>No routes configured yet. Click "Add Route" to get started.</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = routesList.map(route => {
        // Determine status badge class and text
        let badgeClass = route.status || 'unknown';
        let badgeText = (route.status || 'unknown').charAt(0).toUpperCase() + (route.status || 'unknown').slice(1);
        
        // Use new state/reason if available
        if (route.state) {
            badgeClass = route.state.toLowerCase();
            if (route.state === 'UP') {
                badgeText = route.http_status ? `OK — ${route.http_status}` : 'OK';
            } else if (route.state === 'DEGRADED') {
                badgeText = route.duration_ms ? `SLOW — ${(route.duration_ms / 1000).toFixed(1)}s` : 'SLOW';
            } else if (route.state === 'DOWN') {
                if (route.reason === 'offline_dns') badgeText = 'DOWN — DNS';
                else if (route.reason === 'offline_conn') badgeText = 'DOWN — Connect';
                else if (route.reason === 'timeout') badgeText = 'DOWN — Timeout';
                else if (route.reason === 'error_5xx') badgeText = route.http_status ? `DOWN — ${route.http_status}` : 'DOWN — 5xx';
                else if (route.reason === 'error_exc') badgeText = 'DOWN — Error';
                else if (route.reason === 'misconfig') badgeText = 'DOWN — Config';
                else badgeText = 'DOWN';
            } else {
                badgeText = 'UNKNOWN';
            }
        }
        
        return `
        <tr>
            <td>
                <span class="status-badge ${badgeClass}" title="${route.last_error || ''}">
                    <span class="status-dot"></span>
                    ${badgeText}
                </span>
            </td>
            <td><span class="route-path">${route.path}</span></td>
            <td>${route.name}</td>
            <td><span class="route-target">${route.protocol}://${route.target_ip}:${route.target_port}${route.target_path || '/'}</span></td>
            <td>${route.protocol.toUpperCase()}</td>
            <td>
                <label class="toggle-switch">
                    <input type="checkbox" ${route.enabled ? 'checked' : ''} 
                           onchange="toggleRoute('${route.id}')">
                    <span class="toggle-slider"></span>
                </label>
            </td>
            <td>
                <div class="action-buttons">
                    <button class="btn-icon test" onclick="testRoute('${route.id}')" title="Test Connection" data-route-id="${route.id}">
                        <img src="/static/icons/check_circle.svg" alt="" class="icon test-icon" aria-hidden="true">
                    </button>
                    <button class="btn-icon edit" onclick="editRoute('${route.id}')" title="Edit">
                        <img src="/static/icons/edit.svg" alt="Edit" style="width: 18px; height: 18px;" aria-hidden="true">
                    </button>
                    <button class="btn-icon delete" onclick="deleteRoute('${route.id}')" title="Delete">
                        <img src="/static/icons/delete.svg" alt="Delete" style="width: 18px; height: 18px;" aria-hidden="true">
                    </button>
                </div>
            </td>
        </tr>
    `;
    }).join('');
}

// Update Stats
function updateStats(routesList) {
    const total = routesList.length;
    // Handle both old status and new state systems
    const online = routesList.filter(r => 
        (r.state === 'UP') || (r.status === 'online')
    ).length;
    const offline = routesList.filter(r => 
        (r.state === 'DOWN') || (r.status === 'offline')
    ).length;
    const enabled = routesList.filter(r => r.enabled).length;
    
    const statElements = {
        total: document.getElementById('stat-total'),
        online: document.getElementById('stat-online'),
        offline: document.getElementById('stat-offline'),
        enabled: document.getElementById('stat-enabled')
    };
    
    // Update stats with null checks
    if (statElements.total) statElements.total.textContent = total;
    if (statElements.online) statElements.online.textContent = online;
    if (statElements.offline) statElements.offline.textContent = offline;
    if (statElements.enabled) statElements.enabled.textContent = enabled;
}

// Search/Filter Routes with debouncing
const debouncedFilterRoutes = Utils.debounce(function() {
    const searchTerm = document.getElementById('search-input').value.toLowerCase();
    
    if (!searchTerm) {
        renderRoutes(routes);
        return;
    }
    
    const filtered = routes.filter(route => 
        route.path.toLowerCase().includes(searchTerm) ||
        route.name.toLowerCase().includes(searchTerm) ||
        route.target_ip.includes(searchTerm)
    );
    
    renderRoutes(filtered);
}, Config.UI.DEBOUNCE_DELAY);

// Wrapper function for template compatibility
function filterRoutes() {
    debouncedFilterRoutes();
}

// Refresh Routes with loading state
async function refreshRoutes() {
    const btn = event.target.closest('button');
    const icon = btn.querySelector('.icon');
    
    // Clear cache to force fresh data
    Utils.clearCache('routes');
    
    if (icon) {
        icon.classList.add('animate-spin');
    }
    
    await loadRoutes();
    
    if (icon) {
        icon.classList.remove('animate-spin');
    }
    
    showToast('Routes refreshed', 'success');
}

// Modal Management
function showAddModal() {
    currentEditRoute = null;
    document.getElementById('modal-title').textContent = 'Add New Route';
    document.getElementById('route-form').reset();
    document.getElementById('route-id').value = '';
    document.getElementById('route-modal').classList.add('show');
}

function editRoute(routeId) {
    const route = routes.find(r => r.id === routeId);
    if (!route) return;
    
    currentEditRoute = route;
    document.getElementById('modal-title').textContent = 'Edit Route';
    
    // Populate form
    document.getElementById('route-id').value = route.id;
    document.getElementById('path').value = route.path;
    document.getElementById('name').value = route.name;
    document.getElementById('target_ip').value = route.target_ip;
    document.getElementById('target_port').value = route.target_port;
    document.getElementById('target_path').value = route.target_path || '/';
    document.getElementById('protocol').value = route.protocol;
    document.getElementById('timeout').value = route.timeout || 30;
    document.getElementById('enabled').checked = route.enabled;
    document.getElementById('health_check').checked = route.health_check;
    
    document.getElementById('route-modal').classList.add('show');
}

function closeModal() {
    document.getElementById('route-modal').classList.remove('show');
    currentEditRoute = null;
}

// Form Submission
async function handleSubmit(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const routeId = formData.get('id');
    
    const data = {
        path: formData.get('path'),
        name: formData.get('name'),
        target_ip: formData.get('target_ip'),
        target_port: parseInt(formData.get('target_port')),
        target_path: formData.get('target_path') || '/',
        protocol: formData.get('protocol'),
        timeout: parseInt(formData.get('timeout')),
        enabled: formData.get('enabled') === 'on',
        health_check: formData.get('health_check') === 'on'
    };
    
    try {
        let response;
        
        if (routeId) {
            // Update existing route
            response = await fetch(`/api/routes/${routeId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        } else {
            // Create new route
            response = await fetch('/api/routes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        }
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Failed to save route');
        }
        
        showToast(routeId ? 'Route updated successfully' : 'Route created successfully', 'success');
        closeModal();
        Utils.clearCache('routes'); // Clear cache to force refresh
        await loadRoutes();
        
    } catch (error) {
        console.error('Error saving route:', error);
        showToast('Failed to save route: ' + error.message, 'error');
    }
}

// Toggle Route
async function toggleRoute(routeId) {
    try {
        const response = await fetch(`/api/routes/${routeId}/toggle`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Failed to toggle route');
        }
        
        showToast(`Route ${result.enabled ? 'enabled' : 'disabled'}`, 'success');
        Utils.clearCache('routes'); // Clear cache to force refresh
        await loadRoutes();
        
    } catch (error) {
        console.error('Error toggling route:', error);
        showToast('Failed to toggle route: ' + error.message, 'error');
        await loadRoutes(); // Reload to reset toggle state
    }
}

// Test Route
async function testRoute(routeId) {
    const btn = event.target.closest('button');
    const icon = btn.querySelector('.test-icon');
    const originalSrc = icon ? icon.src : null;
    
    if (icon) {
        icon.src = '/static/icons/progress_activity.svg';
        icon.style.animation = 'spin 1s linear infinite';
    }
    
    try {
        const response = await fetch(`/api/routes/${routeId}/test`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast(`Route is ${result.status} (${result.response_time}ms)`, 'success');
        } else {
            showToast(`Route test failed: ${result.error}`, 'error');
        }
        
        await loadRoutes(); // Reload to update status
        
    } catch (error) {
        console.error('Error testing route:', error);
        showToast('Failed to test route: ' + error.message, 'error');
    } finally {
        if (icon && originalSrc) {
            icon.src = originalSrc;
            icon.style.animation = '';
        }
    }
}

// Delete Route
async function deleteRoute(routeId) {
    const route = routes.find(r => r.id === routeId);
    if (!route) return;
    
    if (!confirm(`Are you sure you want to delete the route "${route.name}" (${route.path})?`)) {
        return;
    }
    
    // Find the delete button and add loading state
    const deleteBtn = event.target.closest('button');
    const originalContent = deleteBtn.innerHTML;
    deleteBtn.disabled = true;
    deleteBtn.innerHTML = '<div class="spinner"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg></div>';
    
    try {
        const response = await fetch(`/api/routes/${routeId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Failed to delete route');
        }
        
        showToast('Route deleted successfully', 'success');
        Utils.clearCache('routes'); // Clear cache to force refresh
        await loadRoutes();
        
    } catch (error) {
        console.error('Error deleting route:', error);
        showToast('Failed to delete route: ' + error.message, 'error');
        
        // Restore button on error
        deleteBtn.disabled = false;
        deleteBtn.innerHTML = originalContent;
    }
}

// Toast functionality now provided by utils.js
