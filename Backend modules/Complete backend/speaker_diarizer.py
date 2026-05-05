"""
speaker_diarizer.py

Speaker diarization module – identifies WHO spoke WHEN.
Uses pyannote.audio pretrained pipeline.

Class:
    SpeakerDiarizer
        diarize(audio_path) -> list of dicts
"""

import os
import json
import torch
from pyannote.audio import Pipeline


class SpeakerDiarizer:
    """Splits an audio file into speaker‑labelled segments."""

    def __init__(self, device="cpu"):
        """Initialize the diarization pipeline.

        Args:
            device: 'cpu' or 'cuda'.
        """
        self.token = os.environ.get("HUGGINGFACE_TOKEN")
        if not self.token:
            raise ValueError("Please set HUGGINGFACE_TOKEN env variable.")

        self.device = torch.device(device)
        try:
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=self.token
            )
            self.pipeline.to(self.device)
        except Exception as e:
            print(f"Could not load diarization pipeline: {e}")
            print("Make sure you accepted the license at https://huggingface.co/pyannote/speaker-diarization-3.1")
            raise

    def diarize(self, audio_path):
        """Run diarization on a WAV file and return segments.

        Returns:
            list of dicts: [
                {'start': float, 'end': float, 'speaker': str},
                ...
            ]
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        print(f"Running speaker diarization on {audio_path}...")
        diarization = self.pipeline(audio_path)
        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append({
                'start': round(turn.start, 2),
                'end': round(turn.end, 2),
                'speaker': speaker
            })
        print(f"Found {len(segments)} speaker segments.")
        return segments


# ---------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------
if __name__ == "__main__":
    d = SpeakerDiarizer()
    segs = d.diarize("sample_audio.wav")
    for s in segs:
        print(f"[{s['start']:.2f} - {s['end']:.2f}] {s['speaker']}")