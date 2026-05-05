"""
segment_manager.py

Extracts suspect answer segments from a full interview video/audio.
Uses speaker diarization and OpenAI Whisper for transcription.

Class:
    SegmentManager
        get_suspect_segments(video_path, audio_path, suspect_label=None)
"""

import os
import subprocess
from pydub import AudioSegment
from speaker_diarizer import SpeakerDiarizer
import whisper


class SegmentManager:
    """Handles speaker separation and answer segmentation."""

    def __init__(self, device="cpu"):
        self.diarizer = SpeakerDiarizer(device=device)
        self.whisper_model = whisper.load_model("base")

    def get_suspect_segments(self, audio_path, suspect_label=None):
        """Identify suspect speaking turns and return their time ranges.

        Returns:
            list of dicts: [{'start': float, 'end': float, 'audio_file': str}, ...]
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio not found: {audio_path}")

        # Step 1: Diarize
        segments = self.diarizer.diarize(audio_path)

        # Step 2: Identify suspect speaker label
        speaker_durations = {}
        for seg in segments:
            speaker = seg['speaker']
            speaker_durations[speaker] = speaker_durations.get(speaker, 0) + seg['end'] - seg['start']

        if not speaker_durations:
            print("No speakers found.")
            return []

        if suspect_label is None:
            suspect_label = max(speaker_durations, key=speaker_durations.get)
        print(f"Suspect speaker label: {suspect_label}")

        suspect_segments = [seg for seg in segments if seg['speaker'] == suspect_label]
        if not suspect_segments:
            print(f"No segments found for speaker {suspect_label}.")
            return []

        merged = self._merge_segments(suspect_segments, gap=0.5)

        full_audio = AudioSegment.from_file(audio_path)
        result = []
        for i, (start, end) in enumerate(merged):
            out_file = f"_segment_{i+1}.wav"
            segment_audio = full_audio[start*1000:end*1000]  # pydub works in ms
            segment_audio.export(out_file, format="wav")
            result.append({
                'start': start,
                'end': end,
                'audio_file': os.path.abspath(out_file)
            })
        print(f"Extracted {len(result)} suspect answer segments.")
        return result

    def _merge_segments(self, segs, gap=0.5):
        if not segs:
            return []
        segs = sorted(segs, key=lambda x: x['start'])
        merged = []
        cur_start = segs[0]['start']
        cur_end = segs[0]['end']
        for s in segs[1:]:
            if s['start'] - cur_end <= gap:
                cur_end = max(cur_end, s['end'])
            else:
                merged.append((cur_start, cur_end))
                cur_start = s['start']
                cur_end = s['end']
        merged.append((cur_start, cur_end))
        return merged