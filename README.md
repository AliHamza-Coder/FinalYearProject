# Deceptron — AI-Powered Lie Detection System

Deceptron is a final year project that combines facial emotion recognition, voice stress analysis, and AI-based context filtering to detect deception in real-time conversations. The system is designed for the Pakistani context, with support for English, Urdu, and Roman Urdu.

---

## Project Structure

```
FinalYearProject/
├── Backend modules/
│   ├── Communication module/       # Voice analysis & AI context filtering
│   ├── Emotions detection/         # Facial emotion detection (live & video)
│   └── voice extractore from video/ # Audio/video stream extractor utility
```

---

## Modules Overview

### 1. Communication Module
**Path:** `Backend modules/Communication module/`

The intake layer of Deceptron. Captures live audio or processes audio files, analyzes voice stress, transcribes speech, and uses LLaMA 3.3 70B (via Groq) to detect deception by comparing spoken text against vocal tone.

**Key Features:**
- Continuous multi-threaded microphone listening
- Local speech transcription using Faster-Whisper
- AI emotion recognition via SpeechBrain (Wav2Vec2)
- Acoustic analysis — Jitter, Shimmer, Pitch, HNR, Spectral Brightness
- Fluency & hesitation scoring (WPM, filler words, silence ratio)
- Deception mismatch detection — flags when text is positive but voice shows fear/stress
- Supports English, Urdu, and Roman Urdu input; outputs in Roman Urdu

**Run:**
```bash
# Live microphone mode
python context_filter.py

# Audio file mode
python context_filter.py --file "path/to/audio.wav"
```

**Setup:**
```bash
pip install -r requirements.txt
```
Copy `example.env` to `.env` and add your Groq API key:
```
GROQ_API_KEY=your-api-key-here
```

> First run downloads ~1GB of AI models (SpeechBrain + Whisper).

---

### 2. Emotions Detection Module
**Path:** `Backend modules/Emotions detection/`

Real-time facial emotion detection using MediaPipe for face detection and HSEmotion (EfficientNet) for emotion classification. Supports both live webcam feed and pre-recorded video files.

**Key Features:**
- Live camera emotion detection with bounding box overlay
- Video file processing with frame-by-frame emotion annotation
- Emotion distribution statistics and timeline generation
- GPU acceleration (CUDA) with CPU fallback
- Packaged as a reusable library (`DeceptronLib`) for integration into other projects

**Run:**
```bash
python main.py
```
Select option `1` for live camera or `2` to process a video file.

**Setup:**
```bash
pip install -r requirements.txt
```

**Using as a Library:**
```python
from DeceptronLib.emotion_processor import get_emotion_detector, process_video_file

result = process_video_file("input.mp4")
print(result["stats"])    # Emotion percentages
print(result["timeline"]) # Emotion sequences by frame
```

---

### 3. Voice & Video Extractor
**Path:** `Backend modules/voice extractore from video/`

A utility tool to separate audio and video streams from video files. Useful for preprocessing video evidence before feeding into the analysis pipeline.

**Supported Formats:** MP4, AVI, MOV, MKV, FLV, WMV, WebM, M4V

**Run:**
```bash
python extract_media.py input_video.mp4
python extract_media.py input_video.mp4 -o ./output_folder
```

**Setup:**
```bash
pip install -r requirements.txt
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Facial Emotion | HSEmotion (EfficientNet B0), MediaPipe |
| Voice Emotion | SpeechBrain (Wav2Vec2 / IEMOCAP) |
| Transcription | Faster-Whisper (base model, local) |
| Acoustic Analysis | Praat-Parselmouth, Librosa |
| AI Context Filter | LLaMA 3.3 70B via Groq API |
| Language | Python 3.9 |

---

## Prerequisites

- Python 3.9
- FFmpeg installed and added to system PATH
- Groq API Key (for Communication Module)
- Microphone (for live mode)
- Webcam (for live camera mode)

---

## Important Notes

- Never commit your `.env` file. It is listed in `.gitignore`.
- Use `example.env` as a template to create your own `.env`.
- First-time setup downloads large AI models (~1GB+). Ensure a stable internet connection.
