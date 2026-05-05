"""
eye_gaze_module.py

Eye gaze analysis for deception detection.
Tracks iris positions (MediaPipe FaceMesh, refine_landmarks=True),
classifies gaze direction, measures blinks, eye openness (EAR),
fixation, and gaze stability. Produces an annotated video + terminal report.

Now also supports segment‑based processing (start/end frame) for pipeline use.

Dependencies:
    mediapipe==0.10.11
    opencv-python==4.8.1.78
    numpy==1.24.3
"""

import cv2
import mediapipe as mp
import numpy as np
from collections import deque, defaultdict
import os


class EyeGazeAnalyzer:
    """Analyzes gaze, blinks, and stability from a video file."""

    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,          # iris landmarks 468-477
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # Adjustable hyperparameters
        self.blink_threshold = 0.2          # EAR below this = closed
        self.fixation_window = 30           # frames for fixation score
        self.stability_window = 15          # frames for iris stability
        self.stability_scale = 10.0         # std→score conversion factor

        # MediaPipe eye contour indices
        self.left_eye_contour = [
            33, 246, 161, 160, 159, 158, 157, 173, 133,
            155, 154, 153, 145, 144, 163, 7
        ]
        self.right_eye_contour = [
            362, 398, 384, 385, 386, 387, 388, 466, 263,
            249, 390, 373, 374, 380, 381, 382
        ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _compute_ear(self, landmarks, img_w, img_h):
        """Eye Aspect Ratio (averaged left + right)."""
        def point(idx):
            return np.array([landmarks[idx].x * img_w,
                             landmarks[idx].y * img_h])

        # Left eye
        p33, p133 = point(33), point(133)
        p159, p145 = point(159), point(145)
        p158, p153 = point(158), point(153)
        ear_left = (np.linalg.norm(p159 - p145) + np.linalg.norm(p158 - p153)) / \
                   (2.0 * np.linalg.norm(p33 - p133) + 1e-6)

        # Right eye
        p362, p263 = point(362), point(263)
        p386, p374 = point(386), point(374)
        p385, p373 = point(385), point(373)
        ear_right = (np.linalg.norm(p386 - p374) + np.linalg.norm(p385 - p373)) / \
                    (2.0 * np.linalg.norm(p362 - p263) + 1e-6)

        return ear_left, ear_right

    def _get_iris_center(self, landmarks, indices, img_w, img_h):
        """Average of iris landmark pixels."""
        pts = np.array([[landmarks[i].x * img_w,
                         landmarks[i].y * img_h] for i in indices])
        return np.mean(pts, axis=0)

    # ------------------------------------------------------------------
    # Main processor
    # ------------------------------------------------------------------
    def process_video(self, input_path, output_path=None,
                      start_frame=None, end_frame=None,
                      verbose=True):
        """Analyze video, draw annotations, save output, return frame data.

        Args:
            input_path (str): Path to the input video.
            output_path (str or None): If not None, annotated video is saved here.
            start_frame (int or None): First frame to include (1-indexed).
            end_frame (int or None): Last frame to include (inclusive).
            verbose (bool): Whether to print frame‑by‑frame progress.

        Returns:
            list of dicts: Per‑frame metrics (only for frames within segment).
        """
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {input_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Clamp segment boundaries
        if start_frame is None:
            start_frame = 1
        if end_frame is None:
            end_frame = total_frames
        start_frame = max(1, start_frame)
        end_frame = min(total_frames, end_frame)

        # If output requested, create VideoWriter
        out = None
        if output_path is not None:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        # State tracked PER SEGMENT (reset when start_frame is given)
        blink_count = 0
        blink_state = False
        direction_history = deque(maxlen=self.fixation_window)
        iris_pos_history = deque(maxlen=self.stability_window)

        frame_data_list = []
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1

            # Skip frames before the segment
            if frame_idx < start_frame:
                continue
            # Stop after the segment
            if frame_idx > end_frame:
                break

            timestamp = frame_idx / fps

            # Defaults (no face)
            gaze_direction = 'CENTER'
            ear_avg = 1.0
            blink_activity = False
            fixation_score = 100.0
            gaze_stability = 100.0

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb)

            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0].landmark
                if len(landmarks) >= 478:
                    # --- Eye openness (EAR) & blink ---
                    ear_left, ear_right = self._compute_ear(landmarks, width, height)
                    ear_avg = (ear_left + ear_right) / 2.0
                    blink_activity = ear_avg < self.blink_threshold

                    # State machine: only increment on transition closed -> open
                    if blink_activity and not blink_state:
                        blink_state = True
                    elif not blink_activity and blink_state:
                        blink_state = False
                        blink_count += 1

                    # --- Gaze direction ---
                    left_iris = self._get_iris_center(
                        landmarks, [468,469,470,471,472], width, height)
                    right_iris = self._get_iris_center(
                        landmarks, [473,474,475,476,477], width, height)

                    left_eye_centre = np.mean([
                        [landmarks[33].x * width, landmarks[33].y * height],
                        [landmarks[133].x * width, landmarks[133].y * height]
                    ], axis=0)
                    right_eye_centre = np.mean([
                        [landmarks[362].x * width, landmarks[362].y * height],
                        [landmarks[263].x * width, landmarks[263].y * height]
                    ], axis=0)

                    left_w = np.linalg.norm([landmarks[133].x*width - landmarks[33].x*width,
                                             landmarks[133].y*height - landmarks[33].y*height])
                    right_w = np.linalg.norm([landmarks[263].x*width - landmarks[362].x*width,
                                              landmarks[263].y*height - landmarks[362].y*height])
                    left_h = np.linalg.norm([landmarks[159].x*width - landmarks[145].x*width,
                                             landmarks[159].y*height - landmarks[145].y*height])
                    right_h = np.linalg.norm([landmarks[386].x*width - landmarks[374].x*width,
                                              landmarks[386].y*height - landmarks[374].y*height])

                    left_horiz = (left_iris[0] - left_eye_centre[0]) / (left_w/2 + 1e-6)
                    left_vert = (left_iris[1] - left_eye_centre[1]) / (left_h/2 + 1e-6)
                    right_horiz = (right_iris[0] - right_eye_centre[0]) / (right_w/2 + 1e-6)
                    right_vert = (right_iris[1] - right_eye_centre[1]) / (right_h/2 + 1e-6)

                    avg_h = (left_horiz + right_horiz) / 2.0
                    avg_v = (left_vert + right_vert) / 2.0

                    h_thresh, v_thresh = 0.3, 0.3
                    if abs(avg_h) > abs(avg_v):
                        if avg_h < -h_thresh:
                            gaze_direction = 'LEFT'
                        elif avg_h > h_thresh:
                            gaze_direction = 'RIGHT'
                        else:
                            gaze_direction = 'CENTER'
                    else:
                        if avg_v < -v_thresh:
                            gaze_direction = 'UP'
                        elif avg_v > v_thresh:
                            gaze_direction = 'DOWN'
                        else:
                            gaze_direction = 'CENTER'

                    # --- Fixation score ---
                    direction_history.append(gaze_direction)
                    match = sum(1 for d in direction_history if d == gaze_direction)
                    fixation_score = (match / len(direction_history)) * 100.0

                    # --- Stability score ---
                    avg_iris_pos = (left_iris + right_iris) / 2.0
                    iris_pos_history.append(avg_iris_pos)
                    if len(iris_pos_history) >= 2:
                        positions = np.array(iris_pos_history)
                        mean_pos = np.mean(positions, axis=0)
                        dists = np.linalg.norm(positions - mean_pos, axis=1)
                        gaze_stability = max(0.0, 100.0 - np.std(dists) * self.stability_scale)
                    else:
                        gaze_stability = 100.0

                    # --- Draw overlays (only if output requested) ---
                    if out is not None:
                        left_pts = np.array([[landmarks[i].x*width, landmarks[i].y*height]
                                             for i in self.left_eye_contour], np.int32)
                        right_pts = np.array([[landmarks[i].x*width, landmarks[i].y*height]
                                              for i in self.right_eye_contour], np.int32)
                        cv2.polylines(frame, [left_pts], True, (0,255,0), 1)
                        cv2.polylines(frame, [right_pts], True, (0,255,0), 1)
                        cv2.circle(frame, tuple(left_iris.astype(int)), 3, (0,255,255), -1)
                        cv2.circle(frame, tuple(right_iris.astype(int)), 3, (0,255,255), -1)
                        cv2.line(frame, tuple(left_iris.astype(int)),
                                 tuple(right_iris.astype(int)), (255,255,0), 1)

            # --- Text overlay (only if output requested) ---
            if out is not None:
                blink_rate = (blink_count / (timestamp / 60.0)) if timestamp > 0 else 0.0
                dir_char = gaze_direction[0] if gaze_direction != 'CENTER' else 'C'
                text = (f"Dir:{dir_char} | Blinks:{blink_count} ({blink_rate:.1f}/min) | "
                        f"EAR:{ear_avg:.2f} | Fix:{fixation_score:.0f}% | Stab:{gaze_stability:.0f}%")

                alert = blink_rate > 20.0 or fixation_score < 40.0 or gaze_stability < 40.0
                bg_color = (0, 0, 255) if alert else (0, 255, 0)

                (tw, th), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
                cv2.rectangle(frame, (5, 5), (5 + tw + 5, 5 + th + 5), bg_color, -1)
                cv2.putText(frame, text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX,
                            0.4, (255, 255, 255), 1, cv2.LINE_AA)

            if out is not None:
                out.write(frame)

            # Save frame data (for segment or whole)
            frame_data_list.append({
                'frame_num': frame_idx,
                'timestamp': timestamp,
                'blink_activity': blink_activity,
                'focus_area': gaze_direction,
                'fixation_score': round(fixation_score, 2),
                'gaze_stability': round(gaze_stability, 2)
            })

            if verbose and frame_idx % 10 == 0:
                print(f"Processing frame {frame_idx}/{end_frame}")

        cap.release()
        if out is not None:
            out.release()
        # ✅ Do NOT close the face_mesh here – it will be reused by later calls.

        return frame_data_list


# -------------------------------------------------------------------------
# Standalone execution with detailed terminal output
# -------------------------------------------------------------------------
if __name__ == "__main__":
    # Prompt for input video path
    input_path = input("Enter the input video path: ").strip().strip('"').strip("'")
    if not os.path.exists(input_path):
        print(f"Error: File '{input_path}' not found.")
        exit(1)

    input_dir = os.path.dirname(input_path) or "."
    stem = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(input_dir, f"{stem}_gaze.mp4")

    print(f"Analyzing: {input_path}")
    analyzer = EyeGazeAnalyzer()
    data = analyzer.process_video(input_path, output_path, verbose=True)

    # ---- Frame‑by‑frame terminal output ----
    print("\nFrame-by-frame analysis:")
    for entry in data:
        f_num = entry['frame_num']
        direction = entry['focus_area']
        fix = entry['fixation_score']
        stab = entry['gaze_stability']
        blink = 'Yes' if entry['blink_activity'] else 'No'
        print(f"Frame {f_num:04d}: Direction={direction:6s} | "
              f"Fix={fix:.1f}% | Stab={stab:.1f}% | Blink={blink}")

    # ---- Final Analysis Report ----
    print("\n" + "=" * 50)
    print("         FINAL EYE GAZE ANALYSIS")
    print("=" * 50)
    print(f"Total Frames Processed: {len(data)}")
    print("-" * 50)

    # Direction distribution
    dir_counts = defaultdict(int)
    for entry in data:
        dir_counts[entry['focus_area']] += 1
    print("GAZE DIRECTION DISTRIBUTION:")
    for d in ['LEFT', 'RIGHT', 'UP', 'DOWN', 'CENTER']:
        if d in dir_counts:
            pct = (dir_counts[d] / len(data)) * 100
            print(f"- {d:7s} : {pct:5.1f}% ({dir_counts[d]} frames)")
    print("-" * 50)

    # Blink stats
    blink_events = 0
    prev_open = True
    for entry in data:
        if entry['blink_activity'] and prev_open:
            blink_events += 1
            prev_open = False
        elif not entry['blink_activity'] and not prev_open:
            prev_open = True
    duration_min = data[-1]['timestamp'] / 60.0 if data else 0
    blink_rate = blink_events / duration_min if duration_min > 0 else 0.0

    print(f"Total Blink Events: {blink_events}")
    print(f"Average Blink Rate: {blink_rate:.1f} blinks/min")
    print("-" * 50)

    # Fixation & stability averages
    avg_fix = np.mean([e['fixation_score'] for e in data])
    avg_stab = np.mean([e['gaze_stability'] for e in data])
    print(f"Average Fixation Score: {avg_fix:.1f}%")
    print(f"Average Gaze Stability: {avg_stab:.1f}%")
    print("-" * 50)

    # Gaze timeline
    print("GAZE TIMELINE (Frame Sequences):")
    if data:
        seq_start = data[0]['frame_num']
        seq_dir = data[0]['focus_area']
        for i in range(1, len(data)):
            if data[i]['focus_area'] != seq_dir:
                end_frame = data[i-1]['frame_num']
                print(f"[{seq_start:04d} to {end_frame:04d}] : {seq_dir} "
                      f"(for {end_frame - seq_start + 1} frames)")
                seq_start = data[i]['frame_num']
                seq_dir = data[i]['focus_area']
        last_frame = data[-1]['frame_num']
        print(f"[{seq_start:04d} to {last_frame:04d}] : {seq_dir} "
              f"(for {last_frame - seq_start + 1} frames)")

    print("=" * 50)
    print(f"Output Video Saved: {output_path}")