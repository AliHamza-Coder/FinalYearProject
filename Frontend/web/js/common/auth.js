// ========================================
// DECEPTRON - AUTHENTICATION
// Session management and auth checks
// ========================================

/**
 * Check if user is authenticated
 * @returns {Promise<boolean>} True if authenticated
 */
async function checkSession() {
    try {
        const user = await getCurrentUser();
        return user !== null;
    } catch (error) {
        console.error('Session check failed:', error);
        return false;
    }
}

/**
 * Require authentication - redirect to login if not authenticated
 * @param {string} redirectUrl - URL to redirect to after login
 */
async function requireAuth(redirectUrl = null) {
    const isAuthenticated = await checkSession();
    
    if (!isAuthenticated) {
        // Store intended destination
        if (redirectUrl) {
            sessionStorage.setItem('redirect_after_login', redirectUrl);
        }
        
        // Redirect to login
        window.location.href = 'login.html';
        return false;
    }
    
    return true;
}

/**
 * Handle logout with confirmation
 */
async function handleLogout() {
    if (confirm("Are you sure you want to logout?")) {
        try {
            Loader.show('Logging out...');
            
            await logout();
            
            // Clear any stored data
            sessionStorage.clear();
            
            // Redirect to login
            window.location.href = 'login.html';
        } catch (error) {
            console.error("Logout failed:", error);
            Loader.hide();
            alert('Logout failed. Please try again.');
        }
    }
}

/**
 * Get redirect URL after login
 * @returns {string|null} Redirect URL or null
 */
function getRedirectAfterLogin() {
    const redirect = sessionStorage.getItem('redirect_after_login');
    if (redirect) {
        sessionStorage.removeItem('redirect_after_login');
        return redirect;
    }
    return null;
}

// Expose logout globally for sidebar
window.closeApp = handleLogout;
