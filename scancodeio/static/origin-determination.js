/**
 * Origin Determination Management
 * Handles interactive features for reviewing and editing code origin determinations
 */

(function() {
    'use strict';

    // State management
    let selectedOrigins = new Set();
    let currentEditingUUID = null;

    // Get CSRF token from cookies
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    const csrftoken = getCookie('csrftoken');

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        initializeSelectionHandlers();
        initializeModalHandlers();
        initializeActionButtons();
    });

    /**
     * Initialize checkbox selection handlers
     */
    function initializeSelectionHandlers() {
        const selectAllCheckbox = document.getElementById('select-all-checkbox');
        const originCheckboxes = document.querySelectorAll('.origin-checkbox');
        
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', function() {
                const isChecked = this.checked;
                originCheckboxes.forEach(checkbox => {
                    checkbox.checked = isChecked;
                    if (isChecked) {
                        selectedOrigins.add(checkbox.value);
                    } else {
                        selectedOrigins.delete(checkbox.value);
                    }
                });
                updateBulkActionButtons();
            });
        }

        originCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                if (this.checked) {
                    selectedOrigins.add(this.value);
                } else {
                    selectedOrigins.delete(this.value);
                }
                updateBulkActionButtons();
                
                // Update select-all checkbox state
                if (selectAllCheckbox) {
                    const allChecked = Array.from(originCheckboxes).every(cb => cb.checked);
                    selectAllCheckbox.checked = allChecked;
                }
            });
        });
    }

    /**
     * Update the state of bulk action buttons based on selection
     */
    function updateBulkActionButtons() {
        const hasSelection = selectedOrigins.size > 0;
        document.getElementById('bulk-verify-btn').disabled = !hasSelection;
        document.getElementById('bulk-amend-btn').disabled = !hasSelection;
        document.getElementById('clear-selection-btn').disabled = !hasSelection;
    }

    /**
     * Initialize modal handlers for editing origins
     */
    function initializeModalHandlers() {
        const modal = document.getElementById('edit-origin-modal');
        const closeModalButtons = [
            document.getElementById('close-edit-modal'),
            document.getElementById('cancel-edit-btn')
        ];
        
        closeModalButtons.forEach(btn => {
            if (btn) {
                btn.addEventListener('click', () => closeModal(modal));
            }
        });

        // Close modal on background click
        const modalBackground = modal.querySelector('.modal-background');
        if (modalBackground) {
            modalBackground.addEventListener('click', () => closeModal(modal));
        }

        // Edit buttons
        document.querySelectorAll('.edit-origin-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const uuid = this.dataset.originUuid;
                openEditModal(uuid);
            });
        });

        // Save button
        const saveBtn = document.getElementById('save-origin-btn');
        if (saveBtn) {
            saveBtn.addEventListener('click', saveOriginChanges);
        }

        // Verify buttons (single)
        document.querySelectorAll('.verify-origin-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const uuid = this.dataset.originUuid;
                verifySingleOrigin(uuid);
            });
        });
    }

    /**
     * Initialize action button handlers
     */
    function initializeActionButtons() {
        const bulkVerifyBtn = document.getElementById('bulk-verify-btn');
        const bulkAmendBtn = document.getElementById('bulk-amend-btn');
        const clearSelectionBtn = document.getElementById('clear-selection-btn');

        if (bulkVerifyBtn) {
            bulkVerifyBtn.addEventListener('click', bulkVerifyOrigins);
        }

        if (bulkAmendBtn) {
            bulkAmendBtn.addEventListener('click', bulkAmendOrigins);
        }

        if (clearSelectionBtn) {
            clearSelectionBtn.addEventListener('click', clearSelection);
        }
    }

    /**
     * Open the edit modal for a specific origin
     */
    function openEditModal(uuid) {
        currentEditingUUID = uuid;
        const row = document.querySelector(`tr[data-origin-uuid="${uuid}"]`);
        
        if (!row) return;

        // Get current values from the row
        const resourcePath = row.querySelector('a').textContent.trim();
        const originIdentifier = row.querySelector('.origin-identifier').textContent.trim();
        
        // Populate modal fields
        document.getElementById('edit-origin-uuid').value = uuid;
        document.getElementById('edit-resource-path').value = resourcePath;
        document.getElementById('edit-origin-identifier').value = 
            originIdentifier === 'Not determined' ? '' : originIdentifier;

        // Fetch full origin data from API
        fetchOriginData(uuid).then(data => {
            if (data) {
                document.getElementById('edit-origin-type').value = 
                    data.amended_origin_type || data.detected_origin_type || '';
                document.getElementById('edit-origin-notes').value = 
                    data.amended_origin_notes || '';
                document.getElementById('edit-is-verified').checked = 
                    data.is_verified || false;
            }
        });

        // Show modal
        const modal = document.getElementById('edit-origin-modal');
        modal.classList.add('is-active');
    }

    /**
     * Close the edit modal
     */
    function closeModal(modal) {
        modal.classList.remove('is-active');
        currentEditingUUID = null;
        
        // Clear form
        document.getElementById('edit-origin-type').value = '';
        document.getElementById('edit-origin-identifier').value = '';
        document.getElementById('edit-origin-notes').value = '';
        document.getElementById('edit-is-verified').checked = false;
    }

    /**
     * Fetch origin data from API
     */
    async function fetchOriginData(uuid) {
        try {
            const response = await fetch(`/api/origin-determinations/${uuid}/`, {
                headers: {
                    'Accept': 'application/json',
                }
            });
            
            if (response.ok) {
                return await response.json();
            } else {
                console.error('Failed to fetch origin data:', response.statusText);
                return null;
            }
        } catch (error) {
            console.error('Error fetching origin data:', error);
            return null;
        }
    }

    /**
     * Save changes to origin determination
     */
    async function saveOriginChanges() {
        const uuid = currentEditingUUID;
        if (!uuid) return;

        const data = {
            amended_origin_type: document.getElementById('edit-origin-type').value,
            amended_origin_identifier: document.getElementById('edit-origin-identifier').value,
            amended_origin_notes: document.getElementById('edit-origin-notes').value,
            is_verified: document.getElementById('edit-is-verified').checked,
            amended_by: 'current_user'  // This should be set from server side based on auth
        };

        try {
            const response = await fetch(`/api/origin-determinations/${uuid}/`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken,
                },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                showNotification('Origin updated successfully!', 'success');
                setTimeout(() => location.reload(), 1000);
            } else {
                const errorData = await response.json();
                showNotification('Failed to update origin: ' + JSON.stringify(errorData), 'danger');
            }
        } catch (error) {
            console.error('Error saving origin:', error);
            showNotification('Error saving origin: ' + error.message, 'danger');
        }
    }

    /**
     * Verify a single origin
     */
    async function verifySingleOrigin(uuid) {
        try {
            const response = await fetch(`/api/origin-determinations/${uuid}/`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken,
                },
                body: JSON.stringify({ is_verified: true })
            });

            if (response.ok) {
                showNotification('Origin verified!', 'success');
                setTimeout(() => location.reload(), 1000);
            } else {
                showNotification('Failed to verify origin', 'danger');
            }
        } catch (error) {
            console.error('Error verifying origin:', error);
            showNotification('Error verifying origin: ' + error.message, 'danger');
        }
    }

    /**
     * Bulk verify selected origins
     */
    async function bulkVerifyOrigins() {
        if (selectedOrigins.size === 0) return;

        const uuids = Array.from(selectedOrigins);
        
        try {
            const response = await fetch('/api/origin-determinations/bulk_verify/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken,
                },
                body: JSON.stringify({ uuids: uuids })
            });

            if (response.ok) {
                const result = await response.json();
                showNotification(`${result.updated_count} origins verified!`, 'success');
                setTimeout(() => location.reload(), 1000);
            } else {
                showNotification('Failed to bulk verify origins', 'danger');
            }
        } catch (error) {
            console.error('Error bulk verifying:', error);
            showNotification('Error bulk verifying: ' + error.message, 'danger');
        }
    }

    /**
     * Bulk amend selected origins
     */
    function bulkAmendOrigins() {
        if (selectedOrigins.size === 0) return;
        
        // For now, open a simple prompt for bulk amendment
        // In a production system, you'd want a more sophisticated modal
        const originType = prompt('Enter origin type for selected items (package/repository/url/unknown):');
        if (!originType) return;
        
        const originIdentifier = prompt('Enter origin identifier:');
        if (!originIdentifier) return;

        const updates = Array.from(selectedOrigins).map(uuid => ({
            uuid: uuid,
            amended_origin_type: originType,
            amended_origin_identifier: originIdentifier,
            amended_by: 'current_user'
        }));

        fetch('/api/origin-determinations/bulk_update/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken,
            },
            body: JSON.stringify({ updates: updates })
        })
        .then(response => response.json())
        .then(result => {
            showNotification(`${result.updated_count} origins updated!`, 'success');
            if (result.errors.length > 0) {
                console.error('Some updates failed:', result.errors);
            }
            setTimeout(() => location.reload(), 1000);
        })
        .catch(error => {
            console.error('Error bulk updating:', error);
            showNotification('Error bulk updating: ' + error.message, 'danger');
        });
    }

    /**
     * Clear all selections
     */
    function clearSelection() {
        selectedOrigins.clear();
        document.querySelectorAll('.origin-checkbox').forEach(cb => cb.checked = false);
        document.getElementById('select-all-checkbox').checked = false;
        updateBulkActionButtons();
    }

    /**
     * Show a notification message
     */
    function showNotification(message, type = 'info') {
        // Using bulma-toast if available
        if (typeof bulmaToast !== 'undefined') {
            bulmaToast.toast({
                message: message,
                type: `is-${type}`,
                dismissible: true,
                duration: 4000,
                position: 'top-right',
            });
        } else {
            // Fallback to alert
            alert(message);
        }
    }

})();
