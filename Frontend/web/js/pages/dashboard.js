// ========================================
// DECEPTRON - DASHBOARD PAGE
// Dashboard initialization and user data display
// ========================================

// Load user data and display
async function loadUserData() {
    try {
        const user = await getCurrentUser();
        if (user) {
            const name = user.fullname || user.username || 'Agent';
            const initials = name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
            const initialsContainer = document.getElementById('profile-initials');
            
            if (user.avatar) {
                initialsContainer.innerHTML = `<img src="${user.avatar}" class="w-full h-full object-cover">`;
                initialsContainer.classList.remove('bg-gradient-to-br', 'from-blue-500', 'to-cyan-400');
            } else {
                initialsContainer.innerText = initials;
            }
        } else {
            window.location.href = 'login.html';
        }
    } catch (err) {
        console.error("Data load failed:", err);
    }
}

// Initialize trend chart
function initTrendChart() {
    const ctx = document.getElementById('trendChart').getContext('2d');
    const trendChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['High Lying Risk', 'Not Sure', 'Trustworthy'],
            datasets: [{
                data: [35, 25, 40],
                backgroundColor: [
                    '#f43f5e', // rose-500
                    '#f59e0b', // amber-500
                    '#10b981'  // emerald-500
                ],
                borderWidth: 0,
                hoverOffset: 10,
                borderRadius: 5
            }]
        },
        options: {
            cutout: '80%',
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    enabled: true,
                    backgroundColor: 'rgba(10, 17, 32, 0.9)',
                    titleFont: { family: 'Orbitron' },
                    bodyFont: { family: 'Inter' },
                    padding: 12,
                    cornerRadius: 12,
                    displayColors: false
                }
            },
            responsive: true,
            maintainAspectRatio: false
        }
    });
}

// Theme toggle functionality
function initThemeToggle() {
    const body = document.body;
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = themeToggle.querySelector('i');

    function toggleTheme() {
        const isLight = body.classList.toggle('light-mode');
        localStorage.setItem('theme', isLight ? 'light' : 'dark');
        updateThemeUI(isLight);
    }

    function updateThemeUI(isLight) {
        themeIcon.className = isLight ? 'fas fa-sun' : 'fas fa-moon';
        themeToggle.classList.toggle('bg-gray-200', isLight);
        themeToggle.classList.toggle('text-gray-900', isLight);
        themeToggle.classList.toggle('border-gray-300', isLight);
    }

    themeToggle.addEventListener('click', toggleTheme);
    
    // Initial state
    updateThemeUI(body.classList.contains('light-mode'));
}

// Navigation item highlighting
function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            navItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');
        });
    });
}

// Page initialization
document.addEventListener('DOMContentLoaded', async () => {
    // Check authentication
    await requireAuth();
    
    // Load user data
    await loadUserData();
    
    // Initialize components
    initTrendChart();
    initThemeToggle();
    initNavigation();
});
