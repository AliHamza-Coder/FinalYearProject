// ========================================
// DECEPTRON - LOGIN PAGE
// User authentication logic
// ========================================

document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const btn = e.target.querySelector('button[type="submit"]');
    const originalText = btn.innerText;
    const identity = e.target.querySelector('input[type="text"]').value;
    const password = e.target.querySelector('input[type="password"]').value;

    // UI Loading State
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Signing In...';
    btn.classList.add('opacity-75', 'cursor-not-allowed');

    try {
        if (typeof eel === 'undefined') {
            throw new Error("Server not connected. Please restart the application.");
        }

        const result = await login(identity, password);
        
        if (result.success) {
            window.location.href = 'dashboard.html';
        } else {
            alert("Login failed: " + result.message);
            resetBtn();
        }
    } catch (err) {
        console.error("Login error:", err);
        alert("An error occurred: " + err.message);
        resetBtn();
    }

    function resetBtn() {
        btn.disabled = false;
        btn.innerText = originalText;
        btn.classList.remove('opacity-75', 'cursor-not-allowed');
    }
});
