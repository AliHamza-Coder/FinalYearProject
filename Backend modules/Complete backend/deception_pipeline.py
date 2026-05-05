"""
deception_pipeline.py

Master orchestrator for the Deceptron deception detection system.
Takes a video (or video+audio), extracts suspect answer segments,
runs all analyzers per segment, fuses results, and generates a
comprehensive JSON report with natural‑language reasoning.

Output:
    - Full annotated videos (one per module) in the "results" directory.
    - A 2x2 combined presentation video (eye, emotion, hand, lip) with audio.
    - Per‑segment deception report JSON in the "reports" directory.

Usage:
    python deception_pipeline.py <video_path> [--audio <audio_path>]
                                   [--report_dir <dir>] [--video_dir <dir>]
"""

import os
import sys
import argparse
import json
import subprocess
import tempfile
import cv2
import numpy as np
from collections import Counter
from typing import Dict, List, Any, Optional
from datetime import datetime
import time

# Import project modules (assumed to be in the same directory)
try:
    from speaker_diarizer import SpeakerDiarizer
    from segment_manager import SegmentManager
    from forensic_voice_analyzer import ForensicVoiceAnalyzer
    from eye_gaze_module import EyeGazeAnalyzer
    from lip_jaw_module import LipJawAnalyzer
    from head_pose_module import HeadPoseAnalyzer
    from hand_face_touch_module import HandFaceTouchAnalyzer
    from asymmetry_module import AsymmetryAnalyzer
    from emotion_detection_module import EmotionAnalyzer
    from nlp_deception_module import NLPDeceptionAnalyzer
    from fusion_engine import FusionEngine
    from reasoning_engine import ReasoningEngine
except ImportError as e:
    print(f"Missing module: {e}")
    print("Make sure all project .py files are in the same directory.")
    sys.exit(1)


class DeceptionPipeline:
    """Orchestrates the full multi‑modal deception detection workflow."""

    def __init__(self, report_dir: str = "reports", video_dir: str = "results"):
        self.report_dir = report_dir
        self.video_dir = video_dir
        os.makedirs(self.report_dir, exist_ok=True)
        os.makedirs(self.video_dir, exist_ok=True)

        # Initialize all analyzers
        print("Initializing analyzers...")
        self.voice_analyzer = ForensicVoiceAnalyzer()
        self.eye_analyzer = EyeGazeAnalyzer()
        self.lip_analyzer = LipJawAnalyzer()
        self.head_analyzer = HeadPoseAnalyzer()
        self.hand_analyzer = HandFaceTouchAnalyzer()
        self.asymmetry_analyzer = AsymmetryAnalyzer()
        self.emotion_analyzer = EmotionAnalyzer()
        self.nlp_analyzer = NLPDeceptionAnalyzer()
        self.fusion_engine = FusionEngine()
        self.reasoning_engine = ReasoningEngine()
        self.segment_manager = SegmentManager()
        print("All analyzers loaded successfully.")

    def process(self, video_path: str, audio_path: Optional[str] = None,
                question_context: str = ""):
        """Run the full pipeline on a video file.

        Args:
            video_path: Path to interrogation video (must contain suspect).
            audio_path: If provided, uses this audio file; otherwise extracts from video.
            question_context: Optional interview question (default empty).

        Returns:
            Path to the generated JSON report.
        """
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"\n{'='*60}")
        print(f"  DECEPTRON DECEPTION PIPELINE - Session {session_id}")
        print(f"{'='*60}\n")

        # ------------------------------------------------------------------
        # 1. Handle audio: extract from video if needed
        # ------------------------------------------------------------------
        if audio_path is None:
            print("Extracting audio from video...")
            audio_path = self._extract_audio(video_path)
            if not audio_path:
                print("Failed to extract audio. Aborting.")
                return None
        else:
            print(f"Using provided audio: {audio_path}")

        # ------------------------------------------------------------------
        # 2. Generate full annotated videos (including emotion)
        # ------------------------------------------------------------------
        stem = os.path.splitext(os.path.basename(video_path))[0]
        self._generate_annotated_videos(video_path, stem)

        # ---- Combine selected videos into a 2x2 presentation video with audio ----
        self._create_combined_video(stem, audio_path)

        # ------------------------------------------------------------------
        # 3. Get suspect answer segments
        # ------------------------------------------------------------------
        print("\nRunning speaker diarization & segmentation...")
        segments = self.segment_manager.get_suspect_segments(audio_path)
        if not segments:
            print("No suspect segments found. Check audio content.")
            return None
        print(f"Found {len(segments)} suspect speaking segments.")

        # ------------------------------------------------------------------
        # 4. Get video FPS and total frames for time‑to‑frame conversion
        # ------------------------------------------------------------------
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()

        # ------------------------------------------------------------------
        # 5. Process each segment
        # ------------------------------------------------------------------
        segment_results = []
        for i, seg in enumerate(segments):
            seg_id = f"SEG_{i+1:03d}"
            start_sec = seg['start']
            end_sec = seg['end']
            seg_audio = seg['audio_file']

            print(f"\n--- Processing Segment {seg_id}: {start_sec:.1f}s - {end_sec:.1f}s ---")

            # Convert time to frame numbers
            start_frame = max(1, int(start_sec * fps))
            end_frame = min(total_frames, int(end_sec * fps))

            # ---- Voice analysis ----
            voice_result = self.voice_analyzer.analyze_segment(
                seg_audio, 0, end_sec - start_sec, suppress_terminal=True)
            if voice_result is None:
                print("  Voice analysis failed, skipping segment.")
                continue
            voice_deception = voice_result.get('deception_analysis', {})
            voice_transcript_orig = voice_result.get('transcription_original', '')
            voice_transcript_en = voice_result.get('transcription_english', '')

            # ---- Eye gaze ----
            eye_data = self.eye_analyzer.process_video(
                video_path, output_path=None,
                start_frame=start_frame, end_frame=end_frame, verbose=False)
            if eye_data:
                avg_fix = np.mean([f['fixation_score'] for f in eye_data])
                avg_stab = np.mean([f['gaze_stability'] for f in eye_data])
                dir_changes = sum(1 for i in range(1, len(eye_data))
                                  if eye_data[i]['focus_area'] != eye_data[i-1]['focus_area'])
                blink_spike = any(f['blink_activity'] for f in eye_data)
                eye_summary = {
                    'gaze_stability': avg_stab,
                    'direction_changes': dir_changes,
                    'fixation_score': avg_fix,
                    'blink_rate_spike': blink_spike
                }
            else:
                eye_summary = {'gaze_stability': 100, 'direction_changes': 0,
                               'fixation_score': 100, 'blink_rate_spike': False}

            # ---- Lip/jaw ----
            lip_data = self.lip_analyzer.process_video(
                video_path, output_path=None,
                start_frame=start_frame, end_frame=end_frame, verbose=False)
            if lip_data:
                avg_jaw = np.mean([f['jaw_tightness'] for f in lip_data])
                avg_oral = np.mean([f['oral_stress'] for f in lip_data])
                avg_tremor = np.mean([f['chin_tremor'] for f in lip_data])
                lip_dis = any(f['lip_disappear'] for f in lip_data)
                lip_summary = {
                    'jaw_tightness': avg_jaw,
                    'lip_compression': avg_oral,
                    'chin_tremor': avg_tremor,
                    'lip_disappear': lip_dis
                }
            else:
                lip_summary = {'jaw_tightness': 0, 'lip_compression': 0,
                               'chin_tremor': 0, 'lip_disappear': False}

            # ---- Head pose ----
            head_data = self.head_analyzer.process_video(
                video_path, output_path=None,
                start_frame=start_frame, end_frame=end_frame, verbose=False)
            if head_data:
                avg_withdr = np.mean([f['withdrawal_score'] for f in head_data])
                avg_stiff = np.mean([f['stiffness_score'] for f in head_data])
                nodding = any(f['is_nodding'] for f in head_data)
                shaking = any(f['is_shaking'] for f in head_data)
                head_summary = {
                    'withdrawal_score': avg_withdr,
                    'stiffness': avg_stiff,
                    'is_nodding': nodding,
                    'is_shaking': shaking
                }
            else:
                head_summary = {'withdrawal_score': 0, 'stiffness': 0,
                                'is_nodding': False, 'is_shaking': False}

            # ---- Asymmetry ----
            asym_data = self.asymmetry_analyzer.process_video(
                video_path, output_path=None,
                start_frame=start_frame, end_frame=end_frame, verbose=False)
            if asym_data:
                avg_total_asym = np.mean([f['total_asym'] for f in asym_data])
                avg_mouth = np.mean([f['mouth_asym'] for f in asym_data])
                avg_brow = np.mean([f['brow_asym'] for f in asym_data])
                asym_summary = {
                    'total_asym': avg_total_asym,
                    'mouth_asym': avg_mouth,
                    'brow_asym': avg_brow
                }
            else:
                asym_summary = {'total_asym': 0, 'mouth_asym': 0, 'brow_asym': 0}

            # ---- Hand/face touch ----
            hand_data = self.hand_analyzer.process_video(
                video_path, output_path=None,
                start_frame=start_frame, end_frame=end_frame, verbose=False)
            if hand_data:
                touches = [f for f in hand_data if f['status'] == 'TOUCHING']
                if touches:
                    max_dur = max(t['duration'] for t in touches)
                    best_touch = max(touches, key=lambda x: x['confidence'])
                    touch_summary = {
                        'touch_score': best_touch['confidence'],
                        'touch_region': best_touch['touch_region'],
                        'touch_duration': max_dur
                    }
                else:
                    touch_summary = {'touch_score': 0, 'touch_region': 'NONE', 'touch_duration': 0}
            else:
                touch_summary = {'touch_score': 0, 'touch_region': 'NONE', 'touch_duration': 0}

            # ---- Emotion (real detector) ----
            emotion_data = self.emotion_analyzer.process_video(
                video_path, output_path=None,
                start_frame=start_frame, end_frame=end_frame, verbose=False)
            if emotion_data:
                emotions = [f['emotion'] for f in emotion_data]
                if emotions:
                    dominant = Counter(emotions).most_common(1)[0][0]
                    changes = sum(1 for i in range(1, len(emotions)) if emotions[i] != emotions[i-1])
                    variance = min(100, (changes / len(emotions)) * 100)
                else:
                    dominant = 'Neutral'; variance = 50
            else:
                dominant = 'Neutral'; variance = 50

            emotion_summary = {
                'dominant_emotion': dominant,
                'emotion_variance': variance
            }

            # Assemble face data dict for fusion
            face_data = {
                'eye_gaze': eye_summary,
                'lip_jaw': lip_summary,
                'head_pose': head_summary,
                'asymmetry': asym_summary,
                'hand_touch': touch_summary,
                'emotion_timeline': emotion_summary
            }

            # ---- NLP analysis ----
            text_for_nlp = voice_transcript_en if voice_transcript_en else voice_transcript_orig
            nlp_result = self.nlp_analyzer.analyze(
                text=text_for_nlp,
                voice_stress=voice_deception.get('overall_deception_score', 0),
                question_context=question_context
            )
            if nlp_result is None:
                nlp_result = {'overall_deception_score': 0, 'triggered_flags': []}

            # ---- Voice data for fusion ----
            voice_data = {
                'jitter': voice_result.get('micro_tremors', {}).get('jitter_local_percent', 0),
                'shimmer': voice_result.get('micro_tremors', {}).get('shimmer_local_percent', 0),
                'pitch_std': voice_result.get('fundamental_frequency', {}).get('f0_std_hz', 0),
                'pitch_variance_category': voice_result.get('fundamental_frequency', {}).get('stability_status', 'Stable'),
                'pause_ratio': voice_result.get('temporal_dynamics', {}).get('pause_ratio_percent', 0),
                'wpm': voice_result.get('temporal_dynamics', {}).get('speaking_rate_wpm', 0),
                'stress_category': voice_deception.get('stress_category', 'Low'),
                'deception_score': voice_deception.get('overall_deception_score', 0)
            }

            # ---- Fusion ----
            fusion_result = self.fusion_engine.fuse(
                face_data=face_data,
                voice_data=voice_data,
                nlp_data=nlp_result,
                timestamps=None
            )

            # ---- Reasoning ----
            reasoning_input = {
                'text': text_for_nlp,
                'face_cues': face_data,
                'voice_stress': voice_data,
                'nlp_flags': nlp_result.get('triggered_flags', []),
                'start_time': start_sec,
                'end_time': end_sec
            }
            reason = self.reasoning_engine.explain(reasoning_input)

            # ---- Compile segment result ----
            seg_result = {
                'segment_id': seg_id,
                'start_sec': start_sec,
                'end_sec': end_sec,
                'transcript_original': voice_transcript_orig,
                'transcript_english': voice_transcript_en,
                'fusion': fusion_result,
                'reasoning': reason,
                'raw_scores': {
                    'voice_stress': voice_deception,
                    'eye_gaze': eye_summary,
                    'lip_jaw': lip_summary,
                    'head_pose': head_summary,
                    'asymmetry': asym_summary,
                    'hand_touch': touch_summary,
                    'emotion': emotion_summary,
                    'nlp': nlp_result
                }
            }
            segment_results.append(seg_result)

            print(f"  → Deception Score: {fusion_result['final_deception_score']:.1f}% "
                  f"({fusion_result['confidence_level']})")
            if fusion_result['is_deceptive']:
                print(f"     Deceptive cues active!")

        # ------------------------------------------------------------------
        # 6. Overall summary & report
        # ------------------------------------------------------------------
        if not segment_results:
            print("No valid segments analyzed.")
            return None

        overall_score = np.mean([s['fusion']['final_deception_score'] for s in segment_results])
        deceptive_segments = sum(1 for s in segment_results if s['fusion']['is_deceptive'])
        total_segs = len(segment_results)

        report = {
            'session_id': session_id,
            'timestamp': datetime.now().isoformat(),
            'video_path': video_path,
            'audio_path': audio_path,
            'question_context': question_context,
            'overall_deception_score': round(overall_score, 1),
            'deceptive_segments': deceptive_segments,
            'total_segments': total_segs,
            'segments': segment_results,
            'conclusion': (
                f"Across {total_segs} analyzed responses, the average deception score was {overall_score:.1f}%. "
                f"{deceptive_segments} segment(s) flagged as deceptive."
            )
        }

        # Save JSON report
        os.makedirs(self.report_dir, exist_ok=True)
        report_path = os.path.join(self.report_dir, f"deception_report_{session_id}.json")
        
        class NumpyEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, (np.bool_,)):
                    return bool(obj)
                if isinstance(obj, (np.integer,)):
                    return int(obj)
                if isinstance(obj, (np.floating,)):
                    return float(obj)
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                return super().default(obj)

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, cls=NumpyEncoder)

        print("\n" + "=" * 60)
        print("   PIPELINE COMPLETE")
        print("=" * 60)
        print(f"Annotated videos saved to: {self.video_dir}/")
        print(f"Combined presentation video with audio: {self.video_dir}/{stem}_combined_presentation.mp4")
        print(f"Processed {total_segs} suspect responses.")
        print(f"Average deception score: {overall_score:.1f}%")
        print(f"Deceptive segments: {deceptive_segments}/{total_segs}")
        print(f"Report saved to: {report_path}")
        print("=" * 60)

        return report_path

    # ------------------------------------------------------------------
    #   Generate annotated full videos (including emotion)
    # ------------------------------------------------------------------
    def _generate_annotated_videos(self, video_path: str, stem: str):
        """Run each visual module on the full video and save annotated copies."""
        print("\nGenerating annotated full videos...")
        modules = {
            'eye_gaze': self.eye_analyzer,
            'lip_jaw': self.lip_analyzer,
            'head_pose': self.head_analyzer,
            'asymmetry': self.asymmetry_analyzer,
            'hand_face': self.hand_analyzer,
            'emotion': self.emotion_analyzer
        }
        for name, analyzer in modules.items():
            out_path = os.path.join(self.video_dir, f"{stem}_{name}.mp4")
            print(f"  Creating {out_path} ...")
            analyzer.process_video(video_path, output_path=out_path, verbose=False)
        print("Annotated videos complete.\n")

    # ------------------------------------------------------------------
    #   Create 2x2 combined presentation video with audio
    # ------------------------------------------------------------------
    def _create_combined_video(self, stem: str, audio_path: str):
        """Stack eye_gaze, emotion, hand_face, lip_jaw in 2x2 grid,
        add original audio, and save as 'stem_combined_presentation.mp4'.
        """
        print("\nCreating 2x2 combined presentation video with audio...")
        # Filenames of the four selected modules
        eye_file = os.path.join(self.video_dir, f"{stem}_eye_gaze.mp4")
        emotion_file = os.path.join(self.video_dir, f"{stem}_emotion.mp4")
        hand_file = os.path.join(self.video_dir, f"{stem}_hand_face.mp4")
        lip_file = os.path.join(self.video_dir, f"{stem}_lip_jaw.mp4")

        # Ensure all four exist; if any missing, skip
        for f in [eye_file, emotion_file, hand_file, lip_file]:
            if not os.path.exists(f):
                print(f"  Warning: {f} not found, skipping combined video.")
                return

        combined_video = os.path.join(self.video_dir, f"{stem}_combined_presentation.mp4")
        
        # ffmpeg xstack 2x2: top-left, top-right, bottom-left, bottom-right
        cmd = [
            "ffmpeg", "-y",
            "-i", eye_file, "-i", emotion_file, "-i", hand_file, "-i", lip_file,
            "-i", audio_path,
            "-filter_complex",
            "[0:v][1:v][2:v][3:v]xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0[v]",
            "-map", "[v]", "-map", "4:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            combined_video
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"  Combined video saved: {combined_video}")
        except subprocess.CalledProcessError as e:
            print(f"  ffmpeg error: {e.stderr}")

    # ------------------------------------------------------------------
    #   Audio extraction
    # ------------------------------------------------------------------
    def _extract_audio(self, video_path: str) -> Optional[str]:
        """Extract audio stream from video using ffmpeg."""
        audio_path = tempfile.mktemp(suffix=".wav")
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1",
            audio_path
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return audio_path
        except subprocess.CalledProcessError as e:
            print(f"ffmpeg error: {e.stderr}")
            return None


# ---------------------------------------------------------------------
#   Command‑line entry point
# ---------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deceptron Deception Detection Pipeline")
    parser.add_argument("video", help="Path to interrogation video file")
    parser.add_argument("--audio", help="Optional extracted audio file (.wav)")
    parser.add_argument("--report_dir", default="reports", help="Directory for report JSON files")
    parser.add_argument("--video_dir", default="results", help="Directory for annotated output videos")
    parser.add_argument("--question", default="", help="Interview question (for better NLP context)")
    args = parser.parse_args()

    pipeline = DeceptionPipeline(report_dir=args.report_dir, video_dir=args.video_dir)
    report_path = pipeline.process(args.video, args.audio, question_context=args.question)
    if report_path:
        print(f"Final report: {report_path}")
    else:
        print("Pipeline failed.")