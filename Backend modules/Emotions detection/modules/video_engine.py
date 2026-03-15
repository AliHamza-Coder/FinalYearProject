import cv2
import mediapipe as mp
import os
from modules.emotion_engine import initialize_emotion_detector, detect_emotion

def process_video(input_path):
    """
    Reads a video file, detects emotions frame-by-frame, 
    displays stats in terminal, and saves the output.
    """
    # 1. Setup Directories
    output_dir = "results"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    filename = os.path.basename(input_path)
    output_path = os.path.join(output_dir, f"output_{filename}")

    # 2. Initialize Detectors
    mp_face_detection = mp.solutions.face_detection
    face_detection = mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)
    detector = initialize_emotion_detector()

    # 3. Open Video
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print(f"Error: Could not open video file {input_path}")
        return

    # Get video properties for Output
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS)
    fourcc = cv2.VideoWriter_fourcc(*'XVID') # Codec for .avi (change to 'mp4v' for .mp4)
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    print(f"Processing started: {input_path}")
    print(f"Output will be saved to: {output_path}")
    print("-" * 40)

    frame_count = 0
    emotion_stats = {} # To track total counts for percentages
    emotion_sequences = [] # To track durations (start, end, emotion)
    
    current_seq_emotion = None
    current_seq_start = 1

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            # End of video: Close the last sequence
            if current_seq_emotion:
                emotion_sequences.append({
                    "emotion": current_seq_emotion,
                    "start": current_seq_start,
                    "end": frame_count
                })
            break

        frame_count += 1
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_detection.process(rgb_frame)

        frame_emotion = "None" # Default if no face
        max_score_val = 0.0

        if results.detections:
            # We track the first/main face for the summary statistics
            detection = results.detections[0] 
            bboxC = detection.location_data.relative_bounding_box
            ih, iw, _ = frame.shape
            x, y, w, h = int(bboxC.xmin * iw), int(bboxC.ymin * ih), int(bboxC.width * iw), int(bboxC.height * ih)

            y1, y2 = max(0, y), min(ih, y + h)
            x1, x2 = max(0, x), min(iw, x + w)
            face_crop = frame[y1:y2, x1:x2]
            
            if face_crop.size > 0:
                emotion, scores = detect_emotion(detector, face_crop)
                frame_emotion = emotion
                max_score_val = max(scores) * 100
                
                # Update Stats
                emotion_stats[emotion] = emotion_stats.get(emotion, 0) + 1
                
                # Terminal Log
                print(f"Frame {frame_count:04d}: {emotion} ({max_score_val:.1f}%)")

                # Draw on all detected faces (not just the first one)
                for det in results.detections:
                    b = det.location_data.relative_bounding_box
                    dx, dy, dw, dh = int(b.xmin * iw), int(b.ymin * ih), int(b.width * iw), int(b.height * ih)
                    cv2.rectangle(frame, (dx, dy), (dx + dw, dy + dh), (0, 255, 0), 2)
                    # We only label the first face with emotion for simplicity on video
                    if det == detection:
                        label = f"{emotion} {max_score_val:.1f}%"
                        cv2.putText(frame, label, (dx, dy - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Handle Sequences for Durations
        if frame_emotion != current_seq_emotion:
            if current_seq_emotion is not None:
                emotion_sequences.append({
                    "emotion": current_seq_emotion,
                    "start": current_seq_start,
                    "end": frame_count - 1
                })
            current_seq_emotion = frame_emotion
            current_seq_start = frame_count

        # Write frame to output video
        out.write(frame)

        # Preview
        cv2.imshow("Processing Video...", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            # Close sequence if interrupted
            emotion_sequences.append({
                "emotion": current_seq_emotion,
                "start": current_seq_start,
                "end": frame_count
            })
            print("Processing interrupted by user.")
            break

    # Cleanup
    cap.release()
    out.release()
    cv2.destroyAllWindows()

    # --- FINAL SUMMARY ---
    print("\n" + "="*40)
    print("         FINAL EMOTION ANALYSIS         ")
    print("="*40)
    print(f"Total Frames Processed: {frame_count}")
    print("-" * 40)
    
    # 1. Percentages
    print("EMOTION DISTRIBUTION:")
    # Only count frames where a face was actually detected
    total_face_frames = sum(emotion_stats.values())
    if total_face_frames > 0:
        for emo, count in sorted(emotion_stats.items(), key=lambda item: item[1], reverse=True):
            percentage = (count / total_face_frames) * 100
            print(f"- {emo:10}: {percentage:5.1f}% ({count} frames)")
    else:
        print("No faces detected in video.")

    print("-" * 40)
    
    # 2. Durations (Sequences)
    print("EMOTION TIMELINE (Frame Sequences):")
    for seq in emotion_sequences:
        if seq['emotion'] != "None":
            duration = seq['end'] - seq['start'] + 1
            print(f"[{seq['start']:04d} to {seq['end']:04d}] : {seq['emotion']} (for {duration} frames)")

    print("="*40)
    print(f"Output Video Saved: {output_path}\n")

if __name__ == "__main__":
    # Test path
    test_video = "test.mp4" 
    if os.path.exists(test_video):
        process_video(test_video)
    else:
        print("Please provide a valid video file path.")
