// ========================================
// DECEPTRON - API WRAPPER
// Centralized EEL API functions
// ========================================

/**
 * Get current logged-in user
 * @returns {Promise<Object>} User data or null
 */
async function getCurrentUser() {
    try {
        const result = await eel.get_current_user()();
        return result.success ? result.data : null;
    } catch (error) {
        console.error('Get current user failed:', error);
        return null;
    }
}

/**
 * Get user uploads
 * @returns {Promise<Array>} Array of uploads
 */
async function getUploads() {
    try {
        const result = await eel.get_uploads()();
        return result.success ? result.data : [];
    } catch (error) {
        console.error('Get uploads failed:', error);
        return [];
    }
}

/**
 * Upload file using chunked upload
 * @param {File} file - File to upload
 * @param {boolean} isRecording - Is this a recording?
 * @param {Function} progressCallback - Progress callback
 * @returns {Promise<Object>} Upload result
 */
async function uploadFile(file, isRecording = false, progressCallback = null) {
    try {
        const CHUNK_SIZE = 512 * 1024; // 512KB chunks
        const totalSize = `${(file.size / (1024 * 1024)).toFixed(1)} MB`;
        const fileType = file.type.startsWith('video') ? 'video' : 'audio';
        
        // Initiate upload
        const initResult = await eel.initiate_upload(
            file.name,
            totalSize,
            fileType,
            isRecording
        )();
        
        if (!initResult.success) {
            throw new Error(initResult.message || 'Failed to initiate upload');
        }
        
        const uploadId = initResult.data.upload_id;
        const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
        
        // Upload chunks
        for (let i = 0; i < totalChunks; i++) {
            const start = i * CHUNK_SIZE;
            const end = Math.min(start + CHUNK_SIZE, file.size);
            const chunk = file.slice(start, end);
            
            // Convert chunk to base64
            const base64Chunk = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = (e) => resolve(e.target.result);
                reader.onerror = reject;
                reader.readAsDataURL(chunk);
            });
            
            // Send chunk
            const chunkResult = await eel.append_upload_chunk(uploadId, base64Chunk)();
            if (!chunkResult.success) {
                throw new Error('Chunk upload failed');
            }
            
            // Update progress
            if (progressCallback) {
                const progress = Math.round(((i + 1) / totalChunks) * 100);
                progressCallback(progress);
            }
        }
        
        // Finalize upload
        const finalResult = await eel.finalize_upload(uploadId)();
        return finalResult;
        
    } catch (error) {
        console.error('Upload failed:', error);
        return { success: false, message: error.message };
    }
}

/**
 * Update user profile
 * @param {string} name - Full name
 * @param {string} title - Job title
 * @returns {Promise<Object>} Result
 */
async function updateProfile(name, title) {
    try {
        return await eel.update_profile(name, title)();
    } catch (error) {
        console.error('Update profile failed:', error);
        return { success: false, message: error.message };
    }
}

/**
 * Update user avatar
 * @param {string} base64Avatar - Base64 encoded avatar
 * @returns {Promise<Object>} Result
 */
async function updateAvatar(base64Avatar) {
    try {
        return await eel.update_avatar(base64Avatar)();
    } catch (error) {
        console.error('Update avatar failed:', error);
        return { success: false, message: error.message };
    }
}

/**
 * Update password
 * @param {string} currentPassword - Current password
 * @param {string} newPassword - New password
 * @returns {Promise<Object>} Result
 */
async function updatePassword(currentPassword, newPassword) {
    try {
        return await eel.update_password(currentPassword, newPassword)();
    } catch (error) {
        console.error('Update password failed:', error);
        return { success: false, message: error.message };
    }
}

/**
 * Load user preferences
 * @returns {Promise<Object>} Preferences object
 */
async function loadPreferences() {
    try {
        const result = await eel.load_preferences()();
        return result.success ? result.preferences : {};
    } catch (error) {
        console.error('Load preferences failed:', error);
        return {};
    }
}

/**
 * Save user preferences
 * @param {Object} preferences - Preferences to save
 * @returns {Promise<Object>} Result
 */
async function savePreferences(preferences) {
    try {
        return await eel.save_preferences(preferences)();
    } catch (error) {
        console.error('Save preferences failed:', error);
        return { success: false, message: error.message };
    }
}

/**
 * Delete upload record
 * @param {string} uploadId - Upload ID to delete
 * @returns {Promise<Object>} Result
 */
async function deleteUpload(uploadId) {
    try {
        return await eel.delete_upload_record(uploadId)();
    } catch (error) {
        console.error('Delete upload failed:', error);
        return { success: false, message: error.message };
    }
}

/**
 * User login
 * @param {string} identity - Email or username
 * @param {string} password - Password
 * @returns {Promise<Object>} Result with user data
 */
async function login(identity, password) {
    try {
        return await eel.login(identity, password)();
    } catch (error) {
        console.error('Login failed:', error);
        return { success: false, message: error.message };
    }
}

/**
 * User signup
 * @param {Object} userData - User registration data
 * @returns {Promise<Object>} Result
 */
async function signup(userData) {
    try {
        return await eel.signup(userData)();
    } catch (error) {
        console.error('Signup failed:', error);
        return { success: false, message: error.message };
    }
}

/**
 * User logout
 * @returns {Promise<Object>} Result
 */
async function logout() {
    try {
        return await eel.logout()();
    } catch (error) {
        console.error('Logout failed:', error);
        return { success: false, message: error.message };
    }
}
