# Deceptron: Context-Aware Intelligence & Voice Analyzer

Module 1 of the Deceptron Desktop Lie Detection System. This module acts as the "Intake" layer, combining local transcription, AI emotion recognition, and scientific acoustic analysis to filter conversations and detect deception cues.

## 🚀 Key Features

1.  **Continuous Listening**: Multi-threaded architecture captures audio without interruption while processing.
2.  **Voice Analysis (VSA)**:
    - **Acoustic Features**: Extracts **Jitter** (frequency tremors) and **Shimmer** (amplitude stress) to detect physiological nervousness.
    - **Pitch Analysis**: Tracks fundamental frequency shifts (F0).
3.  **AI Emotion Recognition**: Uses `SpeechBrain` (Wav2Vec2) to detect **Fear, Anger, Sadness, or Neutral** states.
4.  **Deception Mismatch Logic**: Detects "Incongruence"—where the spoken text is positive but the vocal tone is fearful or stressed.
5.  **Language Support**:
    - **Input**: Supports English, Urdu, and Roman Urdu (Codeswitching/Mix).
    - **Output**: Unified **Roman Urdu** transcription and reasoning.

## 🛠️ Setup Instructions (Windows)

### 1. Prerequisites

- **Python 3.9** (Mandatory).
- **Groq API Key**: Set in your `.env` file.
- **FFmpeg**: Ensure FFmpeg is installed and added to your system PATH (required for audio processing).

### 2. Install Dependencies

Open your terminal in this directory and run:

```powershell
pip install -r requirements.txt
```

_Note: The first run will download approximately 1GB of AI models for Emotion Analysis and Transcription._

### 3. Run the Module

#### **Mode A: Live Microphone**

Continuously monitor a live conversation.

```powershell
python context_filter.py
```

#### **Mode B: Audio File Analysis**

Process a pre-recorded `.wav` or `.mp3` file.

```powershell
python context_filter.py --file "path/to/evidence.wav"
```

## 📂 File Structure

- `context_filter.py`: Main controller & multi-threaded logic.
- `voice_analysis.py`: AI Emotion & Acoustic feature extraction.
- `requirements.txt`: List of scientific and AI libraries.
- `.env`: API configuration.

## 🧠 Technical Flow

1. **Capture**: Audio is captured via `SpeechRecognition`.
2. **Analyze**: `VoiceAnalyzer` extracts paralinguistic cues (Emotion, Jitter).
3. **Transcribe**: `Faster-Whisper` converts speech to text locally.
4. **Filter**: LLaMA 3.3 70B (Groq) compares **Text** vs **Voice Data** to flag deception (Mismatch).
