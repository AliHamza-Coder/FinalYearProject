// ========================================
// DECEPTRON - VOICE ANALYSIS PAGE
// Depends on: constants.js, utils.js, api.js, auth.js, media-recorder.js
// ========================================

const recorder = new MediaRecorderManager();

// ── Recording control ─────────────────────────────────────────────────────────

async function startRecording() {
    try {
        const micId = document.getElementById('mic-select').value;

        const constraints = {
            audio: micId ? { deviceId: { exact: micId } } : {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl:  true
            }
        };

        const stream = await startMediaStream(constraints);
        await recorder.startRecording(stream, { mimeType: 'audio/webm;codecs=opus' });
        updateStatusUI('recording', 'Recording Audio...');
    } catch (err) {
        console.error('Recording error:', err);
        showToast('Could not start recording: ' + err.message, 'error');
    }
}

async function stopRecording() {
    await recorder.stopRecording();
    recorder.stopStream();
    updateStatusUI('ready', 'Recording Complete');
    setTimeout(() => showSaveDialog(), 500);
}

// ── Save ──────────────────────────────────────────────────────────────────────

async function saveRecording() {
    const blob = recorder.getBlob('audio/webm');
    if (!blob) { showToast('No recording to save', 'error'); return; }

    const ok = await saveRecordingWithLoader(blob, 'Saving audio...', 'Audio saved successfully!');
    if (ok) recorder.reset();
}

// ── Initialisation ────────────────────────────────────────────────────────────

initializePage(async () => {
    const { microphones } = await enumerateMediaDevices();
    populateDeviceSelect('mic-select', microphones, 'Microphone');

    await applyDevicePreferences({ mic: 'mic-select' });
});
