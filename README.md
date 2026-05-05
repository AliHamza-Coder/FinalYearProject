# Deceptron — Forensic Multi-Modal Deception Detection

Deceptron is a Python-based final year project for forensic deception analysis. It combines
video and audio processing, behavioral feature extraction, and a desktop UI to provide
a modular deception detection and evidence review system.

---

## Repository Overview

This repository contains several independent modules and a desktop frontend:

- `Backend modules/Complete backend/` — integrated video-based deception pipeline.
- `Backend modules/Communication module/` — live audio/voice analysis and Groq-based text reasoning.
- `Backend modules/Emotions detection/` — facial emotion detection for live camera and recorded video.
- `Backend modules/voice extractore from video/` — media extraction utility for audio/video preprocessing.
- `Frontend/` — Eel-powered desktop UI with user accounts, uploads, recordings, and case management.

---

## Key Modules

### Complete Backend
**Path:** `Backend modules/Complete backend/`

This is the main integrated forensic pipeline. It reads a video file, performs speaker diarization,
extracts visual and acoustic features, and generates a detailed report.

- Entry point: `Backend modules/Complete backend/main.py`
- Output folders: `results/`, `reports/`
- Required environment variables:
  - `HUGGINGFACE_TOKEN`
  - `GROQ_API_KEY`
- Uses `python-dotenv` to load values from `.env`.

See `Backend modules/Complete backend/README.md` for detailed setup and module behavior.

### Communication Module
**Path:** `Backend modules/Communication module/`

A focused voice analysis component for live microphone capture or audio file processing.
It performs acoustic feature extraction and text-based reasoning using Groq.

- Entry point: `Backend modules/Communication module/context_filter.py`
- Requires `GROQ_API_KEY`
- Use `Backend modules/Communication module/example.env` as a template.

### Emotions Detection Module
**Path:** `Backend modules/Emotions detection/`

A facial emotion detection engine that supports live webcam analysis and video file processing.
It also includes a reusable library under `DeceptronLib/`.

- Entry point: `Backend modules/Emotions detection/main.py`
- Designed for real-time emotion capture and timeline output.

### Voice Extractor Utility
**Path:** `Backend modules/voice extractore from video/`

A simple tool for splitting audio/video streams from media files, useful before feeding data
into analysis modules.

- Entry point: `Backend modules/voice extractore from video/extract_media.py`

### Frontend Desktop App
**Path:** `Frontend/`

The desktop application is built with Eel and vanilla JavaScript.
It provides login/signup, upload management, recordings, and user settings.

- Entry point: `Frontend/main.py`
- UI files are in `Frontend/web/`
- Persistent data is stored locally in `~/.deceptron`
- Uses `Frontend/modules/database.py` and TinyDB for storage.

---

## Quick Start

### 1. Install requirements

Install Python 3.9 or newer, then install dependencies separately for the module you want to use.

Example for the complete backend:
```bash
cd "Backend modules/Complete backend/"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Example for the frontend:
```bash
cd Frontend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### 2. Configure environment variables

Use the template file in each module and never commit your actual `.env` file.

For the complete backend:
```env
HUGGINGFACE_TOKEN=your_huggingface_token_here
GROQ_API_KEY=your_groq_api_key_here
```

For the communication module:
```env
GROQ_API_KEY=your_groq_api_key_here
```

For the frontend, no `.env` is required.

---

## Running the App

### Complete backend pipeline
```bash
cd "Backend modules/Complete backend/"
python main.py
```

### Communication module
```bash
cd "Backend modules/Communication module/"
python context_filter.py
```

### Emotions detection
```bash
cd "Backend modules/Emotions detection/"
python main.py
```

### Voice extractor
```bash
cd "Backend modules/voice extractore from video/"
python extract_media.py input_video.mp4
```

### Frontend desktop UI
```bash
cd Frontend
python main.py
```

---

## Important Notes

- `.gitignore` already excludes `.env` and `*.env` files.
- `Backend modules/Complete backend/example_env` now contains placeholder values for safe sharing.
- Keep actual API credentials local and never push them to GitHub.
- Ensure FFmpeg is installed and available in your PATH for video/audio processing.

---

## Additional Resources

- `Backend modules/Complete backend/README.md` — full complete backend instructions.
- `Frontend/README.md` — frontend installation and usage details.
- `Backend modules/Communication module/README.md` — communication module guide.
- `Backend modules/Emotions detection/README.md` — emotion detection guide.
