/**
 * Email Management JavaScript
 */

// State
let emails = [];
let currentUserEmail = '';

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Get current user email from the page context
    const emailElement = document.querySelector('[id="stat-current"]');
    if (emailElement) {
        currentUserEmail = emailElement.textContent.trim();
    }
    
    loadEmails();
    setupEventListeners();
});

// Event Listeners
function setupEventListeners() {
    // Modal close on background click
    const modal = document.getElementById('email-modal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeEmailModal();
            }
        });
    }
    
    // ESC key to close modal
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal && modal.classList.contains('show')) {
            closeEmailModal();
        }
    });
}

// Load Emails with caching
async function loadEmails() {
    try {
        // Check cache first
        const cacheKey = 'emails';
        const cachedData = Utils.getCache(cacheKey, Config.UI.CACHE_DURATION);
        
        if (cachedData) {
            emails = cachedData;
            renderEmails(emails);
            updateStats(emails);
            return;
        }
        
        // Fetch from API
        const data = await Utils.apiRequest(Config.API.ENDPOINTS.EMAILS);
        emails = data.emails || [];
        renderEmails(emails);
        updateStats(emails);
    } catch (error) {
        console.error('Error loading emails:', error);
        showToast('Failed to load emails: ' + error.message, 'error');
    }
}

// Render Emails
function renderEmails(emailList) {
    const tbody = document.getElementById('emails-tbody');
    
    if (!emailList || emailList.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="loading">
                    <div>No authorized emails found</div>
                    <small>Add an email address to grant access to the application</small>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = emailList.map((email, index) => {
        const isCurrent = email.toLowerCase() === currentUserEmail.toLowerCase();
        const statusClass = isCurrent ? 'current' : 'active';
        const statusText = isCurrent ? 'Current User' : 'Active';
        
        return `
            <tr>
                <td>
                    <span class="email-address">
                        ${email}
                        ${isCurrent ? '<span class="current-user-label">(You)</span>' : ''}
                    </span>
                </td>
                <td>
                    <span class="email-status ${statusClass}">
                        <span class="status-dot"></span>
                        ${statusText}
                    </span>
                </td>
                <td>
                    <span class="email-date">Manual entry</span>
                </td>
                <td>
                    <div class="action-buttons">
                        ${!isCurrent ? `
                            <button class="btn-icon delete" onclick="confirmRemoveEmail('${email}')" title="Remove email">
                                <img src="/static/icons/delete.svg" alt="Delete" style="width: 18px; height: 18px;" aria-hidden="true">
                            </button>
                        ` : `
                            <span class="text-muted">-</span>
                        `}
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// Update Stats
function updateStats(emailList) {
    const totalElement = document.getElementById('stat-total');
    const activeElement = document.getElementById('stat-active');
    
    if (totalElement) {
        totalElement.textContent = emailList.length;
    }
    
    if (activeElement) {
        activeElement.textContent = emailList.length;
    }
}

// Filter Emails with debouncing
const debouncedFilterEmails = Utils.debounce(function() {
    const searchTerm = document.getElementById('search-input').value.toLowerCase();
    const filteredEmails = emails.filter(email => 
        email.toLowerCase().includes(searchTerm)
    );
    renderEmails(filteredEmails);
}, Config.UI.DEBOUNCE_DELAY);

// Wrapper function for template compatibility
function filterEmails() {
    debouncedFilterEmails();
}

// Show Add Email Modal
function showAddEmailModal() {
    const modal = document.getElementById('email-modal');
    const form = document.getElementById('email-form');
    
    form.reset();
    modal.classList.add('show');
    
    // Focus on email input
    setTimeout(() => {
        document.getElementById('new-email').focus();
    }, 100);
}

// Close Email Modal
function closeEmailModal() {
    const modal = document.getElementById('email-modal');
    modal.classList.remove('show');
}

// Handle Email Form Submit
async function handleEmailSubmit(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const email = formData.get('email').trim().toLowerCase();
    
    if (!email) {
        showToast('Email is required', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/emails', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast(`Email "${email}" added successfully`, 'success');
            closeEmailModal();
            loadEmails(); // Reload the email list
        } else {
            showToast(data.error || 'Failed to add email', 'error');
        }
    } catch (error) {
        console.error('Error adding email:', error);
        showToast('Network error: ' + error.message, 'error');
    }
}

// Confirm Remove Email
function confirmRemoveEmail(email) {
    if (confirm(`Are you sure you want to remove "${email}" from authorized users?\n\nThis user will lose access to the application.`)) {
        removeEmail(email);
    }
}

// Remove Email
async function removeEmail(email) {
    try {
        const response = await fetch(`/api/emails/${encodeURIComponent(email)}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast(`Email "${email}" removed successfully`, 'success');
            loadEmails(); // Reload the email list
        } else {
            showToast(data.error || 'Failed to remove email', 'error');
        }
    } catch (error) {
        console.error('Error removing email:', error);
        showToast('Network error: ' + error.message, 'error');
    }
}

// Refresh Emails
async function refreshEmails() {
    try {
        const response = await fetch('/api/emails/refresh', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast(`Refreshed ${data.count} emails from disk`, 'success');
            loadEmails(); // Reload the email list
        } else {
            showToast(data.error || 'Failed to refresh emails', 'error');
        }
    } catch (error) {
        console.error('Error refreshing emails:', error);
        showToast('Network error: ' + error.message, 'error');
    }
}

// Toast Notifications
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}