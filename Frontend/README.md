# 🛡️ DECEPTRON Forensic Suite
### Advanced Multi-Modal Behavioral Analysis & Truth Verification System
**A high-fidelity Final Year Project (FYP) utilizing neural vision and acoustic indicators.**

---

<div align="center">

![Project Version](https://img.shields.io/badge/Version-1.3.0--Enterprise-00dbff?style=for-the-badge&logo=shield)
![Python Backend](https://img.shields.io/badge/Backend-Python--3.9-FFD43B?style=for-the-badge&logo=python)
![Eel UI](https://img.shields.io/badge/Frontend-Vanilla--ES6-blue?style=for-the-badge&logo=javascript)
![License](https://img.shields.io/badge/License-Proprietary-rose?style=for-the-badge)

**"Empowering truth through forensics, one frame at a time."**

</div>

---

## 🎯 Project Overview
**Deceptron** is a cutting-edge forensic desktop application designed to assist analysts in behavioral decoding and truth verification. By combining **Neural Vision** for facial micro-expressions with **Spectral Acoustic Analysis**, the suite provides a comprehensive multi-modal assessment of subjects in real-time or from recorded media.

Built for high-stakes environments, Deceptron features a **"Forensic Neon"** design system, utilizing high-contrast HSL glows, glass-morphism, and a modular architecture optimized for presentation to technical examiners.

---

## ✨ Core Modules & Features

### 📡 Live Analysis Unit
*   **Neural Vision Mapping**: Real-time subject tracking with localized forensic glows.
*   **Multi-Modal Stream**: Dedicated panels for live neural data, acoustic indicators, and subject emotion mapping.
*   **Low-Latency Capture**: High-performance video/audio recording with zero-jitter chunking.

### 🎭 Facial Micro-Expressions
*   **High-Fidelity Detection**: Specialized module for subtle facial changes.
    *   *Real-time indicator feedback using the Deceptron standard (Cyan/Rose).*
*   **Forensic Video Preview**: Clean containerized output with professional telemetry overlays.

### 🎙️ Forensic Voice Analysis
*   **Spectral Indicators**: Real-time frequency stability and acoustic jitter tracking.
*   **Emotion Mapping**: High-contrast HSL emotion cards (Cyan, Purple, Amber, Rose).
*   **Waveform Visualization**: Interactive zoomable waveforms using `WaveSurfer.js`.

### 🗂️ Case Reports & Management
*   **Automated Case Reports**: Instant generation of forensic metrics with trend visualizations.
*   **Evidence Vault**: Secure, persistent storage for all case recordings and uploads.
*   **Universal Search**: Quickly locate cases by analyst, ID, or subject name.

---

## 🛠️ Technical Stack & Architecture

### Frontend (User Interface)
*   **Engine**: EEL (Python-JS Bridge) via Bottle server.
*   **Logic**: Pure ES6 Vanilla JavaScript — Zero heavy frameworks for maximum presentation speed.
*   **Aesthetics**: 
    *   **Forensic Glow System**: HSL-based localized glows for visual telemetry.
    *   **Typography**: *Orbitron* (Telemetry) & *Inter* (Data).
    *   **Responsiveness**: Grid and Flexbox-driven layout with full theme support.

### Backend (Process Management)
*   **Persistent Storage**: `TinyDB` database engine.
    *   *Persistent Architecture*: All databases and media are stored in a secure `.deceptron` directory in the user's local AppData/Home folder to survive system resets.
*   **Execution Runtime**: Python 3.9+ with `gevent` event loop handling.

---

## 📦 Installation & Setup

### Requirements
*   **Python 3.9** (Recommended for forensic module stability)
*   **Chrome/Edge** (For application window rendering)
*   **Camera/Mic** (Physical hardware required; virtual drivers filtered)

### 1. Manual Installation (Standard Pip)
```bash
# Clone the unit
git clone https://github.com/AliHamza-Coder/Deceptron-Fyp-Final-Year-Project.git
cd Deceptron-Fyp-Final-Year-Project

# Activate Forensic Environment
python -m venv venv
venv\Scripts\activate

# Install Core Sensors
pip install -r requirements.txt
python main.py
```

### 2. High-Performance Run (Using UV)
If you have [uv](https://github.com/astral-sh/uv) installed, you can launch the environment instantly:
```bash
uv run python main.py
```

### 3. Quick Run (Windows)
Double-click the **`RUN.bat`** file to automatically initialize the environment and launch the forensic suite.

---

## 🏗️ Building the Executable (Standalone EXE)
To create a portable, standalone version of Deceptron for distribution:

### Using PyInstaller (Standard)
```bash
# Ensure dependencies are installed
pip install pyinstaller
# Build using the included spec file
pyinstaller main.spec
```

### Using UV (Recommended for Speed)
```bash
uv run pyinstaller main.spec
```
The final executable will be located in the `dist/` directory as `deceptron.exe`.

---

## 🚀 Presentation Guide (For FYP Examiners)
When presenting Deceptron, ensure the following modules are showcased:
1.  **Auth Flow**: Demonstrate the secure login with password eye-toggles.
2.  **Live Session**: Start the camera to show the Neural Vision panel.
3.  **Voice Analysis**: Load a pre-recorded `.webm` to show spectral indicators.
4.  **Dashboard Hub**: Showcase the metrics overview and recent case history.
5.  **Evidence Vault**: Show the persistent storage and case deletion flows.

---

## 📝 Project Details
*   **Project Title**: Deceptron — Advanced Truth Verification
*   **Project Lead**: Ali Hamza
*   **Designation**: Final Year Project (FYP)
*   **Version**: 1.3.0 Standard

---

<div align="center">

**Developed with ❤️ and Precision**  
_This project is intended for research and forensic evaluation purposes only._

</div>
