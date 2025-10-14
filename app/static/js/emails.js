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
        
        // Show loading state for fresh data
        const tbody = document.getElementById('emails-tbody');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="3" style="text-align: center; padding: 2rem;">
                        <div class="spinner"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg></div>
                        <div style="margin-top: 0.5rem;">Loading emails...</div>
                    </td>
                </tr>
            `;
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
                            <button class="btn-icon edit" onclick="editEmail('${email}')" title="Edit email">
                                <img src="/static/icons/edit.svg" alt="Edit" style="width: 18px; height: 18px;" aria-hidden="true">
                            </button>
                            <button class="btn-icon delete" onclick="confirmRemoveEmail('${email}')" title="Remove email">
                                <img src="/static/icons/delete.svg" alt="Delete" style="width: 18px; height: 18px;" aria-hidden="true">
                            </button>
                        ` : `
                            <span class="text-muted">Current User</span>
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
    showEmailModal();
}

// Show Add/Edit Email Modal
function showEmailModal(editEmail = null) {
    const modal = document.getElementById('email-modal');
    const form = document.getElementById('email-form');
    const title = document.getElementById('email-modal-title');
    const description = document.getElementById('email-modal-description');
    const submitText = document.getElementById('email-submit-text');
    const emailInput = document.getElementById('new-email');
    const originalEmailInput = document.getElementById('original-email');
    
    form.reset();
    
    if (editEmail) {
        // Edit mode
        title.textContent = 'Edit Authorized Email';
        description.textContent = 'Update the email address. The user will need to log in with the new email.';
        submitText.textContent = 'Update Email';
        emailInput.value = editEmail;
        originalEmailInput.value = editEmail;
    } else {
        // Add mode
        title.textContent = 'Add Authorized Email';
        description.textContent = 'Enter a valid email address to grant access to the application.';
        submitText.textContent = 'Add Email';
        originalEmailInput.value = '';
    }
    
    modal.classList.add('show');
    
    // Focus on email input
    setTimeout(() => {
        emailInput.focus();
        if (editEmail) {
            emailInput.select(); // Select all text for easy editing
        }
    }, 100);
}

// Edit Email
function editEmail(email) {
    // Prevent editing own email
    if (email.toLowerCase() === currentUserEmail.toLowerCase()) {
        showToast('Cannot edit your own email for security reasons', 'warning');
        return;
    }
    
    showEmailModal(email);
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
    const originalEmail = document.getElementById('original-email').value;
    const isEdit = !!originalEmail;
    const submitBtn = document.getElementById('email-submit-btn');
    const originalBtnContent = submitBtn.innerHTML;
    
    if (!email) {
        showToast('Email is required', 'error');
        return;
    }
    
    // If editing and email hasn't changed, just close modal
    if (isEdit && email === originalEmail.toLowerCase()) {
        closeEmailModal();
        return;
    }
    
    // Show loading state
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<div class="spinner"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg></div> ' + (isEdit ? 'Updating...' : 'Adding...');
    
    try {
        let response;
        
        if (isEdit) {
            // Update email (remove old, add new)
            response = await fetch(`/api/emails/${encodeURIComponent(originalEmail)}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email })
            });
        } else {
            // Add new email
            response = await fetch('/api/emails', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email })
            });
        }
        
        const data = await response.json();
        
        if (response.ok) {
            showToast(isEdit ? `Email updated from "${originalEmail}" to "${email}"` : `Email "${email}" added successfully`, 'success');
            closeEmailModal();
            Utils.clearCache('emails'); // Clear cache to force refresh
            loadEmails(); // Reload the email list
        } else {
            showToast(data.error || (isEdit ? 'Failed to update email' : 'Failed to add email'), 'error');
            // Restore button on error
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnContent;
        }
    } catch (error) {
        console.error('Error saving email:', error);
        showToast('Network error: ' + error.message, 'error');
        // Restore button on error
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnContent;
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
    // Find the delete button and add loading state
    const deleteBtn = event.target?.closest('button');
    let originalContent;
    if (deleteBtn) {
        originalContent = deleteBtn.innerHTML;
        deleteBtn.disabled = true;
        deleteBtn.innerHTML = '<div class="spinner"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg></div>';
    }
    
    try {
        const response = await fetch(`/api/emails/${encodeURIComponent(email)}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast(`Email "${email}" removed successfully`, 'success');
            Utils.clearCache('emails'); // Clear cache to force refresh
            loadEmails(); // Reload the email list
        } else {
            showToast(data.error || 'Failed to remove email', 'error');
            
            // Restore button on error
            if (deleteBtn) {
                deleteBtn.disabled = false;
                deleteBtn.innerHTML = originalContent;
            }
        }
    } catch (error) {
        console.error('Error removing email:', error);
        showToast('Network error: ' + error.message, 'error');
        
        // Restore button on error
        if (deleteBtn) {
            deleteBtn.disabled = false;
            deleteBtn.innerHTML = originalContent;
        }
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
            Utils.clearCache('emails'); // Clear cache to force refresh
            loadEmails(); // Reload the email list
        } else {
            showToast(data.error || 'Failed to refresh emails', 'error');
        }
    } catch (error) {
        console.error('Error refreshing emails:', error);
        showToast('Network error: ' + error.message, 'error');
    }
}