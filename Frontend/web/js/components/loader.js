const Loader = (function() {
    let loaderEl = null;

    function init() {
        if (document.getElementById('deceptron-global-loader')) return;
        
        const loaderHTML = `
            <div id="deceptron-global-loader" class="fixed inset-0 z-[999999] hidden items-center justify-center bg-black/80 backdrop-blur-xl transition-opacity duration-500 opacity-0">
                <div class="flex flex-col items-center space-y-8">
                    <!-- Roll Spinner -->
                    <div class="w-16 h-16 border-4 border-cyan-500/20 border-t-cyan-500 rounded-full animate-spin shadow-[0_0_15px_rgba(0,219,255,0.2)]"></div>
                    
                    <div class="text-center">
                        <h2 id="loader-title" class="text-xs font-black text-white uppercase tracking-[0.8em] animate-pulse">Securing Evidence</h2>
                    </div>
                </div>
            </div>
            
            <style>
                @keyframes spin-reverse {
                    from { transform: rotate(360deg); }
                    to { transform: rotate(0deg); }
                }
                .animate-spin-reverse {
                    animation: spin-reverse 2s linear infinite;
                }
            </style>
        `;
        document.body.insertAdjacentHTML('beforeend', loaderHTML);
        loaderEl = document.getElementById('deceptron-global-loader');
    }

    function show(title = "Securing Evidence", status = "") {
        init();
        const titleEl = document.getElementById('loader-title');
        const statusEl = document.getElementById('loader-status');
        
        if (titleEl) titleEl.textContent = title;
        if (statusEl) {
            statusEl.textContent = status;
            statusEl.classList.toggle('hidden', !status);
        }
        
        loaderEl.classList.remove('hidden');
        loaderEl.classList.add('flex');
        // Force reflow
        loaderEl.offsetHeight;
        loaderEl.style.opacity = '1';
    }

    function updateProgress(percent) {
        // Disabled per user request for simplicity
    }

    function hide() {
        if (!loaderEl) return;
        loaderEl.style.opacity = '0';
        setTimeout(() => {
            loaderEl.classList.remove('flex');
            loaderEl.classList.add('hidden');
        }, 500);
    }

    return { show, hide, updateProgress };
})();
