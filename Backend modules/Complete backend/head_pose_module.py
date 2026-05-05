"""
head_pose_module.py

Head pose analysis for deception detection.
Uses MediaPipe Face Mesh + solvePnP to extract pitch, yaw, roll,
Z‑depth, stiffness, withdrawal, nodding, and shaking.
Now supports optional segment processing (start/end frame) and calibration.

Class:
    HeadPoseAnalyzer
        calibrate(neutral_video_path) -> set baselines
        process_video(input_path, output_path=None,
                      start_frame=None, end_frame=None, verbose=True)
"""

import cv2
import mediapipe as mp
import numpy as np
from collections import deque, defaultdict
import os


class HeadPoseAnalyzer:
    """Analyses head pose: angles, depth, stiffness, withdrawal, nodding/shaking."""

    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # MediaPipe landmark indices for head pose (6 points)
        self.IDX_NOSE = 1
        self.IDX_CHIN = 152
        self.IDX_LEYE = 33          # left eye outer corner
        self.IDX_REYE = 263         # right eye outer corner
        self.IDX_LMOUTH = 61        # left mouth corner
        self.IDX_RMOUTH = 291       # right mouth corner

        # 3D model points (average face geometry, mm)
        self.model_points = np.array([
            [0.0, 0.0, 0.0],            # nose tip
            [0.0, -65.0, -30.0],        # chin
            [-35.0, 30.0, -35.0],       # left eye outer
            [35.0, 30.0, -35.0],        # right eye outer
            [-30.0, -45.0, -40.0],      # left mouth corner
            [30.0, -45.0, -40.0]        # right mouth corner
        ], dtype=np.float32)

        # Adjustable parameters
        self.stiffness_window_sec = 1.0
        self.nodding_window_sec = 1.0
        self.nodding_zero_cross_thresh = 3       # sign changes per sec for nodding
        self.nodding_amplitude_thresh = 3.0       # degrees min range
        self.withdrawal_scale = 500.0             # % scaling for withdrawal score
        self.stiffness_scale = 50.0               # 100 - scale*std_dev => score

        # Baseline storage (set by calibrate() or auto‑calibration)
        self.baseline_depth = None
        self.baseline_pitch = None
        self.baseline_yaw = None
        self.baseline_roll = None

    # ------------------------------------------------------------------
    # Public calibration method
    # ------------------------------------------------------------------
    def calibrate(self, neutral_video_path):
        """Set baseline depth/angles from a known neutral recording.

        Scans the first 5 seconds of the video and stores averaged values.
        Call this before segment processing if you have a truthful clip.
        """
        cap = cv2.VideoCapture(neutral_video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open calibration video: {neutral_video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        calib_duration = 5.0
        max_frames = int(calib_duration * fps)

        focal = width
        cam_matrix = np.array([[focal, 0, width/2],
                               [0, focal, height/2],
                               [0, 0, 1]], dtype=np.float32)
        dist_coeffs = np.zeros((4, 1))

        depths, pitches, yaws, rolls = [], [], [], []
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
                img_pts = self._build_image_points(landmarks, width, height)
                success, rvec, tvec = cv2.solvePnP(
                    self.model_points, img_pts, cam_matrix, dist_coeffs,
                    flags=cv2.SOLVEPNP_ITERATIVE)
                if success:
                    R, _ = cv2.Rodrigues(rvec)
                    p, y, r = self._rotation_matrix_to_euler_angles(R)
                    depths.append(np.linalg.norm(tvec))
                    pitches.append(p)
                    yaws.append(y)
                    rolls.append(r)

        cap.release()
        if depths:
            self.baseline_depth = np.mean(depths)
            self.baseline_pitch = np.mean(pitches)
            self.baseline_yaw = np.mean(yaws)
            self.baseline_roll = np.mean(rolls)
            print(f"Calibration done: depth={self.baseline_depth:.0f}mm, "
                  f"pitch={self.baseline_pitch:.1f}, yaw={self.baseline_yaw:.1f}, roll={self.baseline_roll:.1f}")
            return True
        else:
            print("Calibration failed – no face detected.")
            return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _landmark_point(self, landmarks, idx, img_w, img_h):
        lm = landmarks[idx]
        return (int(lm.x * img_w), int(lm.y * img_h))

    def _build_image_points(self, landmarks, img_w, img_h):
        """Return (6,2) array of image points for solvePnP."""
        return np.array([
            self._landmark_point(landmarks, self.IDX_NOSE, img_w, img_h),
            self._landmark_point(landmarks, self.IDX_CHIN, img_w, img_h),
            self._landmark_point(landmarks, self.IDX_LEYE, img_w, img_h),
            self._landmark_point(landmarks, self.IDX_REYE, img_w, img_h),
            self._landmark_point(landmarks, self.IDX_LMOUTH, img_w, img_h),
            self._landmark_point(landmarks, self.IDX_RMOUTH, img_w, img_h)
        ], dtype=np.float32)

    def _rotation_matrix_to_euler_angles(self, R):
        """Returns (pitch, yaw, roll) in degrees from rotation matrix."""
        sy = np.sqrt(R[0, 0]**2 + R[1, 0]**2)
        singular = sy < 1e-6
        if not singular:
            pitch = np.arctan2(R[2, 1], R[2, 2])
            yaw = np.arctan2(-R[2, 0], sy)
            roll = np.arctan2(R[1, 0], R[0, 0])
        else:
            pitch = np.arctan2(-R[1, 2], R[1, 1])
            yaw = np.arctan2(-R[2, 0], sy)
            roll = 0.0
        return np.rad2deg(pitch), np.rad2deg(yaw), np.rad2deg(roll)

    # ------------------------------------------------------------------
    # Main processor
    # ------------------------------------------------------------------
    def process_video(self, input_path, output_path=None,
                      start_frame=None, end_frame=None,
                      verbose=True):
        """Analyze video, draw annotations, save output, return frame data.

        Args:
            input_path: path to input video.
            output_path: if not None, save annotated video here.
            start_frame: first frame to process (1-indexed).
            end_frame: last frame to process (inclusive).
            verbose: whether to print frame‑by‑frame output.

        Returns:
            list of dicts: per‑frame metrics within the requested segment.
        """
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {input_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Clamp segment
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

        # Camera matrix
        focal = width
        cam_matrix = np.array([[focal, 0, width/2],
                               [0, focal, height/2],
                               [0, 0, 1]], dtype=np.float32)
        dist_coeffs = np.zeros((4, 1))

        # Auto‑calibration only if baselines are None and we start from the beginning
        auto_calib = (start_frame == 1 and
                      self.baseline_depth is None)
        if auto_calib:
            calib_duration = 5.0
            calib_ended = False
            calib_depths = []
            calib_pitches = []
            calib_yaws = []
            calib_rolls = []
        else:
            calib_ended = True  # use existing baselines

        # Windows for stiffness and nodding/shaking
        stiff_window_len = max(2, int(fps * self.stiffness_window_sec))
        pitch_window = deque(maxlen=stiff_window_len)
        yaw_window = deque(maxlen=stiff_window_len)
        roll_window = deque(maxlen=stiff_window_len)

        nod_window_len = max(2, int(fps * self.nodding_window_sec))
        pitch_vel_history = deque(maxlen=nod_window_len)
        yaw_vel_history = deque(maxlen=nod_window_len)
        pitch_val_history = deque(maxlen=nod_window_len)
        yaw_val_history = deque(maxlen=nod_window_len)

        frame_data_list = []
        frame_idx = 0
        prev_pitch = prev_yaw = None

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
            pitch = 0.0
            yaw = 0.0
            roll = 0.0
            z_depth = 500.0
            stiffness_score = 0.0
            withdrawal_score = 0.0
            is_nodding = False
            is_shaking = False

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb)

            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0].landmark
                img_pts = self._build_image_points(landmarks, width, height)
                nose_img = tuple(img_pts[0].astype(int))

                success, rvec, tvec = cv2.solvePnP(
                    self.model_points, img_pts, cam_matrix, dist_coeffs,
                    flags=cv2.SOLVEPNP_ITERATIVE)

                if success:
                    R, _ = cv2.Rodrigues(rvec)
                    pitch, yaw, roll = self._rotation_matrix_to_euler_angles(R)
                    z_depth = float(np.linalg.norm(tvec))

                    # ---- Calibration ----
                    if auto_calib and not calib_ended and timestamp <= calib_duration:
                        calib_depths.append(z_depth)
                        calib_pitches.append(pitch)
                        calib_yaws.append(yaw)
                        calib_rolls.append(roll)
                        if out is not None:
                            cv2.putText(frame, "CALIBRATING...", (10, 30),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                        frame_data_list.append({
                            'frame_num': frame_idx, 'timestamp': timestamp,
                            'pitch': 0.0, 'yaw': 0.0, 'roll': 0.0,
                            'z_depth': 0.0, 'stiffness_score': 0.0,
                            'withdrawal_score': 0.0,
                            'is_nodding': False, 'is_shaking': False
                        })
                        if out is not None:
                            out.write(frame)
                        continue

                    if auto_calib and not calib_ended:
                        calib_ended = True
                        self.baseline_depth = np.mean(calib_depths) if calib_depths else z_depth
                        self.baseline_pitch = np.mean(calib_pitches) if calib_pitches else pitch
                        self.baseline_yaw = np.mean(calib_yaws) if calib_yaws else yaw
                        self.baseline_roll = np.mean(calib_rolls) if calib_rolls else roll
                        print(f"Auto‑calibration: depth={self.baseline_depth:.0f}mm, "
                              f"pitch={self.baseline_pitch:.1f}, yaw={self.baseline_yaw:.1f}, roll={self.baseline_roll:.1f}")

                    # ---- Withdrawal score ----
                    if self.baseline_depth and self.baseline_depth > 0:
                        delta = z_depth - self.baseline_depth
                        withdrawal_score = max(0.0, min(100.0,
                                                        (delta / self.baseline_depth) * self.withdrawal_scale))

                    # ---- Stiffness ----
                    pitch_window.append(pitch)
                    yaw_window.append(yaw)
                    roll_window.append(roll)
                    if len(pitch_window) >= 2:
                        std_dev = np.mean([
                            np.std(pitch_window),
                            np.std(yaw_window),
                            np.std(roll_window)
                        ])
                        stiffness_score = max(0.0, min(100.0,
                                                       100.0 - self.stiffness_scale * std_dev))

                    # ---- Nodding / Shaking ----
                    if prev_pitch is not None:
                        pitch_vel = pitch - prev_pitch
                        yaw_vel = yaw - prev_yaw
                    else:
                        pitch_vel = 0.0
                        yaw_vel = 0.0
                    prev_pitch = pitch
                    prev_yaw = yaw

                    pitch_vel_history.append(pitch_vel)
                    yaw_vel_history.append(yaw_vel)
                    pitch_val_history.append(pitch)
                    yaw_val_history.append(yaw)

                    if len(pitch_vel_history) >= 3:
                        sign_changes_pitch = sum(
                            1 for i in range(1, len(pitch_vel_history))
                            if np.sign(pitch_vel_history[i-1]) != np.sign(pitch_vel_history[i])
                            and np.sign(pitch_vel_history[i]) != 0
                        )
                        pitch_range = max(pitch_val_history) - min(pitch_val_history)
                        is_nodding = (sign_changes_pitch >= self.nodding_zero_cross_thresh
                                      and pitch_range >= self.nodding_amplitude_thresh)

                        sign_changes_yaw = sum(
                            1 for i in range(1, len(yaw_vel_history))
                            if np.sign(yaw_vel_history[i-1]) != np.sign(yaw_vel_history[i])
                            and np.sign(yaw_vel_history[i]) != 0
                        )
                        yaw_range = max(yaw_val_history) - min(yaw_val_history)
                        is_shaking = (sign_changes_yaw >= self.nodding_zero_cross_thresh
                                      and yaw_range >= self.nodding_amplitude_thresh)

                    # ---- Drawing (only if output requested) ----
                    if out is not None:
                        # 3D axis on nose
                        axis_length = 50
                        axis_3d = np.array([[axis_length, 0, 0],
                                            [0, axis_length, 0],
                                            [0, 0, axis_length]], dtype=np.float32)
                        axis_2d, _ = cv2.projectPoints(axis_3d, rvec, tvec, cam_matrix, dist_coeffs)
                        cv2.line(frame, nose_img, tuple(axis_2d[0][0].astype(int)), (0, 0, 255), 2)
                        cv2.line(frame, nose_img, tuple(axis_2d[1][0].astype(int)), (0, 255, 0), 2)
                        cv2.line(frame, nose_img, tuple(axis_2d[2][0].astype(int)), (255, 0, 0), 2)

                        # Nose direction line
                        line_len = 50
                        dx = -int(np.sin(np.deg2rad(yaw)) * line_len)
                        dy = -int(np.sin(np.deg2rad(pitch)) * line_len)
                        cv2.line(frame, nose_img,
                                 (nose_img[0] + dx, nose_img[1] + dy), (255, 0, 0), 2)

                        # Text overlay
                        if withdrawal_score > 50:
                            bg = (0, 0, 255)
                        elif stiffness_score > 70:
                            bg = (0, 255, 255)
                        elif is_nodding or is_shaking:
                            bg = (0, 165, 255)
                        else:
                            bg = (0, 255, 0)

                        text = (f"P:{pitch:.1f} Y:{yaw:.1f} R:{roll:.1f} "
                                f"Z:{z_depth:.0f}mm | Stiff:{stiffness_score:.0f}% Withdr:{withdrawal_score:.0f}% "
                                f"{'NOD' if is_nodding else ''}{' SHK' if is_shaking else ''}")
                        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
                        cv2.rectangle(frame, (5, 5), (5+tw+10, 5+th+10), bg, -1)
                        cv2.putText(frame, text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX,
                                    0.4, (255, 255, 255), 1, cv2.LINE_AA)

                else:
                    if verbose:
                        print(f"Frame {frame_idx:04d}: POSE FAILED")

            else:
                if out is not None:
                    cv2.putText(frame, "NO FACE", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                if verbose:
                    print(f"Frame {frame_idx:04d}: NO FACE")

            if out is not None:
                out.write(frame)

            # Terminal output (only if verbose and face detected)
            if verbose and results.multi_face_landmarks:
                print(f"Frame {frame_idx:04d}: P={pitch:.2f} Y={yaw:.2f} R={roll:.2f} "
                      f"Z={z_depth:.0f}mm | Stiff={stiffness_score:.0f}% Withdr={withdrawal_score:.0f}% "
                      f"Nod={'Y' if is_nodding else 'N'} Shk={'Y' if is_shaking else 'N'}")

            frame_data_list.append({
                'frame_num': frame_idx,
                'timestamp': timestamp,
                'pitch': round(pitch, 2),
                'yaw': round(yaw, 2),
                'roll': round(roll, 2),
                'z_depth': round(z_depth, 2),
                'stiffness_score': round(stiffness_score, 2),
                'withdrawal_score': round(withdrawal_score, 2),
                'is_nodding': is_nodding,
                'is_shaking': is_shaking
            })

        cap.release()
        if out is not None:
            out.release()

        return frame_data_list


# -------------------------------------------------------------------------
#   Standalone execution (unchanged – works as before)
# -------------------------------------------------------------------------
if __name__ == "__main__":
    input_path = input("Enter the input video path: ").strip().strip('"').strip("'")
    if not os.path.exists(input_path):
        print(f"Error: File '{input_path}' not found.")
        exit(1)

    input_dir = os.path.dirname(input_path) or "."
    stem = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(input_dir, f"{stem}_headpose.mp4")

    print(f"Analyzing: {input_path}")
    analyzer = HeadPoseAnalyzer()
    data = analyzer.process_video(input_path, output_path, verbose=True)

    if not data:
        print("No frames processed.")
        exit(0)

    total_frames = len(data)
    calib_frames = sum(1 for d in data if d['timestamp'] <= 5.0)
    eval_data = [d for d in data if d['pitch'] != 0 or d['yaw'] != 0 or d['roll'] != 0]

    print("\n" + "=" * 50)
    print("         FINAL HEAD POSE ANALYSIS")
    print("=" * 50)
    print(f"Total Frames Processed: {total_frames}")
    print(f"Calibration Frames: {calib_frames}")
    print("-" * 50)

    if eval_data:
        avg_pitch = np.mean([d['pitch'] for d in eval_data])
        avg_yaw = np.mean([d['yaw'] for d in eval_data])
        avg_roll = np.mean([d['roll'] for d in eval_data])
        avg_depth = np.mean([d['z_depth'] for d in eval_data])
        avg_stiff = np.mean([d['stiffness_score'] for d in eval_data])
        avg_withdr = np.mean([d['withdrawal_score'] for d in eval_data])
        nod_pct = (sum(1 for d in eval_data if d['is_nodding']) / len(eval_data)) * 100
        shake_pct = (sum(1 for d in eval_data if d['is_shaking']) / len(eval_data)) * 100

        print(f"Average Pitch: {avg_pitch:.2f} deg")
        print(f"Average Yaw: {avg_yaw:.2f} deg")
        print(f"Average Roll: {avg_roll:.2f} deg")
        print(f"Average Z-Depth: {avg_depth:.0f} mm")
        print(f"Average Stiffness: {avg_stiff:.1f}%")
        print(f"Average Withdrawal: {avg_withdr:.1f}%")
        print(f"Nodding: {nod_pct:.1f}% of time")
        print(f"Shaking: {shake_pct:.1f}% of time")
        print("-" * 50)

        # Timeline
        print("DYNAMIC MOVEMENT TIMELINE (Frame Sequences):")
        status_list = []
        for d in eval_data:
            flags = ''
            if d['is_nodding']:
                flags += 'N'
            if d['is_shaking']:
                flags += 'S'
            status_list.append(flags if flags else '-')
        if status_list:
            cur = status_list[0]
            start = eval_data[0]['frame_num']
            for i in range(1, len(status_list)):
                if status_list[i] != cur:
                    end = eval_data[i-1]['frame_num']
                    desc = 'Nodding' if cur=='N' else 'Shaking' if cur=='S' else \
                           'Nodding+Shaking' if cur=='NS' else 'None'
                    print(f"[{start:04d} to {end:04d}] : {desc} (for {end-start+1} frames)")
                    start = eval_data[i]['frame_num']
                    cur = status_list[i]
            end = eval_data[-1]['frame_num']
            desc = 'Nodding' if cur=='N' else 'Shaking' if cur=='S' else \
                   'Nodding+Shaking' if cur=='NS' else 'None'
            print(f"[{start:04d} to {end:04d}] : {desc} (for {end-start+1} frames)")

    print("=" * 50)
    print(f"Output Video Saved: {output_path}")