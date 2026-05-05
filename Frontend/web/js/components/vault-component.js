/**
 * DECEPTRON Vault Component
 * A reusable premium UI for selecting uploaded evidence.
 */

const VaultComponent = (function() {
    let vaultModal = null;
    let currentUploads = [];
    let onSelectCallback = null;

    // Initialize Vault Modal HTML
    function init() {
        if (document.getElementById('deceptronVaultModal')) return;

        const modalHTML = `
            <div id="deceptronVaultModal" class="fixed inset-0 hidden items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xl transition-all duration-300" style="z-index: 100000 !important;">
                <div class="vault-container relative w-full max-w-3xl bg-[#0f172a] border-2 border-slate-800 rounded-[2.5rem] shadow-2xl overflow-hidden transition-all duration-300 scale-95 opacity-0" style="height: 550px;">
                    <div class="flex items-center justify-between p-8 border-b border-white/5">
                        <div class="flex items-center space-x-4">
                            <div class="w-12 h-12 rounded-2xl bg-primary-blue/10 flex items-center justify-center border border-primary-blue/20">
                                <i class="fas fa-vault text-primary-blue text-xl"></i>
                            </div>
                            <div>
                                <h3 class="text-sm font-black text-white uppercase tracking-[0.2em]">Forensic Vault</h3>
                                <p class="text-[9px] text-slate-500 font-bold uppercase tracking-widest mt-1">Secure Evidence Selection</p>
                            </div>
                        </div>
                        <button onclick="VaultComponent.close()" class="w-10 h-10 rounded-xl bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-all flex items-center justify-center">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>

                    <div class="p-8 pb-6">
                        <div class="relative group">
                            <input type="text" id="vaultSearch" placeholder="Search evidence vault..." 
                                   class="w-full bg-black/20 border-2 border-white/5 rounded-2xl py-4 px-6 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-primary-blue transition-all">
                            <i class="fas fa-search absolute right-6 top-1/2 -translate-y-1/2 text-slate-600 group-focus-within:text-primary-blue transition-colors pointer-events-none"></i>
                        </div>
                    </div>

                    <div class="px-8 pb-8 flex-1 overflow-y-auto custom-scrollbar" id="vaultList" style="height: calc(550px - 220px);">
                    </div>
                </div>
            </div>

            <style>
                #deceptronVaultModal .vault-container { 
                    display: flex;
                    flex-direction: column;
                }
                
                .vault-item {
                    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                    cursor: pointer;
                    margin-bottom: 16px;
                    border: 1px solid rgba(255,255,255,0.05);
                    background: rgba(255,255,255,0.02);
                    border-radius: 1.5rem;
                }
                .vault-item:hover {
                    transform: translateX(8px);
                    background: rgba(37, 99, 235, 0.1);
                    border-color: rgba(37, 99, 235, 0.4);
                    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
                }
                
                .vault-item h4 { color: #ffffff !important; }
                .vault-item p { color: #94a3b8 !important; }

                .custom-scrollbar::-webkit-scrollbar { width: 6px; }
                .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(37, 99, 235, 0.2); border-radius: 10px; }
                
                .custom-scrollbar {
                    scroll-behavior: smooth;
                    -webkit-overflow-scrolling: touch;
                }
            </style>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
        vaultModal = document.getElementById('deceptronVaultModal');

        // Search event
        document.getElementById('vaultSearch').addEventListener('input', (e) => {
            renderItems(e.target.value);
        });

        // Close on backdrop
        vaultModal.addEventListener('click', (e) => {
            if (e.target === vaultModal) close();
        });
    }

    async function open(callback) {
        init();
        onSelectCallback = callback;
        
        // Reset search
        document.getElementById('vaultSearch').value = '';
        
        // Show modal with animation
        vaultModal.classList.remove('hidden');
        vaultModal.classList.add('flex');
        setTimeout(() => {
            vaultModal.querySelector('.vault-container').classList.remove('scale-95', 'opacity-0');
            vaultModal.querySelector('.vault-container').classList.add('scale-100', 'opacity-100');
        }, 10);

        // Fetch data
        renderLoader();
        try {
            const result = await eel.get_uploads()();
            if (result.success) {
                currentUploads = result.data || [];
                renderItems();
            } else {
                console.error("Vault pull failed:", result.message);
                renderError();
            }
        } catch (err) {
            console.error("Vault pull failed:", err);
            renderError();
        }
    }

    function close() {
        if (!vaultModal) return;
        const container = vaultModal.querySelector('.vault-container');
        container.classList.add('scale-95', 'opacity-0');
        setTimeout(() => {
            vaultModal.classList.remove('flex');
            vaultModal.classList.add('hidden');
        }, 300);
    }

    function renderLoader() {
        document.getElementById('vaultList').innerHTML = `
            <div class="flex flex-col items-center justify-center h-full space-y-6">
                <div class="relative w-16 h-16">
                    <div class="absolute inset-0 border-4 border-cyan-500/10 rounded-full"></div>
                    <div class="absolute inset-0 border-4 border-t-cyan-500 rounded-full animate-spin shadow-[0_0_15px_rgba(0,219,255,0.3)]"></div>
                </div>
                <p class="text-[10px] font-black uppercase tracking-[0.4em] text-cyan-400 animate-pulse">Syncing with Forensics Cloud...</p>
            </div>
        `;
    }

    function renderError() {
        document.getElementById('vaultList').innerHTML = `
            <div class="flex flex-col items-center justify-center h-full space-y-4 text-red-400">
                <i class="fas fa-exclamation-triangle text-2xl"></i>
                <p class="text-[10px] font-bold uppercase tracking-widest text-center">Encryption Link Severed.<br>Please re-authenticate.</p>
            </div>
        `;
    }

    function renderItems(filter = '') {
        const list = document.getElementById('vaultList');
        const searchTerm = filter.toLowerCase();
        
        const filtered = currentUploads.filter(item => 
            item.filename.toLowerCase().includes(searchTerm)
        );

        if (filtered.length === 0) {
            list.innerHTML = `
                <div class="flex flex-col items-center justify-center h-full space-y-4 opacity-50 animate-pulse">
                    <div class="w-16 h-16 rounded-full bg-cyan-500/5 flex items-center justify-center border border-cyan-500/10">
                        <i class="fas fa-ghost text-3xl text-cyan-400"></i>
                    </div>
                    <p class="text-[10px] font-black uppercase tracking-[0.3em] text-gray-500">Neural Buffer Empty: No Records</p>
                </div>
            `;
            return;
        }

        list.innerHTML = filtered.map(item => {
            const isVideo = item.type === 'video';
            const icon = isVideo ? 'fa-video' : 'fa-microphone';
            
            return `
                <div class="vault-item group p-4 border border-slate-100 rounded-2xl flex items-center justify-between transition-all hover:bg-white hover:border-cyan-500/50"
                     onclick="VaultComponent.select('${item.id}')">
                    <div class="flex items-center space-x-4">
                        <div class="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center border border-white/10 group-hover:bg-primary-blue/10 group-hover:border-primary-blue/30 transition-all duration-300">
                            <i class="fas ${icon} text-lg text-primary-blue"></i>
                        </div>
                        <div>
                            <h4 class="text-sm font-bold text-slate-800 group-hover:text-primary-blue transition-colors w-64 truncate" title="${item.filename}">${item.filename}</h4>
                            <div class="flex items-center space-x-2 mt-1">
                                <span class="bg-slate-100 px-1.5 py-0.5 rounded text-[9px] font-mono text-slate-500">${item.type.toUpperCase()}</span>
                                <span class="text-[10px] text-slate-400 uppercase font-bold tracking-tighter">${item.timestamp}</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="flex items-center pl-4 bg-white/5 rounded-lg py-1.5 px-3 border border-white/5 group-hover:border-primary-blue/30 transition-colors">
                        <span class="text-[9px] font-black uppercase tracking-widest text-slate-500 mr-3 group-hover:text-white">Select</span>
                        <div class="w-6 h-6 rounded-full bg-slate-800 flex items-center justify-center border border-slate-700 group-hover:bg-primary-blue group-hover:text-white group-hover:border-primary-blue transition-all">
                             <i class="fas fa-arrow-right text-[8px]"></i>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    function select(id) {
        const item = currentUploads.find(u => u.id === id);
        if (item && onSelectCallback) {
            onSelectCallback(item);
            close();
        }
    }

    return {
        open,
        close,
        select
    };
})();