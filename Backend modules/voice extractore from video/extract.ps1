# Voice and Video Extractor - PowerShell Script

# Change to script directory
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Voice and Video Extractor" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Activate virtual environment
& ".\myenv\Scripts\Activate.ps1"

# Check if arguments provided
if ($args.Count -eq 0) {
    Write-Host "Usage: .\extract.ps1 <input_video> [options]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Green
    Write-Host "  .\extract.ps1 video.mp4"
    Write-Host "  .\extract.ps1 video.mp4 -o ./results"
    Write-Host "  .\extract.ps1 video.mkv -a audio.mp3 -v video.mp4"
    Write-Host ""
}
else {
    # Run the extraction script with arguments
    python extract_media.py @args
}

Write-Host ""
