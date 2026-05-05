"""
hand_face_touch_module.py

Self‑adaptor detection for deception analysis.
Uses MediaPipe Face Mesh + Hands to detect when a hand touches the face.
Measures touch region, confidence, duration, and hand count.

Now supports optional segment processing (start/end frame) and 
optional annotated output video.

Class:
    HandFaceTouchAnalyzer
        process_video(input_path, output_path=None,
                      start_frame=None, end_frame=None, verbose=True)
"""

import cv2
import mediapipe as mp
import numpy as np
from collections import defaultdict
import os


class HandFaceTouchAnalyzer:
    """Detects hand‑to‑face touches (self‑adaptors).

    Combines MediaPipe Face Mesh (for face regions) and Hands (for fingertips).
    No calibration required – detection is absolute.
    """

    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils

        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # Region definitions (indices for face mesh)
        self.NOSE_TIP = 1
        self.MOUTH_CENTER = (13, 14)          # average of inner lips
        self.FOREHEAD = 10
        self.LEFT_EYE_CENTER = (33, 133)      # outer & inner corners
        self.RIGHT_EYE_CENTER = (263, 362)
        self.LEFT_CHEEK = 117
        self.RIGHT_CHEEK = 346

        # Finger tip indices
        self.FINGER_TIPS = [8, 12]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _landmark_point(self, landmarks, idx, img_w, img_h):
        if isinstance(idx, tuple):
            pts = np.array([(landmarks[i].x * img_w, landmarks[i].y * img_h) for i in idx])
            return np.mean(pts, axis=0)
        lm = landmarks[idx]
        return np.array([lm.x * img_w, lm.y * img_h])

    def _distance(self, pt1, pt2):
        return np.linalg.norm(np.array(pt1) - np.array(pt2))

    def _region_radius(self, face_w, face_h, region_name):
        """Return a fixed fraction of face size as touch radius."""
        baselen = min(face_w, face_h)
        radii = {
            'NOSE': 0.08 * baselen,
            'MOUTH': 0.08 * baselen,
            'EYE': 0.07 * baselen,
            'FOREHEAD': 0.1 * baselen,
            'CHEEK': 0.1 * baselen
        }
        return radii.get(region_name, 0.05 * baselen)

    # ------------------------------------------------------------------
    # Main processor
    # ------------------------------------------------------------------
    def process_video(self, input_path, output_path=None,
                      start_frame=None, end_frame=None,
                      verbose=True):
        """Process video, optionally draw and save annotations, return frame data.

        Args:
            input_path: Path to the input video.
            output_path: If not None, save annotated video here.
            start_frame: First frame to process (1‑indexed). Default = 1.
            end_frame: Last frame to process (inclusive). Default = total frames.
            verbose: Print frame‑by‑frame terminal output.

        Returns:
            list of dicts: Per‑frame metrics within the requested segment.
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

        # Output video writer (only if output_path provided)
        out = None
        if output_path is not None:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        frame_data_list = []
        frame_idx = 0
        touch_duration = 0          # resets at segment start (appropriate for per‑segment analysis)

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1

            # Skip frames before segment
            if frame_idx < start_frame:
                continue
            # Stop after segment
            if frame_idx > end_frame:
                break

            timestamp = frame_idx / fps

            # Defaults
            touch_region = 'NONE'
            touch_confidence = 0.0
            hand_count = 0
            status = 'NO_TOUCH'

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_results = self.face_mesh.process(rgb)
            hand_results = self.hands.process(rgb)

            # ----- Face landmarks & regions -----
            face_regions = {}
            face_box = None
            if face_results.multi_face_landmarks:
                landmarks = face_results.multi_face_landmarks[0].landmark

                xs = [lm.x * width for lm in landmarks]
                ys = [lm.y * height for lm in landmarks]
                x_min, x_max = min(xs), max(xs)
                y_min, y_max = min(ys), max(ys)
                face_w = x_max - x_min
                face_h = y_max - y_min
                face_box = (int(x_min), int(y_min), int(face_w), int(face_h))

                regions_def = {
                    'NOSE': (self._landmark_point(landmarks, self.NOSE_TIP, width, height),
                             self._region_radius(face_w, face_h, 'NOSE')),
                    'MOUTH': (self._landmark_point(landmarks, self.MOUTH_CENTER, width, height),
                              self._region_radius(face_w, face_h, 'MOUTH')),
                    'FOREHEAD': (self._landmark_point(landmarks, self.FOREHEAD, width, height),
                                 self._region_radius(face_w, face_h, 'FOREHEAD')),
                    'LEFT_EYE': (self._landmark_point(landmarks, self.LEFT_EYE_CENTER, width, height),
                                 self._region_radius(face_w, face_h, 'EYE')),
                    'RIGHT_EYE': (self._landmark_point(landmarks, self.RIGHT_EYE_CENTER, width, height),
                                  self._region_radius(face_w, face_h, 'EYE')),
                    'LEFT_CHEEK': (self._landmark_point(landmarks, self.LEFT_CHEEK, width, height),
                                   self._region_radius(face_w, face_h, 'CHEEK')),
                    'RIGHT_CHEEK': (self._landmark_point(landmarks, self.RIGHT_CHEEK, width, height),
                                    self._region_radius(face_w, face_h, 'CHEEK'))
                }
                face_regions['EYE'] = [regions_def['LEFT_EYE'], regions_def['RIGHT_EYE']]
                face_regions['CHEEK'] = [regions_def['LEFT_CHEEK'], regions_def['RIGHT_CHEEK']]
                for name in ['NOSE', 'MOUTH', 'FOREHEAD']:
                    face_regions[name] = [regions_def[name]]

            # ----- Hand detection & touch check -----
            if hand_results.multi_hand_landmarks:
                hand_count = len(hand_results.multi_hand_landmarks)
                # Draw hand skeletons (red) only if output requested
                if out is not None:
                    for hand_lms in hand_results.multi_hand_landmarks:
                        self.mp_draw.draw_landmarks(
                            frame, hand_lms, self.mp_hands.HAND_CONNECTIONS,
                            self.mp_draw.DrawingSpec(color=(0, 0, 255), thickness=2, circle_radius=2),
                            self.mp_draw.DrawingSpec(color=(0, 0, 255), thickness=2))
                        for tip_idx in self.FINGER_TIPS:
                            tip = hand_lms.landmark[tip_idx]
                            px = int(tip.x * width)
                            py = int(tip.y * height)
                            cv2.circle(frame, (px, py), 6, (0, 255, 255), -1)

                # Touch detection
                if face_results.multi_face_landmarks:
                    for hand_lms in hand_results.multi_hand_landmarks:
                        for tip_idx in self.FINGER_TIPS:
                            tip = hand_lms.landmark[tip_idx]
                            tip_pt = np.array([tip.x * width, tip.y * height])
                            for region_category, region_list in face_regions.items():
                                for center, radius in region_list:
                                    dist = self._distance(tip_pt, center)
                                    if dist <= radius:
                                        conf = (1.0 - dist / radius) * 100.0
                                        if conf > touch_confidence:
                                            touch_confidence = conf
                                            # Use unified name
                                            if region_category in ('EYE', 'CHEEK'):
                                                touch_region = region_category
                                            else:
                                                touch_region = region_category
                                        break
                                if touch_confidence > 0:
                                    break
                            if touch_confidence > 0:
                                break
                        if touch_confidence > 0:
                            break

                # Update duration
                if touch_confidence > 0:
                    touch_duration += 1
                    status = 'TOUCHING'
                else:
                    touch_duration = 0
                    status = 'NO_TOUCH'
            else:
                # No hands → reset duration if previously touching
                if status == 'TOUCHING':
                    touch_duration = 0
                    status = 'NO_TOUCH'

            # ----- Drawing (only if output requested) -----
            if out is not None:
                if face_box:
                    cv2.rectangle(frame, (face_box[0], face_box[1]),
                                  (face_box[0]+face_box[2], face_box[1]+face_box[3]),
                                  (0, 255, 0), 2)
                if face_results.multi_face_landmarks:
                    for region_category, region_list in face_regions.items():
                        for center, radius in region_list:
                            cv2.circle(frame, (int(center[0]), int(center[1])),
                                       int(radius), (255, 0, 0), 1)

                if status == 'TOUCHING':
                    text = f"REGION: {touch_region} | CONF: {touch_confidence:.0f}% | DUR: {touch_duration} | HANDS: {hand_count}"
                    bg_color = (0, 0, 255)
                    cv2.putText(frame, f">>> SELF-ADAPTOR: {touch_region}",
                                (10, height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                                (0, 0, 255), 2)
                else:
                    text = f"REGION: NONE | DUR: 0 | HANDS: {hand_count}"
                    bg_color = (0, 255, 0)

                (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                cv2.rectangle(frame, (5, 5), (5 + tw + 10, 5 + th + 10), bg_color, -1)
                cv2.putText(frame, text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX,
                            0.45, (255, 255, 255), 1, cv2.LINE_AA)

                out.write(frame)

            # ----- Terminal output (only if verbose) -----
            if verbose:
                print(f"Frame {frame_idx:04d}: Region={touch_region:8s} | "
                      f"Conf={touch_confidence:.1f}% | Dur={touch_duration} | "
                      f"Hands={hand_count} | {status}")

            # Save frame data
            frame_data_list.append({
                'frame_num': frame_idx,
                'timestamp': timestamp,
                'touch_region': touch_region,
                'confidence': round(touch_confidence, 2),
                'duration': touch_duration,
                'hand_count': hand_count,
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
    output_path = os.path.join(input_dir, f"{stem}_handface.mp4")

    print(f"Analyzing: {input_path}")
    analyzer = HandFaceTouchAnalyzer()
    data = analyzer.process_video(input_path, output_path, verbose=True)

    if not data:
        print("No frames processed.")
        exit(0)

    total_frames = len(data)
    touches = [d for d in data if d['status'] == 'TOUCHING']
    touch_pct = (len(touches) / total_frames) * 100 if total_frames > 0 else 0

    print("\n" + "=" * 50)
    print("         FINAL SELF‑ADAPTOR ANALYSIS")
    print("=" * 50)
    print(f"Total Frames Processed: {total_frames}")
    print(f"Touching Frames: {len(touches)} ({touch_pct:.1f}%)")
    print("-" * 50)

    if touches:
        region_counts = defaultdict(int)
        for d in touches:
            region_counts[d['touch_region']] += 1
        print("TOUCH REGIONS:")
        for reg in ['NOSE', 'MOUTH', 'EYE', 'FOREHEAD', 'CHEEK']:
            cnt = region_counts.get(reg, 0)
            if cnt > 0:
                print(f"  {reg:8s}: {cnt} frames ({cnt/len(touches)*100:.1f}% of touches)")
        print(f"\nAverage Touch Confidence: {np.mean([d['confidence'] for d in touches]):.1f}%")
        print(f"Longest Continuous Touch: {max(d['duration'] for d in touches)} frames")
        print("-" * 50)

        print("TOUCH TIMELINE (Frame Sequences):")
        in_touch = False
        start = None
        cur_reg = None
        segments = []
        for d in data:
            if d['status'] == 'TOUCHING':
                if not in_touch:
                    start = d['frame_num']
                    cur_reg = d['touch_region']
                    in_touch = True
            else:
                if in_touch:
                    segments.append((start, d['frame_num']-1, cur_reg))
                    in_touch = False
                    cur_reg = None
        if in_touch:
            segments.append((start, data[-1]['frame_num'], cur_reg))
        for s, e, reg in segments:
            print(f"[{s:04d} to {e:04d}] : {reg} (for {e-s+1} frames)")
    else:
        print("No self‑adaptor touches detected.")

    print("=" * 50)
    print(f"Output Video Saved: {output_path}")