@echo off
REM Voice and Video Extractor - Windows Batch Script

cd /d "%~dp0"

echo.
echo ============================================================
echo   Voice and Video Extractor
echo ============================================================
echo.

REM Activate virtual environment
call myenv\Scripts\activate.bat

REM Check if argument provided
if "%~1"=="" (
    echo Usage: extract.bat input_video.mp4 [options]
    echo.
    echo Examples:
    echo   extract.bat video.mp4
    echo   extract.bat video.mp4 -o ./results
    echo   extract.bat video.mkv -a audio.mp3 -v video.mp4
    echo.
    pause
) else (
    REM Run the extraction script with arguments
    python extract_media.py %*
    pause
)
