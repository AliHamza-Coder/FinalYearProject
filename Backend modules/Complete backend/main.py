"""
main.py – Deceptron FYP Master Integration
===========================================
Processes a video directly, without prompting for an interview question.
All results (annotated videos + JSON report) are saved in results/ and reports/.

Usage:
    python main.py
"""

import os
import sys
import traceback
from dotenv import load_dotenv

# Disable Hugging Face progress bars to fix [WinError 6] The handle is invalid in tqdm
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

# Fix for PyTorch 2.6: Monkey-patch torch.load to default to weights_only=False
# This allows pyannote to load all its custom classes without failing.
try:
    import torch
    _orig_torch_load = torch.load
    def _patched_torch_load(*args, **kwargs):
        # Force weights_only to False regardless of what lightning_fabric passes
        kwargs['weights_only'] = False
        return _orig_torch_load(*args, **kwargs)
    torch.load = _patched_torch_load
except Exception:
    pass

from deception_pipeline import DeceptionPipeline

def main():
    # Load environment variables from .env if present
    load_dotenv()
    
    # Check for required API keys before proceeding
    missing_keys = []
    if not os.environ.get("HUGGINGFACE_TOKEN"):
        missing_keys.append("HUGGINGFACE_TOKEN")
    if not os.environ.get("GROQ_API_KEY"):
        missing_keys.append("GROQ_API_KEY")
        
    if missing_keys:
        print("\nError: Missing required environment variables:")
        for key in missing_keys:
            print(f"  - {key}")
        print("\nPlease set these variables before running the pipeline.")
        print("Example (Windows): set GROQ_API_KEY=your_key")
        print("Example (Linux/Mac): export GROQ_API_KEY=your_key\n")
        return

    video_path = input("Enter the video file path: ").strip().strip('"').strip("'")
    if not os.path.exists(video_path):
        print("Error: File not found.")
        return

    # Use an empty question context – the pipeline will still work
    question_context = ""

    # Check for a pre‑extracted audio file alongside the video
    base, _ = os.path.splitext(video_path)
    candidate_wav = base + ".wav"
    audio_path = None
    if os.path.exists(candidate_wav):
        use_wav = input(f"Found audio '{candidate_wav}'. Use it? (y/n): ").lower()
        if use_wav == 'y':
            audio_path = candidate_wav

    print("\nStarting Deceptron segment-based pipeline...")
    try:
        pipeline = DeceptionPipeline(report_dir="reports", video_dir="results")
        report_path = pipeline.process(video_path, audio_path, question_context=question_context)
        if report_path:
            print(f"\nFinal report saved to: {report_path}")
        else:
            print("\nPipeline finished with warnings - check console output.")
    except Exception as e:
        print("\n" + "=" * 60)
        print("   PIPELINE ENCOUNTERED AN ERROR")
        print("=" * 60)
        # Direct traceback to stdout in case stderr is closed or overridden
        traceback.print_exc(file=sys.stdout)
        print("\nCommon causes:")
        print("- HuggingFace token not set or pyannote model license not accepted.")
        print("- Groq API key missing or invalid.")
        print("- Video file corrupted or no face detected.")
        print("=" * 60)

if __name__ == "__main__":
    main()