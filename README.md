
# Deceptron - Lying Detection System by Group Blue Section Blue

Deceptron is a computer vision-based lying detection system. This current version focuses on high-accuracy facial emotion recognition and real-time face tracking.

## 🚀 Features

- **Real-time Face Detection**: Powered by MediaPipe for robust face tracking.
- **Micro-Expression Analysis**: Uses HSEmotion (High-Speed Facial Emotion Recognition) to detect emotions like Happiness, Anger, Sadness, etc.
- **Optimized Performance**: Configured for Python 3.9 with specific library versions to ensure stability on Windows.

## 🛠️ Prerequisites

- **Python 3.9**: The project is optimized and tested for this version.
- **Virtual Environment**: It is highly recommended to run this in a virtual environment (`myenv`).

## 📥 Installation

1. **Clone or Open the directory**:

   ```bash
   cd d:\Deceptron-fyp-fnl
   ```

2. **Activate your Virtual Environment**:

   ```bash
   # Windows
   .\myenv\Scripts\activate
   ```

3. **Install Dependencies**:
   The project requires specific versions of libraries to avoid common crashes (OpenCV/NumPy mismatches).
   ```bash
   pip install -r requirements.txt
   ```

## 🏃 How to Run

To start the real-time camera feed with emotion detection, run:

```bash
python CAmera-Module.py
```

### Controls:

- **'q'**: Press the 'q' key while the camera window is focused to exit.

## 📁 Project Structure

- `CAmera-Module.py`: The main entry point that handles camera input, face detection, and UI overlay.
- `EmotionDetection.py`: Backend module that manages the HSEmotion model loading and inference.
- `requirements.txt`: List of all verified compatible library versions.

## ⚠️ Important Notes

- **Library Patching**: `EmotionDetection.py` includes a built-in patch for `torch.load` to handle security changes in newer PyTorch versions.
- **Protobuf**: If you encounter Protobuf errors, the system is configured to use the `python` implementation via environment variables (handled automatically in most CLI setups).
- **First Run**: On the first execution, the system will automatically download the required emotion detection model (`enet_b0_8_best_vgaf.pt`). This may take a few minutes depending on your internet speed.

---

_Developed for Advanced Agentic Coding - FYP Project Path_
