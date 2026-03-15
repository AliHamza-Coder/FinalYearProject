# Voice & Video Extractor

Separate voice (audio) and video streams from video files with ease! 🎬🎵

## Overview

This tool extracts audio and video separately from video files. You get:
- **Audio file** (MP3 format) - containing only the voice/sound
- **Video file** (MP4 format) - containing only the video without audio

## Supported Formats

- MP4, AVI, MOV, MKV, FLV, WMV, WebM, M4V

## Installation

1. **Activate the virtual environment:**
   ```bash
   # On Windows PowerShell
   .\myenv\Scripts\Activate.ps1
   
   # Or on Windows CMD
   myenv\Scripts\activate.bat
   ```

2. **Install required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage
Extract both audio and video from a video file:
```bash
python extract_media.py input_video.mp4
```

### Advanced Usage

**Specify output directory:**
```bash
python extract_media.py input_video.mp4 -o ./my_extracts
```

**Custom output file paths:**
```bash
python extract_media.py video.mkv -a my_audio.mp3 -v my_video.mp4
```

**Get help:**
```bash
python extract_media.py --help
```

## Output

By default, extracted files are saved to `extracted_media/` directory:
- `video_name_audio.mp3` - Extracted audio file
- `video_name_video_no_audio.mp4` - Video without audio

## Command Line Arguments

- `video_file`: *(required)* Path to your video file
- `-o, --output-dir`: Directory for extracted files (default: `extracted_media`)
- `-a, --audio-output`: Custom path for audio output
- `-v, --video-output`: Custom path for video output

## Examples

```bash
# Extract from a local video
python extract_media.py ./videos/my_video.mp4

# Extract to specific directory
python extract_media.py my_video.mp4 -o ./results

# Extract with custom file names
python extract_media.py input.mp4 -a voice.mp3 -v video_only.mp4

# Extract from MKV file
python extract_media.py movie.mkv -o ./extracted
```

## Requirements

All dependencies are listed in `requirements.txt` and will be installed when you run:
```bash
pip install -r requirements.txt
```

Key libraries:
- **moviepy** - Main library for video/audio manipulation
- **imageio** & **imageio-ffmpeg** - Video codec support
- **pydub** - Additional audio processing
- **tqdm** - Progress indicators
- **opencv-python** - Advanced video processing

## Troubleshooting

### "No audio found in this video!"
The selected video file doesn't contain an audio track. You'll still get the video file.

### FFmpeg Error
Make sure FFmpeg is installed on your system:
- **Windows**: `choco install ffmpeg` or download from https://ffmpeg.org/download.html
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`

### Import Errors
Make sure you've activated the virtual environment and installed requirements:
```bash
.\myenv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Features

✅ Extract audio to MP3 format  
✅ Extract video without audio in MP4 format  
✅ Batch process multiple files  
✅ Custom output paths  
✅ Progress indication  
✅ Error handling  
✅ Support for multiple video formats  

## License

Free to use and modify.

## Notes

Processing time depends on:
- Video file size
- Video resolution and bitrate
- Your system performance

For large files, processing may take some time. The TQDM library shows progress during extraction.
