// ========================================
// DECEPTRON - SIGNUP PAGE
// User registration logic
// ========================================

document.getElementById('signupForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const btn = e.target.querySelector('button[type="submit"]');
    const originalText = btn.innerText;
    
    // Disable button and show loading state
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating Account...';
    
    const user_data = {
        firstName: e.target.querySelector('input[placeholder="First Name"]').value,
        lastName: e.target.querySelector('input[placeholder="Last Name"]').value,
        username: e.target.querySelector('input[placeholder="Username"]').value,
        email: e.target.querySelector('input[placeholder="Email Address"]').value,
        password: e.target.querySelector('input[placeholder="Create Password"]').value,
        created_at: new Date().toISOString()
    };

    try {
        if (typeof eel === 'undefined') {
            throw new Error("Eel is not loaded. Please restart the application.");
        }

        const result = await signup(user_data);
        if (result.success) {
            // Show success state on button before redirecting
            btn.innerHTML = '<i class="fas fa-check"></i> Success!';
            btn.classList.remove('btn-primary');
            btn.classList.add('bg-green-500');
            
            setTimeout(() => {
                alert("Account created successfully! Please sign in.");
                window.location.href = 'login.html';
            }, 500);
        } else {
            alert("Error: " + result.message);
            resetButton(btn, originalText);
        }
    } catch (err) {
        console.error("Signup error:", err);
        alert("An error occurred: " + err.message);
        resetButton(btn, originalText);
    }
});

function resetButton(btn, text) {
    btn.disabled = false;
    btn.innerText = text;
    btn.classList.add('btn-primary');
    btn.classList.remove('bg-green-500');
}
