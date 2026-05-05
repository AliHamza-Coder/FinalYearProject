// ========================================
// DECEPTRON - MEDIA RECORDER MANAGER
// Centralised recording logic shared by
// start-session, voice-analysis, facial-expression
// ========================================

class MediaRecorderManager {
    constructor() {
        this.stream      = null;
        this.recorder    = null;
        this.chunks      = [];
        this.isRecording = false;
    }

    /**
     * Start recording from an existing MediaStream.
     * @param {MediaStream} stream  - Active stream to record.
     * @param {object}      options - MediaRecorder options (mimeType, bitrate, …).
     */
    async startRecording(stream, options = {}) {
        if (this.isRecording) return;

        this.stream  = stream;
        this.chunks  = [];

        // Fallback: try the requested mimeType, then common alternatives
        const mimeType = options.mimeType || 'video/webm';
        const resolvedOptions = MediaRecorder.isTypeSupported(mimeType)
            ? options
            : { ...options, mimeType: 'video/webm' };

        this.recorder = new MediaRecorder(this.stream, resolvedOptions);

        this.recorder.ondataavailable = (event) => {
            if (event.data && event.data.size > 0) {
                this.chunks.push(event.data);
            }
        };

        this.recorder.start(1000);   // collect a chunk every second
        this.isRecording = true;
    }

    /**
     * Stop recording and return a Promise that resolves once the
     * recorder has fully stopped (onstop fires).
     * @returns {Promise<void>}
     */
    stopRecording() {
        return new Promise((resolve) => {
            if (!this.recorder || !this.isRecording) {
                resolve();
                return;
            }

            this.recorder.onstop = () => resolve();
            this.recorder.stop();
            this.isRecording = false;
        });
    }

    /**
     * Build and return a Blob from the collected chunks.
     * @param {string} mimeType - MIME type for the Blob.
     * @returns {Blob|null}
     */
    getBlob(mimeType) {
        if (this.chunks.length === 0) return null;
        return new Blob(this.chunks, { type: mimeType });
    }

    /**
     * Stop the underlying MediaStream tracks (releases camera/mic).
     * @param {string|null} videoElementId - Optional video element to clear.
     */
    stopStream(videoElementId = null) {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        if (videoElementId) {
            const el = document.getElementById(videoElementId);
            if (el) el.srcObject = null;
        }
    }

    /** Reset chunks so the same instance can be re-used for a new session. */
    reset() {
        this.chunks      = [];
        this.isRecording = false;
    }
}
