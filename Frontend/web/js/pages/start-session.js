// ========================================
// DECEPTRON - LIVE SESSION PAGE
// Depends on: constants.js, utils.js, api.js, auth.js, media-recorder.js
// ========================================

const recorder = new MediaRecorderManager();
let activeStream = null;

// ── Camera control ────────────────────────────────────────────────────────────

async function startCamera() {
    try {
        const cameraId = document.getElementById('camera-select').value;
        const micId    = document.getElementById('mic-select').value;

        const constraints = {
            video: cameraId ? { deviceId: { exact: cameraId } } : true,
            audio: micId    ? { deviceId: { exact: micId    } } : true
        };

        activeStream = await startMediaStream(constraints, 'webcam');
        updateStatusUI('live', 'Camera Active');
    } catch (err) {
        console.error('Camera error:', err);
        showToast('Could not access camera/mic. Please check permissions.', 'error');
    }
}

function stopCamera() {
    activeStream = stopMediaStream(activeStream, 'webcam');
    updateStatusUI('ready', 'System Ready');
}

// ── Recording control ─────────────────────────────────────────────────────────

async function startRecording() {
    if (!activeStream) {
        showToast('Please start camera first', 'error');
        return;
    }
    try {
        await recorder.startRecording(activeStream, {
            mimeType: 'video/webm;codecs=vp9',
            videoBitsPerSecond: 2500000
        });
        updateStatusUI('recording', 'Recording...');
    } catch (err) {
        console.error('Recording error:', err);
        showToast('Recording failed: ' + err.message, 'error');
    }
}

async function stopRecording() {
    await recorder.stopRecording();
    updateStatusUI('live', 'Camera Active');
    setTimeout(() => showSaveDialog(), 500);
}

// ── Save ──────────────────────────────────────────────────────────────────────

async function saveRecording() {
    const blob = recorder.getBlob('video/webm');
    if (!blob) { showToast('No recording to save', 'error'); return; }

    const ok = await saveRecordingWithLoader(blob, 'Saving recording...', 'Recording saved successfully!');
    if (ok) recorder.reset();
}

// ── Initialisation ────────────────────────────────────────────────────────────

initializePage(async () => {
    const { cameras, microphones } = await enumerateMediaDevices();
    populateDeviceSelect('camera-select', cameras,    'Camera');
    populateDeviceSelect('mic-select',    microphones, 'Microphone');

    await applyDevicePreferences({ camera: 'camera-select', mic: 'mic-select' });
});
