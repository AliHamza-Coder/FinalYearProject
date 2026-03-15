import cv2
import mediapipe as mp
import os
import torch
from hsemotion.facial_emotions import HSEmotionRecognizer

def get_emotion_detector(model_name='enet_b0_8_best_vgaf', device=None):
    """
    Initializes and returns the HSEmotion Recognizer.
    """
    if device is None:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    # Compatibility patch for newer torch versions
    try:
        fer = HSEmotionRecognizer(model_name=model_name, device=device)
    except Exception as e:
        if "WeightsUnpickler" in str(e) or "unpickle" in str(e):
            original_load = torch.load
            torch.load = lambda *args, **kwargs: original_load(*args, **{**kwargs, 'weights_only': False})
            fer = HSEmotionRecognizer(model_name=model_name, device=device)
            torch.load = original_load
        else:
            raise e
    return fer

def process_video_file(input_path, output_folder="results"):
    """
    Core function to process a video file.
    Returns a dictionary containing:
    - status: success/error
    - output_path: path to the processed video
    - stats: dictionary of emotion percentages
    - timeline: list of emotion sequences [start, end, emotion]
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    output_path = os.path.join(output_folder, f"processed_{os.path.basename(input_path)}")

    # Initialize MediaPipe
    mp_face_detection = mp.solutions.face_detection
    face_detection = mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)
    
    # Initialize Engine
    fer = get_emotion_detector()

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        return {"status": "error", "message": f"Could not open {input_path}"}

    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v') # Using mp4v for better compatibility
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_count = 0
    emotion_counts = {}
    timeline = []
    
    current_emotion = None
    start_frame = 1

    while True:
        ret, frame = cap.read()
        if not ret:
            # End of video: finalize sequence
            if current_emotion:
                timeline.append({"emotion": current_emotion, "start": start_frame, "end": frame_count})
            break

        frame_count += 1
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = face_detection.process(rgb)

        detected_emotion = "None"
        confidence = 0.0

        if res.detections:
            # Analyze primary face
            det = res.detections[0]
            bboxC = det.location_data.relative_bounding_box
            ih, iw, _ = frame.shape
            x, y, w, h = int(bboxC.xmin * iw), int(bboxC.ymin * ih), int(bboxC.width * iw), int(bboxC.height * ih)

            face = frame[max(0, y):min(ih, y + h), max(0, x):min(iw, x + w)]
            if face.size > 0:
                emo, scores = fer.predict_emotions(face, logits=False)
                detected_emotion = emo
                confidence = max(scores) * 100
                
                emotion_counts[emo] = emotion_counts.get(emo, 0) + 1

                # Draw Overlay
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, f"{emo} {confidence:.1f}%", (x, y - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Handle Timeline logic
        if detected_emotion != current_emotion:
            if current_emotion is not None:
                timeline.append({"emotion": current_emotion, "start": start_frame, "end": frame_count - 1})
            current_emotion = detected_emotion
            start_frame = frame_count

        out.write(frame)

    cap.release()
    out.release()

    # Calculate percentages
    total_face_frames = sum(emotion_counts.values())
    stats = {}
    if total_face_frames > 0:
        for emo, count in emotion_counts.items():
            stats[emo] = round((count / total_face_frames) * 100, 2)

    return {
        "status": "success",
        "output_path": output_path,
        "total_frames": frame_count,
        "stats": stats,
        "timeline": [t for t in timeline if t['emotion'] != "None"]
    }
