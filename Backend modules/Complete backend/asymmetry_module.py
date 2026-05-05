"""
asymmetry_module.py

Facial asymmetry analysis for deception detection.
Uses MediaPipe Face Mesh (468 landmarks) to measure left/right feature
asymmetry relative to the nose bridge.

Now supports optional segment processing (start/end frame) and
external calibration.

Class:
    AsymmetryAnalyzer
        calibrate(neutral_video_path) -> set baselines
        process_video(input_path, output_path=None,
                      start_frame=None, end_frame=None, verbose=True)
"""

import cv2
import mediapipe as mp
import numpy as np
from collections import defaultdict
import os


class AsymmetryAnalyzer:
    """Detects facial asymmetry relative to a personal baseline.

    Calibration stores resting asymmetry; all subsequent frames show
    deviation from that norm.
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

        # Key landmarks
        self.NOSE_BRIDGE = 6
        self.CHIN = 152
        self.MOUTH_LEFT = 61
        self.MOUTH_RIGHT = 291
        self.BROW_LEFT = 105
        self.BROW_RIGHT = 334
        self.EYE_LEFT = 33
        self.EYE_RIGHT = 263

        # Thresholds
        self.asymmetry_threshold = 15.0
        self.alert_threshold = 30.0

        # Baseline storage (set by calibrate() or auto‑calibration)
        self.baseline_mouth = None
        self.baseline_brow = None
        self.baseline_eye = None

    # ------------------------------------------------------------------
    # Public calibration
    # ------------------------------------------------------------------
    def calibrate(self, neutral_video_path):
        """Set baseline asymmetries from a known neutral recording.

        Scans first 5 seconds and stores average raw asymmetries.
        """
        cap = cv2.VideoCapture(neutral_video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open calibration video: {neutral_video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        calib_duration = 5.0
        max_frames = int(calib_duration * fps)

        mouth_vals, brow_vals, eye_vals = [], [], []
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
                mouth_vals.append(self._raw_asymmetry(
                    landmarks, self.NOSE_BRIDGE, self.MOUTH_LEFT, self.MOUTH_RIGHT,
                    width, height))
                brow_vals.append(self._raw_asymmetry(
                    landmarks, self.NOSE_BRIDGE, self.BROW_LEFT, self.BROW_RIGHT,
                    width, height))
                eye_vals.append(self._raw_asymmetry(
                    landmarks, self.NOSE_BRIDGE, self.EYE_LEFT, self.EYE_RIGHT,
                    width, height))

        cap.release()
        if mouth_vals:
            self.baseline_mouth = np.mean(mouth_vals)
            self.baseline_brow = np.mean(brow_vals)
            self.baseline_eye = np.mean(eye_vals)
            print(f"Calibration baselines → Mouth: {self.baseline_mouth:.1f}%  "
                  f"Brow: {self.baseline_brow:.1f}%  Eye: {self.baseline_eye:.1f}%")
            return True
        print("Calibration failed – no face detected.")
        return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _distance(self, pt1, pt2):
        return np.linalg.norm(np.array(pt1) - np.array(pt2))

    def _landmark_point(self, landmarks, idx, img_w, img_h):
        lm = landmarks[idx]
        return (int(lm.x * img_w), int(lm.y * img_h))

    def _raw_asymmetry(self, landmarks, center_idx, left_idx, right_idx,
                       img_w, img_h):
        """Return raw (0-100) asymmetry for one facial region."""
        center = self._landmark_point(landmarks, center_idx, img_w, img_h)
        left = self._landmark_point(landmarks, left_idx, img_w, img_h)
        right = self._landmark_point(landmarks, right_idx, img_w, img_h)

        dist_left = self._distance(center, left)
        dist_right = self._distance(center, right)
        avg_dist = (dist_left + dist_right) / 2.0

        if avg_dist < 1e-6:
            return 0.0
        raw = (abs(dist_left - dist_right) / avg_dist) * 100.0
        return min(raw, 100.0)

    # ------------------------------------------------------------------
    # Main processor
    # ------------------------------------------------------------------
    def process_video(self, input_path, output_path=None,
                      start_frame=None, end_frame=None,
                      verbose=True):
        """Analyze video, draw annotations, save output, return frame data.

        Args:
            input_path: path to video file.
            output_path: if not None, save annotated video here.
            start_frame: first frame (1‑indexed).
            end_frame: last frame (inclusive).
            verbose: print frame‑by‑frame terminal output.

        Returns:
            list of dicts: per‑frame metrics.
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

        # Auto‑calibration (only if no baseline set and we start from frame 1)
        auto_calib = (start_frame == 1 and
                      self.baseline_mouth is None)
        if auto_calib:
            calib_duration = 5.0
            calib_ended = False
            calib_mouth = []
            calib_brow = []
            calib_eye = []
        else:
            calib_ended = True   # use existing baselines

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

            # Defaults
            raw_mouth = 0.0
            raw_brow = 0.0
            raw_eye = 0.0
            mouth_dev = 0.0
            brow_dev = 0.0
            eye_dev = 0.0
            total_dev = 0.0
            status = 'SYMMETRIC'

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb)

            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0].landmark

                raw_mouth = self._raw_asymmetry(
                    landmarks, self.NOSE_BRIDGE, self.MOUTH_LEFT, self.MOUTH_RIGHT,
                    width, height)
                raw_brow = self._raw_asymmetry(
                    landmarks, self.NOSE_BRIDGE, self.BROW_LEFT, self.BROW_RIGHT,
                    width, height)
                raw_eye = self._raw_asymmetry(
                    landmarks, self.NOSE_BRIDGE, self.EYE_LEFT, self.EYE_RIGHT,
                    width, height)

                # Auto‑calibration
                if auto_calib and not calib_ended and timestamp <= calib_duration:
                    calib_mouth.append(raw_mouth)
                    calib_brow.append(raw_brow)
                    calib_eye.append(raw_eye)
                    if out is not None:
                        cv2.putText(frame, "CALIBRATING...", (10, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    frame_data_list.append({
                        'frame_num': frame_idx, 'timestamp': timestamp,
                        'mouth_asym': 0.0, 'brow_asym': 0.0, 'eye_asym': 0.0,
                        'total_asym': 0.0, 'status': 'SYMMETRIC'
                    })
                    if out is not None:
                        out.write(frame)
                    continue

                if auto_calib and not calib_ended:
                    calib_ended = True
                    self.baseline_mouth = np.mean(calib_mouth) if calib_mouth else raw_mouth
                    self.baseline_brow = np.mean(calib_brow) if calib_brow else raw_brow
                    self.baseline_eye = np.mean(calib_eye) if calib_eye else raw_eye
                    print(f"Auto‑calibration baselines → Mouth: {self.baseline_mouth:.1f}%  "
                          f"Brow: {self.baseline_brow:.1f}%  Eye: {self.baseline_eye:.1f}%")

                # Deviation scores (relative to baselines)
                if self.baseline_mouth is not None:
                    mouth_dev = max(0.0, raw_mouth - self.baseline_mouth)
                    brow_dev = max(0.0, raw_brow - self.baseline_brow)
                    eye_dev = max(0.0, raw_eye - self.baseline_eye)
                    total_dev = (mouth_dev + brow_dev + eye_dev) / 3.0
                else:
                    total_dev = 0.0

                status = 'ASYMMETRIC' if total_dev >= self.asymmetry_threshold else 'SYMMETRIC'

                # ---- Drawing (only if output requested) ----
                if out is not None:
                    nose_br = self._landmark_point(landmarks, self.NOSE_BRIDGE, width, height)
                    chin = self._landmark_point(landmarks, self.CHIN, width, height)
                    mouth_l = self._landmark_point(landmarks, self.MOUTH_LEFT, width, height)
                    mouth_r = self._landmark_point(landmarks, self.MOUTH_RIGHT, width, height)
                    brow_l = self._landmark_point(landmarks, self.BROW_LEFT, width, height)
                    brow_r = self._landmark_point(landmarks, self.BROW_RIGHT, width, height)

                    cv2.line(frame, nose_br, chin, (0, 255, 0), 2)
                    cv2.line(frame, nose_br, mouth_l, (255, 0, 0), 1)
                    cv2.line(frame, nose_br, mouth_r, (255, 0, 0), 1)
                    cv2.line(frame, nose_br, brow_l, (0, 255, 255), 1)
                    cv2.line(frame, nose_br, brow_r, (0, 255, 255), 1)

                    if total_dev > self.alert_threshold:
                        cv2.putText(frame, ">>> ASYMMETRIC EXPRESSION", (10, height - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

                    text = (f"M:{mouth_dev:.1f}% B:{brow_dev:.1f}% E:{eye_dev:.1f}% "
                            f"| Total:{total_dev:.1f}% | {status}")
                    bg_color = (0, 0, 255) if total_dev > self.alert_threshold else \
                               (0, 255, 255) if status == 'ASYMMETRIC' else (0, 255, 0)
                    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                    cv2.rectangle(frame, (5, 5), (5 + tw + 10, 5 + th + 10), bg_color, -1)
                    cv2.putText(frame, text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX,
                                0.45, (255, 255, 255), 1, cv2.LINE_AA)

            else:
                if out is not None:
                    cv2.putText(frame, "NO FACE DETECTED", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            if out is not None:
                out.write(frame)

            if verbose and results.multi_face_landmarks:
                print(f"Frame {frame_idx:04d}: M={mouth_dev:.2f}% | B={brow_dev:.2f}% | "
                      f"E={eye_dev:.2f}% | Total={total_dev:.2f}% | {status}")

            frame_data_list.append({
                'frame_num': frame_idx,
                'timestamp': timestamp,
                'mouth_asym': round(mouth_dev, 2),
                'brow_asym': round(brow_dev, 2),
                'eye_asym': round(eye_dev, 2),
                'total_asym': round(total_dev, 2),
                'status': status
            })

        cap.release()
        if out is not None:
            out.release()

        return frame_data_list


# -------------------------------------------------------------------------
#   Standalone execution (unchanged)
# -------------------------------------------------------------------------
if __name__ == "__main__":
    input_path = input("Enter the input video path: ").strip().strip('"').strip("'")
    if not os.path.exists(input_path):
        print(f"Error: File '{input_path}' not found.")
        exit(1)

    input_dir = os.path.dirname(input_path) or "."
    stem = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(input_dir, f"{stem}_asymmetry.mp4")

    print(f"Analyzing: {input_path}")
    analyzer = AsymmetryAnalyzer()
    data = analyzer.process_video(input_path, output_path, verbose=True)

    if not data:
        print("No frames processed.")
        exit(0)

    total_frames = len(data)
    calib_frames = sum(1 for d in data if d['timestamp'] <= 5.0)
    eval_data = [d for d in data if d['mouth_asym'] > 0 or d['brow_asym'] > 0 or d['eye_asym'] > 0]

    print("\n" + "=" * 50)
    print("         FINAL ASYMMETRY ANALYSIS")
    print("=" * 50)
    print(f"Total Frames Processed: {total_frames}")
    print(f"Calibration Frames: {calib_frames}")
    print("-" * 50)

    if eval_data:
        avg_mouth = np.mean([d['mouth_asym'] for d in eval_data])
        avg_brow = np.mean([d['brow_asym'] for d in eval_data])
        avg_eye = np.mean([d['eye_asym'] for d in eval_data])
        avg_total = np.mean([d['total_asym'] for d in eval_data])
        asym_pct = (sum(1 for d in eval_data if d['status'] == 'ASYMMETRIC') / len(eval_data)) * 100

        print(f"Average Mouth Deviation: {avg_mouth:.2f}%")
        print(f"Average Brow Deviation: {avg_brow:.2f}%")
        print(f"Average Eye Deviation: {avg_eye:.2f}%")
        print(f"Average Total Deviation: {avg_total:.2f}%")
        print(f"ASYMMETRIC Status: {asym_pct:.1f}% of evaluated time")
        print("-" * 50)

        print("ASYMMETRY TIMELINE (Frame Sequences):")
        status_list = [d['status'] for d in eval_data]
        if status_list:
            cur = status_list[0]
            start = eval_data[0]['frame_num']
            for i in range(1, len(status_list)):
                if status_list[i] != cur:
                    end = eval_data[i-1]['frame_num']
                    print(f"[{start:04d} to {end:04d}] : {cur} (for {end-start+1} frames)")
                    start = eval_data[i]['frame_num']
                    cur = status_list[i]
            end = eval_data[-1]['frame_num']
            print(f"[{start:04d} to {end:04d}] : {cur} (for {end-start+1} frames)")

    print("=" * 50)
    print(f"Output Video Saved: {output_path}")