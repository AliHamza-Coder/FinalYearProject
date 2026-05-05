// ========================================
// DECEPTRON - SETTINGS PAGE
// Depends on: constants.js, utils.js, api.js, auth.js
// ========================================

let previewStream = null;

// ── Save ──────────────────────────────────────────────────────────────────────

async function saveSettings(event) {
    const btn          = event.currentTarget;
    const originalText = btn.innerText;

    try {
        btn.disabled  = true;
        btn.innerText = 'Saving...';

        const prefs = {
            defaultCamera: document.getElementById('camera-select')?.value,
            defaultMic:    document.getElementById('mic-select')?.value
        };

        const result = await savePreferences(prefs);

        if (result.success) {
            btn.innerText = 'Saved!';
            setTimeout(() => { btn.innerText = originalText; btn.disabled = false; }, 1500);
        } else {
            throw new Error(result.message);
        }
    } catch (e) {
        console.error('Save error:', e);
        btn.innerText = 'ERROR';
        setTimeout(() => { btn.innerText = originalText; btn.disabled = false; }, 2000);
    }
}

// ── Camera preview ────────────────────────────────────────────────────────────

async function startCameraPreview() {
    try {
        const cameraId = document.getElementById('camera-select').value;
        previewStream  = stopMediaStream(previewStream);          // stop old stream first

        previewStream = await startMediaStream(
            { video: { deviceId: cameraId ? { exact: cameraId } : undefined } },
            'camera-preview'
        );
    } catch (err) {
        console.error('Camera preview error:', err);
    }
}

// ── Initialisation ────────────────────────────────────────────────────────────

initializePage(async () => {
    const { cameras, microphones } = await enumerateMediaDevices();
    populateDeviceSelect('camera-select', cameras,     'Camera');
    populateDeviceSelect('mic-select',    microphones, 'Microphone');

    await applyDevicePreferences({ camera: 'camera-select', mic: 'mic-select' });

    document.getElementById('save-settings-btn')?.addEventListener('click', saveSettings);
    document.getElementById('camera-select')?.addEventListener('change', startCameraPreview);
});
