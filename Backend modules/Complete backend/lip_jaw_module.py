"""
lip_jaw_module.py

Lip & Jaw analysis for deception detection.
Uses MediaPipe Face Mesh to track mouth, lips, chin, and jaw.
Measures jaw tightness, oral stress (compressed lips), chin tremor,
and detects lip disappearing (sealed lips).

Now supports optional segment‑based processing (start/end frame).

Class:
    LipJawAnalyzer
        process_video(input_path, output_path=None,
                      start_frame=None, end_frame=None, verbose=True)
        calibrate(neutral_video_path) -> set baselines
"""

import cv2
import mediapipe as mp
import numpy as np
from collections import deque, defaultdict
import os


class LipJawAnalyzer:
    """Analyzes lip compression, jaw tightness, and chin tremor.

    Calibrates baseline distances during the first 5 seconds of the video,
    then scores each subsequent frame relative to those baselines.
    """

    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # Adjustable thresholds
        self.jaw_tightness_threshold = 50
        self.oral_stress_threshold = 50
        self.lip_seal_ratio_threshold = 0.01
        self.tremor_window = 5
        self.tremor_scale = 100.0

        # Key landmarks
        self.NOSE_TIP = 4
        self.CHIN = 152
        self.INNER_LIP_TOP = 13
        self.INNER_LIP_BOTTOM = 14
        self.MOUTH_LEFT = 78
        self.MOUTH_RIGHT = 308
        self.LEFT_EYE_OUTER = 130
        self.RIGHT_EYE_OUTER = 359

        # Baseline storage (set by calibrate() or auto‑calibration)
        self.baseline_nose_chin = None
        self.baseline_lip_ratio = None
        self.baseline_face_scale = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _distance(self, pt1, pt2):
        """Euclidean distance between two (x,y) points."""
        return np.linalg.norm(np.array(pt1) - np.array(pt2))

    def _landmark_point(self, landmarks, idx, img_w, img_h):
        """Return (x, y) pixel coordinates of a landmark."""
        lm = landmarks[idx]
        return (lm.x * img_w, lm.y * img_h)

    def calibrate(self, neutral_video_path):
        """Set baseline distances from a known truthful recording.

        Scans the first 5 seconds of the video and stores averaged metrics.
        Call this before segment‑based processing if you have a neutral clip.
        """
        cap = cv2.VideoCapture(neutral_video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open calibration video: {neutral_video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        calib_duration = 5.0
        max_frames = int(calib_duration * fps)

        nose_chin_vals = []
        lip_ratios = []
        face_scales = []
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1
            if frame_idx > max_frames:
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb)
            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0].landmark
                nose_tip = self._landmark_point(landmarks, self.NOSE_TIP, width, height)
                chin = self._landmark_point(landmarks, self.CHIN, width, height)
                mouth_left = self._landmark_point(landmarks, self.MOUTH_LEFT, width, height)
                mouth_right = self._landmark_point(landmarks, self.MOUTH_RIGHT, width, height)
                lip_top = self._landmark_point(landmarks, self.INNER_LIP_TOP, width, height)
                lip_bottom = self._landmark_point(landmarks, self.INNER_LIP_BOTTOM, width, height)
                left_eye = self._landmark_point(landmarks, self.LEFT_EYE_OUTER, width, height)
                right_eye = self._landmark_point(landmarks, self.RIGHT_EYE_OUTER, width, height)

                nose_chin_vals.append(self._distance(nose_tip, chin))
                face_scales.append(self._distance(left_eye, right_eye))
                mw = self._distance(mouth_left, mouth_right)
                if mw > 0:
                    lip_ratios.append(self._distance(lip_top, lip_bottom) / mw)

        cap.release()
        if nose_chin_vals:
            self.baseline_nose_chin = np.mean(nose_chin_vals)
            self.baseline_face_scale = np.mean(face_scales)
            self.baseline_lip_ratio = np.mean(lip_ratios) if lip_ratios else 0.05
            print(f"Calibration done: nose-chin={self.baseline_nose_chin:.1f}px, "
                  f"face={self.baseline_face_scale:.1f}px, lip-ratio={self.baseline_lip_ratio:.3f}")
        else:
            print("Calibration failed – no face found.")
        return bool(nose_chin_vals)

    # ------------------------------------------------------------------
    # Main processor
    # ------------------------------------------------------------------
    def process_video(self, input_path, output_path=None,
                      start_frame=None, end_frame=None,
                      verbose=True):
        """Process video, draw annotations, save output, return frame data.

        Args:
            input_path (str): Path to the input video.
            output_path (str or None): If not None, annotated video is saved here.
            start_frame (int or None): First frame to process (1‑indexed).
            end_frame (int or None): Last frame to process (inclusive).
            verbose (bool): Whether to print frame‑by‑frame progress.

        Returns:
            list of dicts: Per‑frame metrics.
        """
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {input_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Clamp boundaries
        if start_frame is None:
            start_frame = 1
        if end_frame is None:
            end_frame = total_frames
        start_frame = max(1, start_frame)
        end_frame = min(total_frames, end_frame)

        # Output video writer
        out = None
        if output_path is not None:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        # Auto‑calibration (only if baselines are not set and we process from the very beginning)
        auto_calib = (start_frame == 1 and
                      self.baseline_nose_chin is None)
        if auto_calib:
            calib_nose_chin = []
            calib_lip_ratios = []
            calib_face_scale = []
            calib_duration = 5.0
            calib_ended = False
        else:
            calib_ended = True  # use existing baselines

        # Tremor tracking
        chin_positions = deque(maxlen=self.tremor_window)

        frame_data_list = []
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1

            # Skip before segment
            if frame_idx < start_frame:
                continue
            # Stop after segment
            if frame_idx > end_frame:
                break

            timestamp = frame_idx / fps

            # Defaults (no face)
            jaw_tightness = 0.0
            oral_stress = 0.0
            lip_status = 'NORMAL'
            jaw_status = 'NORMAL'
            chin_tremor = 0.0
            lip_disappear = False

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb)

            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0].landmark

                # Extract points
                nose_tip = self._landmark_point(landmarks, self.NOSE_TIP, width, height)
                chin = self._landmark_point(landmarks, self.CHIN, width, height)
                lip_top = self._landmark_point(landmarks, self.INNER_LIP_TOP, width, height)
                lip_bottom = self._landmark_point(landmarks, self.INNER_LIP_BOTTOM, width, height)
                mouth_left = self._landmark_point(landmarks, self.MOUTH_LEFT, width, height)
                mouth_right = self._landmark_point(landmarks, self.MOUTH_RIGHT, width, height)
                left_eye = self._landmark_point(landmarks, self.LEFT_EYE_OUTER, width, height)
                right_eye = self._landmark_point(landmarks, self.RIGHT_EYE_OUTER, width, height)

                nose_chin_dist = self._distance(nose_tip, chin)
                inner_lip_height = self._distance(lip_top, lip_bottom)
                mouth_width = self._distance(mouth_left, mouth_right)
                face_scale_current = self._distance(left_eye, right_eye)
                lip_ratio = inner_lip_height / mouth_width if mouth_width > 0 else 1.0

                # Auto‑calibration (first 5 seconds of the video)
                if auto_calib and not calib_ended and timestamp <= calib_duration:
                    calib_nose_chin.append(nose_chin_dist)
                    calib_face_scale.append(face_scale_current)
                    if mouth_width > 0:
                        calib_lip_ratios.append(lip_ratio)
                    if out is not None:
                        cv2.putText(frame, "CALIBRATING...", (10, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    frame_data_list.append({
                        'frame_num': frame_idx, 'timestamp': timestamp,
                        'jaw_tightness': 0.0, 'oral_stress': 0.0,
                        'lip_status': 'NORMAL', 'jaw_status': 'NORMAL',
                        'chin_tremor': 0.0, 'lip_disappear': False
                    })
                    if out is not None:
                        out.write(frame)
                    continue

                if auto_calib and not calib_ended:
                    calib_ended = True
                    self.baseline_nose_chin = np.mean(calib_nose_chin) if calib_nose_chin else nose_chin_dist
                    self.baseline_face_scale = np.mean(calib_face_scale) if calib_face_scale else face_scale_current
                    self.baseline_lip_ratio = np.mean(calib_lip_ratios) if calib_lip_ratios else lip_ratio
                    print(f"Auto‑calibration: nose-chin={self.baseline_nose_chin:.1f}px, "
                          f"face={self.baseline_face_scale:.1f}px, lip-ratio={self.baseline_lip_ratio:.3f}")

                # ---- Scores (now using instance baselines) ----
                if self.baseline_nose_chin and self.baseline_nose_chin > 0:
                    ratio_jaw = nose_chin_dist / self.baseline_nose_chin
                    jaw_tightness = max(0.0, min(100.0, (1.0 - ratio_jaw) * 100.0))
                else:
                    jaw_tightness = 0.0

                if self.baseline_lip_ratio and self.baseline_lip_ratio > 0:
                    if lip_ratio < self.baseline_lip_ratio:
                        ratio_oral = lip_ratio / self.baseline_lip_ratio
                        oral_stress = max(0.0, min(100.0, (1.0 - ratio_oral) * 100.0))
                    else:
                        oral_stress = 0.0
                else:
                    oral_stress = 0.0

                lip_disappear = (lip_ratio < self.lip_seal_ratio_threshold)
                jaw_status = 'TENSED' if jaw_tightness >= self.jaw_tightness_threshold else 'NORMAL'
                lip_status = 'TENSED' if oral_stress >= self.oral_stress_threshold else 'NORMAL'

                # Chin tremor
                if self.baseline_face_scale and self.baseline_face_scale > 0:
                    norm_chin = (chin[0] / self.baseline_face_scale, chin[1] / self.baseline_face_scale)
                else:
                    norm_chin = (chin[0], chin[1])
                chin_positions.append(norm_chin)
                if len(chin_positions) >= 2:
                    positions = np.array(chin_positions)
                    mean_pos = np.mean(positions, axis=0)
                    std_dev = np.std(np.linalg.norm(positions - mean_pos, axis=1))
                    chin_tremor = max(0.0, min(100.0, std_dev * self.tremor_scale))

                # ---- Draw overlays (only if output requested) ----
                if out is not None:
                    cv2.line(frame, (int(lip_top[0]), int(lip_top[1])),
                             (int(lip_bottom[0]), int(lip_bottom[1])), (0, 0, 255), 2)
                    cv2.line(frame, (int(mouth_left[0]), int(mouth_left[1])),
                             (int(mouth_right[0]), int(mouth_right[1])), (0, 255, 255), 2)
                    cv2.line(frame, (int(nose_tip[0]), int(nose_tip[1])),
                             (int(chin[0]), int(chin[1])), (0, 165, 255), 2)
                    cv2.circle(frame, (int(chin[0]), int(chin[1])), 4, (0, 255, 0), -1)

                    # Text overlay
                    status_text = (f"Jaw: {jaw_tightness:.0f}% | Oral: {oral_stress:.0f}% | "
                                   f"Jaw: {jaw_status} | Lip: {lip_status} | Tremor: {chin_tremor:.0f}%")
                    if lip_disappear:
                        status_text += " | LIPS DISAPPEAR"
                    if lip_disappear:
                        bg_color = (255, 105, 180)
                    elif jaw_status == 'TENSED' or lip_status == 'TENSED':
                        bg_color = (0, 0, 255)
                    else:
                        bg_color = (0, 255, 0)
                    (tw, th), _ = cv2.getTextSize(status_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                    cv2.rectangle(frame, (5, 5), (5 + tw + 10, 5 + th + 10), bg_color, -1)
                    cv2.putText(frame, status_text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX,
                                0.45, (255, 255, 255), 1, cv2.LINE_AA)

            else:
                if out is not None:
                    cv2.putText(frame, "NO FACE DETECTED", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            if out is not None:
                out.write(frame)

            # Terminal output (only if verbose and face detected)
            if verbose and results.multi_face_landmarks:
                print(f"Frame {frame_idx:04d}: Jaw={jaw_tightness:.1f}% | Oral={oral_stress:.1f}% | "
                      f"Lip={lip_status} | Jaw={jaw_status} | Tremor={chin_tremor:.1f}% | "
                      f"Disappear={'Yes' if lip_disappear else 'No'}")

            frame_data_list.append({
                'frame_num': frame_idx,
                'timestamp': timestamp,
                'jaw_tightness': round(jaw_tightness, 2),
                'oral_stress': round(oral_stress, 2),
                'lip_status': lip_status,
                'jaw_status': jaw_status,
                'chin_tremor': round(chin_tremor, 2),
                'lip_disappear': lip_disappear
            })

        cap.release()
        if out is not None:
            out.release()

        return frame_data_list


# -------------------------------------------------------------------------
#   Standalone execution with detailed terminal output
# -------------------------------------------------------------------------
if __name__ == "__main__":
    input_path = input("Enter the input video path: ").strip().strip('"').strip("'")
    if not os.path.exists(input_path):
        print(f"Error: File '{input_path}' not found.")
        exit(1)

    input_dir = os.path.dirname(input_path) or "."
    stem = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(input_dir, f"{stem}_lipjaw.mp4")

    print(f"Analyzing: {input_path}")
    analyzer = LipJawAnalyzer()
    data = analyzer.process_video(input_path, output_path, verbose=True)

    if not data:
        print("No frames processed.")
        exit(0)

    total_frames = len(data)
    # After auto‑calibration, the first 5 sec are stored but with zero scores – we filter for real data
    eval_data = [d for d in data if d['jaw_tightness'] > 0 or d['oral_stress'] > 0 or d['chin_tremor'] > 0]

    print("\n" + "=" * 50)
    print("         FINAL LIP & JAW ANALYSIS")
    print("=" * 50)
    print(f"Total Frames Processed: {total_frames}")
    print(f"Evaluable frames: {len(eval_data)}")
    print("-" * 50)

    if eval_data:
        avg_jaw = np.mean([d['jaw_tightness'] for d in eval_data])
        avg_oral = np.mean([d['oral_stress'] for d in eval_data])
        avg_tremor = np.mean([d['chin_tremor'] for d in eval_data])
        lip_tensed = sum(1 for d in eval_data if d['lip_status'] == 'TENSED')
        jaw_tensed = sum(1 for d in eval_data if d['jaw_status'] == 'TENSED')
        lip_dis = sum(1 for d in eval_data if d['lip_disappear'])
        tot = len(eval_data)

        print(f"Average Jaw Tightness: {avg_jaw:.1f}%")
        print(f"Average Oral Stress: {avg_oral:.1f}%")
        print(f"Average Chin Tremor: {avg_tremor:.1f}%")
        print(f"Lip TENSED: {lip_tensed/tot*100:.1f}% of time")
        print(f"Jaw TENSED: {jaw_tensed/tot*100:.1f}% of time")
        print(f"Lip Disappear: {lip_dis/tot*100:.1f}% of time")
        print("-" * 50)

        # Status timeline
        print("STATUS TIMELINE (Frame Sequences):")
        status_list = []
        for d in eval_data:
            lip = 'T' if d['lip_status'] == 'TENSED' else 'N'
            jaw = 'T' if d['jaw_status'] == 'TENSED' else 'N'
            disappear = 'D' if d['lip_disappear'] else '-'
            status_list.append((d['frame_num'], f"{lip}{jaw}{disappear}"))

        if status_list:
            seq_start = status_list[0][0]
            cur = status_list[0][1]
            for i in range(1, len(status_list)):
                if status_list[i][1] != cur:
                    end = status_list[i-1][0]
                    ls = 'Tensed' if cur[0]=='T' else 'Normal'
                    js = 'Tensed' if cur[1]=='T' else 'Normal'
                    ds = ' Disappear' if cur[2]=='D' else ''
                    print(f"[{seq_start:04d} to {end:04d}] : Lip {ls}, Jaw {js}{ds} (for {end-seq_start+1} frames)")
                    seq_start = status_list[i][0]
                    cur = status_list[i][1]
            end = status_list[-1][0]
            ls = 'Tensed' if cur[0]=='T' else 'Normal'
            js = 'Tensed' if cur[1]=='T' else 'Normal'
            ds = ' Disappear' if cur[2]=='D' else ''
            print(f"[{seq_start:04d} to {end:04d}] : Lip {ls}, Jaw {js}{ds} (for {end-seq_start+1} frames)")

    print("=" * 50)
    print(f"Output Video Saved: {output_path}")