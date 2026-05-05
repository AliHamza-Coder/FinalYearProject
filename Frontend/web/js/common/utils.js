// ========================================
// DECEPTRON - COMMON UTILITIES
// Shared helper functions used across pages
// ========================================

/**
 * Format bytes to human-readable file size
 * @param {number} bytes - File size in bytes
 * @returns {string} Formatted size (e.g., "2.5 MB")
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Format timestamp to readable date/time
 * @param {string|Date} date - Date to format
 * @returns {string} Formatted date
 */
function formatTimestamp(date) {
    if (!date) return 'N/A';
    const d = new Date(date);
    return d.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Show toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type: 'success', 'error', 'info'
 */
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    if (!toast) return;
    
    const messageEl = toast.querySelector('div');
    if (messageEl) {
        messageEl.innerText = message;
    }
    
    // Show toast
    toast.classList.remove('opacity-0', 'translate-y-4');
    toast.classList.add('opacity-1', 'translate-y-0');
    
    // Hide after 3 seconds
    setTimeout(() => {
        toast.classList.add('opacity-0', 'translate-y-4');
        toast.classList.remove('opacity-1', 'translate-y-0');
    }, 3000);
}

/**
 * Update status UI elements
 * @param {string} status - Status type
 * @param {string} message - Status message
 */
function updateStatusUI(status, message) {
    const statusBadge = document.getElementById('status-badge');
    const statusText = document.getElementById('status-text');
    
    if (!statusBadge || !statusText) return;
    
    // Remove all status classes
    statusBadge.classList.remove('status-ready', 'status-live', 'status-recording', 'status-analyzing');
    
    // Add new status class
    statusBadge.classList.add(`status-${status}`);
    statusText.textContent = message;
}

/**
 * Toggle sidebar visibility
 */
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const restoreBtn = document.getElementById('restore-sidebar');
    
    if (!sidebar) return;
    
    if (sidebar.classList.contains('collapsed')) {
        sidebar.classList.remove('collapsed');
        if (restoreBtn) restoreBtn.classList.remove('visible');
    } else {
        sidebar.classList.add('collapsed');
        if (restoreBtn) restoreBtn.classList.add('visible');
    }
}

/**
 * Validate email format
 * @param {string} email - Email to validate
 * @returns {boolean} True if valid
 */
function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

/**
 * Debounce function calls
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in ms
 * @returns {Function} Debounced function
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
 * Generate unique ID
 * @returns {string} Unique ID
 */
function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

// ── Media / Device Utilities ─────────────────────────────────────────────────

/**
 * Return an object with separated camera, microphone and speaker lists.
 * @returns {Promise<{cameras: InputDeviceInfo[], microphones: InputDeviceInfo[], speakers: MediaDeviceInfo[]}>}
 */
async function enumerateMediaDevices() {
    const devices = await navigator.mediaDevices.enumerateDevices();
    return {
        cameras:    devices.filter(d => d.kind === 'videoinput'),
        microphones:devices.filter(d => d.kind === 'audioinput'),
        speakers:   devices.filter(d => d.kind === 'audiooutput')
    };
}

/**
 * Populate a <select> element with media devices.
 * @param {string} selectId     - ID of the <select> element.
 * @param {InputDeviceInfo[]} devices - Devices to populate.
 * @param {string} defaultLabel - Fallback label prefix when device.label is empty.
 */
function populateDeviceSelect(selectId, devices, defaultLabel = 'Device') {
    const select = document.getElementById(selectId);
    if (!select) return;
    select.innerHTML = '';
    devices.forEach((device, i) => {
        const option        = document.createElement('option');
        option.value        = device.deviceId;
        option.textContent  = device.label || `${defaultLabel} ${i + 1}`;
        select.appendChild(option);
    });
}

/**
 * Request a MediaStream and optionally attach it to a video element.
 * @param {MediaStreamConstraints} constraints  - getUserMedia constraints.
 * @param {string|null}            videoElementId - ID of <video> to attach stream.
 * @returns {Promise<MediaStream>}
 */
async function startMediaStream(constraints, videoElementId = null) {
    const stream = await navigator.mediaDevices.getUserMedia(constraints);
    if (videoElementId) {
        const el = document.getElementById(videoElementId);
        if (el) el.srcObject = stream;
    }
    return stream;
}

/**
 * Stop all tracks on a stream and optionally clear a video element.
 * @param {MediaStream|null} stream        - Stream to stop.
 * @param {string|null}      videoElementId - Video element to clear.
 * @returns {null}
 */
function stopMediaStream(stream, videoElementId = null) {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
    }
    if (videoElementId) {
        const el = document.getElementById(videoElementId);
        if (el) el.srcObject = null;
    }
    return null;
}

/**
 * Load saved device preferences and apply them to select elements.
 * @param {{ camera?: string, mic?: string }} selectIds - Map of preference key → select element ID.
 * @returns {Promise<object>} The full preferences object.
 */
async function applyDevicePreferences(selectIds = {}) {
    const prefs = await loadPreferences();
    if (selectIds.camera && prefs.defaultCamera) {
        const el = document.getElementById(selectIds.camera);
        if (el) el.value = prefs.defaultCamera;
    }
    if (selectIds.mic && prefs.defaultMic) {
        const el = document.getElementById(selectIds.mic);
        if (el) el.value = prefs.defaultMic;
    }
    return prefs;
}

/**
 * Upload a Blob and manage Loader UI + feedback messages.
 * @param {Blob}   blob           - The file/recording blob to upload.
 * @param {string} loaderMessage  - Message shown while loading.
 * @param {string} successMessage - Alert text on success.
 * @returns {Promise<boolean>} True on success.
 */
async function saveRecordingWithLoader(blob, loaderMessage = 'Saving...', successMessage = 'Saved successfully!') {
    try {
        if (typeof Loader !== 'undefined') Loader.show(loaderMessage);

        const result = await uploadFile(blob, true, (progress) => {
            if (typeof Loader !== 'undefined') Loader.updateProgress(progress);
        });

        if (result.success) {
            showToast(successMessage, 'success');
            return true;
        } else {
            showToast('Save failed: ' + (result.message || 'Unknown error'), 'error');
            return false;
        }
    } catch (error) {
        console.error('saveRecordingWithLoader error:', error);
        showToast('Save error: ' + error.message, 'error');
        return false;
    } finally {
        if (typeof Loader !== 'undefined') Loader.hide();
    }
}

/**
 * Standard page bootstrap: wait for DOM, check auth, then run the callback.
 * @param {Function} callback - Async function containing page-specific init logic.
 */
function initializePage(callback) {
    document.addEventListener('DOMContentLoaded', async () => {
        await requireAuth();
        if (typeof callback === 'function') await callback();
    });
}

