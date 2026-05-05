# Deceptron: Multi-Modal Deception Detection System

Deceptron is an advanced, multi-modal artificial intelligence system designed for forensic deception detection. It analyzes interrogation videos and audio to identify physiological, behavioral, and linguistic markers associated with deceptive behavior.

The system processes video files by isolating suspect speaking segments, running deep analysis across multiple behavioral "channels" (voice, eyes, face, pose, and language), and fusing these signals into a final deception score with natural language reasoning.

---

## 🌟 Features

- **Multi-Modal Analysis**: Combines vocal, facial, gestural, and linguistic cues.
- **Automated Segmentation**: Uses speaker diarization (pyannote.audio) to automatically identify and isolate suspect speaking turns.
- **Natural Language Reasoning**: Generates human-readable explanations for *why* a segment was flagged, using LLM-powered analysis.
- **Visual Evidence**: Generates annotated videos for each module and a combined 2x2 presentation video showing key evidence in a single view.
- **Comprehensive Reporting**: Outputs detailed JSON reports with per-segment scores and overall session conclusions.

---

## 📁 Project Structure

### Core Orchestration
- `deception_pipeline.py`: The master orchestrator that manages the end-to-end workflow.
- `main.py`: The primary command-line entry point for users.
- `fusion_engine.py`: Merges raw scores from different modules into a unified deception probability.
- `reasoning_engine.py`: Synthesizes data into human-readable forensic explanations.

### Analysis Modules
- **Vocal**: `forensic_voice_analyzer.py` (Jitter, Shimmer, Pitch Variance, Pauses, WPM).
- **Facial**:
  - `eye_gaze_module.py`: Tracks gaze stability, focus areas, and blink spikes.
  - `lip_jaw_module.py`: Detects jaw tightness, lip compression, and micro-tremors.
  - `asymmetry_module.py`: Measures micro-asymmetry in facial expressions.
  - `emotion_detection_module.py`: Real-time emotion classification and variance tracking.
- **Gestural & Pose**:
  - `head_pose_module.py`: Analyzes stiffness, withdrawal scores, and nodding/shaking.
  - `hand_face_touch_module.py`: Detects self-soothing gestures (hand-to-face contact).
- **Linguistic**:
  - `nlp_deception_module.py`: Uses Whisper for transcription and Groq (LLM) to analyze verbal patterns for deception flags.

---

## 🚀 Installation

### 1. Prerequisites
- **Python 3.8+**
- **FFmpeg**: Must be installed and available in your system's PATH.

### 2. Clone and Setup Environment
```bash
# Clone the repository
git clone <repository-url>
cd "Python backend modules final"

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## ⚙️ Configuration

The system requires API tokens for speaker diarization and NLP analysis. Create a `.env` file in the root directory:

```env
HUGGINGFACE_TOKEN=your_huggingface_token_here
GROQ_API_KEY=your_groq_api_key_here
```

> [!IMPORTANT]
> **Hugging Face Token**: You must accept the user terms for the `pyannote/speaker-diarization-3.1` and `pyannote/segmentation-3.0` models on Hugging Face to use the diarization feature.

---

## 🛠 Usage

Run the master script:

```bash
python main.py
```

1. Enter the path to your video file (e.g., `video.mp4`).
2. The system will extract audio and begin speaker diarization.
3. It will automatically process segments where the suspect is speaking.
4. Annotated results will appear in the `results/` and `reports/` folders.

---

## 📊 Outputs

- **`results/`**: 
  - Annotated videos for each module (e.g., `video_eye_gaze.mp4`, `video_emotion.mp4`).
  - `video_combined_presentation.mp4`: A 2x2 grid showing Eye, Emotion, Hand, and Lip analysis side-by-side with original audio.
- **`reports/`**:
  - `deception_report_YYYYMMDD_HHMMSS.json`: A deep-dive JSON file containing all scores, transcripts, and natural language reasoning for every analyzed segment.

---

## 🔍 How it Works

1. **Extraction**: Audio is extracted and normalized from the video.
2. **Diarization**: The system identifies different speakers and isolates the suspect's turns.
3. **Multi-Channel Processing**: Each segment is sent to the visual modules (processed frame-by-frame via MediaPipe and OpenCV) and the vocal module (processed via Parselmouth/Praat).
4. **NLP**: Whisper generates a transcript, which is then audited for "deceptive cues" like distancing language or evasiveness.
5. **Fusion**: All results are weighted and fused.
6. **Reasoning**: The system provides a final verdict and a breakdown of deceptive vs. truthful indicators.

---

## ⚠️ Troubleshooting

- **WinError 6 (The handle is invalid)**: This occurs on Windows with `tqdm`. The system automatically disables Hugging Face progress bars to prevent this.
- **FFmpeg not found**: Ensure FFmpeg is installed. Run `ffmpeg -version` in your terminal to verify.
- **No faces detected**: Ensure the video has good lighting and the suspect's face is clearly visible.
