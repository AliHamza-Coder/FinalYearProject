/**
 * DECEPTRON Media Preview - Simplified Procedural Version
 */

// ============================================
// GLOBAL STATE
// ============================================
let activeWaveSurfer = null;

// ============================================
// AUDIO PREVIEW FUNCTIONS
// ============================================

/**
 * Initialize Audio Modal once
 */
function initAudioModal() {
    if (document.getElementById('audioPreviewModal')) return;

    const modalHTML = `
        <div id="audioPreviewModal" class="fixed inset-0 z-[120] hidden items-center justify-center p-4 bg-black/60 backdrop-blur-sm transition-all duration-300">
            <div class="audio-modal-container relative w-full max-w-2xl bg-slate-900 border border-white/10 rounded-3xl shadow-2xl overflow-hidden glass transform transition-all duration-300 scale-95 opacity-0">
                <div class="flex items-center justify-between p-6 border-b border-white/5">
                    <div class="flex items-center space-x-3">
                        <div class="w-10 h-10 rounded-xl bg-cyan-500/10 flex items-center justify-center border border-cyan-500/20">
                            <i class="fas fa-microphone-lines text-cyan-400"></i>
                        </div>
                        <div>
                            <h3 id="audioModalTitle" class="text-xs font-black text-white uppercase tracking-[0.2em]">Forensic Audio Preview</h3>
                            <p class="text-[9px] text-cyan-500/50 font-bold uppercase tracking-widest mt-0.5">Acoustic Logic Pattern</p>
                        </div>
                    </div>
                    <button onclick="closeAudioPreview()" class="w-10 h-10 rounded-xl bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition-all flex items-center justify-center">
                        <i class="fas fa-times"></i>
                    </button>
                </div>

                <div class="p-8 space-y-8">
                    <div class="relative bg-black/40 rounded-2xl p-6 border border-white/5">
                        <div id="audioWaveform" class="w-full"></div>
                        
                        <div class="mt-8 flex items-center justify-between">
                            <div class="flex items-center space-x-6">
                                <button id="audioPlayBtn" onclick="toggleAudioPlayback()" class="w-14 h-14 rounded-2xl bg-cyan-500 text-black flex items-center justify-center transition-all hover:scale-110 active:scale-95 shadow-[0_0_20px_rgba(0,219,255,0.4)]">
                                    <i class="fas fa-play text-xl"></i>
                                </button>
                                
                                <div class="flex flex-col justify-center">
                                    <div id="audioTime" class="text-lg font-black text-white tracking-tighter">00:00 / 00:00</div>
                                    <div class="text-[9px] text-gray-500 uppercase font-black tracking-widest mt-1">Timeline Sync Status: Active</div>
                                </div>
                            </div>

                            <div class="flex items-center space-x-4 bg-white/5 px-4 py-3 rounded-xl border border-white/5">
                                <i class="fas fa-volume-high text-cyan-400 text-sm"></i>
                                <input type="range" id="audioVolume" class="w-24 h-1 bg-white/10 rounded-full appearance-none cursor-pointer audio-slider" min="0" max="100" value="80" oninput="setAudioVolume(this.value)">
                            </div>
                        </div>
                    </div>

                    <div class="flex items-center gap-4">
                        <div class="flex-1 p-3 bg-white/5 rounded-2xl border border-white/5 group hover:border-cyan-500/30 transition-colors">
                            <p class="text-[8px] text-gray-500 uppercase font-black tracking-widest mb-1">File Weight</p>
                            <p id="audioSize" class="text-xs font-black text-white">--</p>
                        </div>
                        <div class="flex-1 p-3 bg-white/5 rounded-2xl border border-white/5 group hover:border-cyan-500/30 transition-colors">
                            <p class="text-[8px] text-gray-500 uppercase font-black tracking-widest mb-1">Duration</p>
                            <p id="audioDuration" class="text-xs font-black text-white">--</p>
                        </div>
                        <div class="flex-1 p-3 bg-white/5 rounded-2xl border border-white/5 group hover:border-cyan-500/30 transition-colors">
                            <p class="text-[8px] text-gray-500 uppercase font-black tracking-widest mb-1">Encryption</p>
                            <p id="audioDate" class="text-xs font-black text-emerald-400">SECURE</p>
                        </div>
                    </div>
                </div>
            </div>
            <style>
                #audioPreviewModal * { box-sizing: border-box; }
                .audio-modal-container { width: 95%; max-width: 650px !important; min-height: 400px; }
                body.light-mode .audio-modal-container { background: #ffffff !important; border-color: rgba(0, 219, 255, 0.4) !important; box-shadow: 0 20px 50px rgba(0, 118, 214, 0.15) !important; }
                body.light-mode #audioModalTitle, body.light-mode #audioTime, body.light-mode #audioSize, body.light-mode #audioDuration { color: #0f172a !important; }
                body.light-mode .audio-modal-container .bg-black\/40 { background: #f8fafc !important; border: 2px solid rgba(0, 219, 255, 0.2) !important; }
                body.light-mode .audio-modal-container .bg-white\/5 { background: #f1f5f9 !important; border: 1px solid rgba(0, 219, 255, 0.1) !important; }
                body.light-mode .audio-modal-container .text-gray-500 { color: #64748b !important; }
                #audioPlayBtn { background-color: #00DBFF !important; color: #000000 !important; border: none !important; cursor: pointer !important; display: flex !important; align-items: center !important; justify-content: center !important; }
                #audioPlayBtn i { color: #000000 !important; font-size: 1.25rem !important; }
                .audio-slider { -webkit-appearance: none; height: 4px; border-radius: 2px; }
                .audio-slider::-webkit-slider-thumb { -webkit-appearance: none; appearance: none; width: 16px; height: 16px; background: #00DBFF; border-radius: 50%; cursor: pointer; border: 2px solid #fff; }
                .glass { backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); }
            </style>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);

    // Close on outside click
    const modal = document.getElementById('audioPreviewModal');
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeAudioPreview();
    });
}

/**
 * Open Audio Preview
 */
function openAudioPreview(filename, filepath, metadata = {}) {
    initAudioModal();
    
    document.getElementById('audioModalTitle').textContent = filename;
    document.getElementById('audioSize').textContent = metadata.size || '--';
    document.getElementById('audioDuration').textContent = '--:--';
    document.getElementById('audioTime').textContent = '00:00 / 00:00';

    const modal = document.getElementById('audioPreviewModal');
    const container = modal.querySelector('.audio-modal-container');
    
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    
    setTimeout(() => {
        container.classList.remove('scale-95', 'opacity-0');
        container.classList.add('scale-100', 'opacity-100');
        
        // Ensure container is clean
        const waveformEl = document.getElementById('audioWaveform');
        if (waveformEl) waveformEl.innerHTML = '';

        // Init WaveSurfer
        const isLight = document.body.classList.contains('light-mode');
        const waveColor = isLight ? '#94a3b8' : 'rgba(255, 255, 255, 0.15)'; 
        const progressColor = '#00DBFF';

        if (activeWaveSurfer) {
            try { activeWaveSurfer.destroy(); } catch(e) {}
        }

        activeWaveSurfer = WaveSurfer.create({
            container: '#audioWaveform',
            waveColor: waveColor,
            progressColor: progressColor,
            cursorColor: '#00DBFF',
            barWidth: 3,
            barRadius: 4,
            responsive: true,
            height: 120, 
            barGap: 4,
            normalize: true
        });

        activeWaveSurfer.load(filepath);

        activeWaveSurfer.on('ready', () => {
            const dur = formatSeconds(activeWaveSurfer.getDuration());
            document.getElementById('audioDuration').textContent = dur;
            updateAudioTime();
        });

        activeWaveSurfer.on('play', () => updateAudioPlayIcon(true));
        activeWaveSurfer.on('pause', () => updateAudioPlayIcon(false));
        activeWaveSurfer.on('finish', () => {
            updateAudioPlayIcon(false);
            activeWaveSurfer.setTime(0); // Reset to start
        });

        activeWaveSurfer.on('error', (err) => {
            console.error('WaveSurfer Error:', err);
            document.getElementById('audioTime').textContent = 'Playback unavailable';
            document.getElementById('audioTime').style.color = '#ef4444';
        });
    }, 10);
}

function closeAudioPreview() {
    if (activeWaveSurfer) {
        activeWaveSurfer.pause();
        activeWaveSurfer.destroy();
        activeWaveSurfer = null;
    }

    const modal = document.getElementById('audioPreviewModal');
    const container = modal.querySelector('.audio-modal-container');
    
    container.classList.remove('scale-100', 'opacity-100');
    container.classList.add('scale-95', 'opacity-0');
    
    setTimeout(() => {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }, 300);
}

function toggleAudioPlayback() {
    if (!activeWaveSurfer) return;
    activeWaveSurfer.playPause();
}

function updateAudioPlayIcon(isPlaying) {
    const icon = document.querySelector('#audioPlayBtn i');
    if (icon) icon.className = isPlaying ? 'fas fa-pause text-xl' : 'fas fa-play text-xl';
}

function updateAudioTime() {
    if (!activeWaveSurfer) return;
    const current = formatSeconds(activeWaveSurfer.getCurrentTime());
    const total = formatSeconds(activeWaveSurfer.getDuration());
    document.getElementById('audioTime').textContent = `${current} / ${total}`;
}

function setAudioVolume(val) {
    if (activeWaveSurfer) activeWaveSurfer.setVolume(val / 100);
}

// ============================================
// VIDEO PREVIEW FUNCTIONS
// ============================================

function initVideoModal() {
    if (document.getElementById('videoPreviewModal')) return;

    const modalHTML = `
        <div id="videoPreviewModal" class="fixed inset-0 z-[120] hidden items-center justify-center p-4 bg-black/60 backdrop-blur-sm transition-all duration-300">
            <div class="video-modal-container relative w-full max-w-4xl bg-slate-900 border border-white/10 rounded-3xl shadow-2xl overflow-hidden glass transform transition-all duration-300 scale-95 opacity-0">
                <div class="flex items-center justify-between p-6 border-b border-white/5">
                    <div class="flex items-center space-x-3">
                        <div class="w-10 h-10 rounded-xl bg-purple-500/10 flex items-center justify-center border border-purple-500/20">
                            <i class="fas fa-video text-purple-400"></i>
                        </div>
                        <div>
                            <h3 id="videoModalTitle" class="text-xs font-black text-white uppercase tracking-[0.2em]">Forensic Video Preview</h3>
                            <p class="text-[9px] text-purple-500/50 font-bold uppercase tracking-widest mt-0.5">Visual Logic Feed</p>
                        </div>
                    </div>
                    <button onclick="closeVideoPreview()" class="w-10 h-10 rounded-xl bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition-all flex items-center justify-center">
                        <i class="fas fa-times"></i>
                    </button>
                </div>

                <div class="p-6 space-y-5">
                    <div class="relative bg-black rounded-2xl overflow-hidden border border-white/10 shadow-2xl flex items-center justify-center" style="height: 350px; background: #000; padding-bottom: 2px;">
                        <video id="videoPreviewPlayer" class="max-w-full max-h-full" style="object-fit: contain;" controls></video>
                    </div>

                    <div class="flex items-center gap-4">
                        <div class="flex-1 p-3 bg-white/5 rounded-2xl border border-white/5 group hover:border-purple-500/30 transition-colors">
                            <p class="text-[8px] text-gray-500 uppercase font-black tracking-widest mb-1">File Weight</p>
                            <p id="videoSize" class="text-xs font-black text-white">--</p>
                        </div>
                        <div class="flex-1 p-3 bg-white/5 rounded-2xl border border-white/5 group hover:border-purple-500/30 transition-colors">
                            <p class="text-[8px] text-gray-500 uppercase font-black tracking-widest mb-1">Duration</p>
                            <p id="videoDuration" class="text-xs font-black text-white">--</p>
                        </div>
                        <div class="flex-1 p-3 bg-white/5 rounded-2xl border border-white/5 group hover:border-purple-500/30 transition-colors">
                            <p class="text-[8px] text-gray-500 uppercase font-black tracking-widest mb-1">Encryption</p>
                            <p id="videoDate" class="text-xs font-black text-emerald-400">SECURE</p>
                        </div>
                    </div>
                </div>
            </div>
            <style>
                #videoPreviewModal * { box-sizing: border-box; }
                .video-modal-container { width: 95%; max-width: 800px !important; }
                body.light-mode .video-modal-container { background: #ffffff !important; border-color: rgba(139, 92, 246, 0.4) !important; box-shadow: 0 20px 50px rgba(139, 92, 246, 0.15) !important; }
                body.light-mode #videoModalTitle, body.light-mode #videoSize, body.light-mode #videoDuration { color: #0f172a !important; }
                body.light-mode .video-modal-container .bg-white\/5 { background: #f5f3ff !important; border: 1px solid rgba(139, 92, 246, 0.1) !important; }
                body.light-mode .video-modal-container .text-gray-500 { color: #64748b !important; }
            </style>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);

    const modal = document.getElementById('videoPreviewModal');
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeVideoPreview();
    });

    const vPlayer = document.getElementById('videoPreviewPlayer');
    vPlayer.addEventListener('loadedmetadata', () => {
        document.getElementById('videoDuration').textContent = formatSeconds(vPlayer.duration);
    });
}

function openVideoPreview(filename, filepath, metadata = {}) {
    initVideoModal();
    
    document.getElementById('videoModalTitle').textContent = filename;
    document.getElementById('videoSize').textContent = metadata.size || '--';
    
    const vPlayer = document.getElementById('videoPreviewPlayer');
    vPlayer.src = filepath;
    vPlayer.load();

    const modal = document.getElementById('videoPreviewModal');
    const container = modal.querySelector('.video-modal-container');
    
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    
    setTimeout(() => {
        container.classList.remove('scale-95', 'opacity-0');
        container.classList.add('scale-100', 'opacity-100');
    }, 10);
}

function closeVideoPreview() {
    const vPlayer = document.getElementById('videoPreviewPlayer');
    if (vPlayer) {
        vPlayer.pause();
        vPlayer.src = '';
    }

    const modal = document.getElementById('videoPreviewModal');
    const container = modal.querySelector('.video-modal-container');
    
    container.classList.remove('scale-100', 'opacity-100');
    container.classList.add('scale-95', 'opacity-0');
    
    setTimeout(() => {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }, 300);
}

// ============================================
// HELPERS
// ============================================

function formatSeconds(seconds) {
    if (isNaN(seconds)) return '00:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// Export global objects to match previous API if needed
window.audioPreview = { open: openAudioPreview, close: closeAudioPreview };
window.videoPreview = { open: openVideoPreview, close: closeVideoPreview };
