// ========================================
// DECEPTRON - CONSTANTS
// App-wide constants and configuration
// ========================================

// Upload configuration
const CHUNK_SIZE = 512 * 1024; // 512KB chunks
const MAX_FILE_SIZE = 500 * 1024 * 1024; // 500MB max

// Supported MIME types
const MIME_TYPES = {
    VIDEO: ['video/webm', 'video/mp4', 'video/x-matroska'],
    AUDIO: ['audio/webm', 'audio/wav', 'audio/mp3', 'audio/mpeg']
};

// UI constants
const TOAST_DURATION = 3000; // 3 seconds
const DEBOUNCE_DELAY = 300; // 300ms

// Recording constraints
const RECORDING_CONSTRAINTS = {
    VIDEO: {
        width: { ideal: 1280 },
        height: { ideal: 720 },
        frameRate: { ideal: 30 }
    },
    AUDIO: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
    }
};

// Status types
const STATUS_TYPES = {
    READY: 'ready',
    LIVE: 'live',
    RECORDING: 'recording',
    ANALYZING: 'analyzing',
    PAUSED: 'paused'
};
