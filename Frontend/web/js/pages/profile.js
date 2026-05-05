// ========================================
// DECEPTRON - PROFILE PAGE
// User profile management
// ========================================

let pendingAvatarBase64 = null;

// Save profile changes
async function saveProfile() {
    console.log("Save Profile clicked");
    try {
        const name = document.getElementById('edit-name').value;
        const title = document.getElementById('edit-title').value;
        const currentPwd = document.getElementById('current-password').value;
        const newPwd = document.getElementById('new-password').value;

        console.log("Profile data:", { name, title });

        // Update avatar if changed
        if (pendingAvatarBase64) {
            console.log("Updating avatar...");
            const avatarResult = await updateAvatar(pendingAvatarBase64);
            console.log("Avatar result:", avatarResult);
            
            if (!avatarResult.success) {
                alert("Avatar update failed: " + avatarResult.message);
                return;
            }
        }

        // Update profile
        console.log("Updating profile...");
        const result = await updateProfile(name, title);
        console.log("Profile result:", result);

        if (result.success) {
            alert("Profile updated successfully!");
            
            // Update password if provided
            if (currentPwd && newPwd) {
                console.log("Updating password...");
                const pwdResult = await updatePassword(currentPwd, newPwd);
                console.log("Password result:", pwdResult);
                
                if (!pwdResult.success) {
                    alert("Password update failed: " + pwdResult.message);
                }
            }
            
            // Reload page to show changes
            setTimeout(() => location.reload(), 500);
        } else {
            alert("Profile update failed: " + result.message);
        }
    } catch (error) {
        console.error("Save error:", error);
        alert("An error occurred while saving.");
    }
}

// Handle avatar upload
function handleAvatarUpload(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            pendingAvatarBase64 = e.target.result;
            document.getElementById('avatar-preview').src = e.target.result;
        };
        reader.readAsDataURL(file);
    }
}

// Load user profile data
async function loadProfileData() {
    try {
        const user = await getCurrentUser();
        if (user) {
            document.getElementById('edit-name').value = user.fullname || '';
            document.getElementById('edit-title').value = user.title || '';
            
            if (user.avatar) {
                document.getElementById('avatar-preview').src = user.avatar;
            }
        } else {
            window.location.href = 'login.html';
        }
    } catch (error) {
        console.error("Profile load error:", error);
    }
}

// Initialize page
document.addEventListener('DOMContentLoaded', async () => {
    await requireAuth();
    await loadProfileData();
    
    // Attach event listeners
    document.getElementById('save-profile-btn')?.addEventListener('click', saveProfile);
    document.getElementById('avatar-upload')?.addEventListener('change', handleAvatarUpload);
});
