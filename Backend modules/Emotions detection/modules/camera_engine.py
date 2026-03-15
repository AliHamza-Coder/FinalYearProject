import cv2
import mediapipe as mp
from modules.emotion_engine import initialize_emotion_detector, detect_emotion

def run_camera_analysis():
    """
    Main loop for camera-based emotion detection.
    """
    # Initialize MediaPipe Face Detection
    mp_face_detection = mp.solutions.face_detection
    face_detection = mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)

    # Initialize Emotion Detector Functionally
    detector = initialize_emotion_detector()

    print("Camera starting...")
    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        print("Error: Could not open camera.")
        return

    print("Press 'q' to quit.")

    while True:
        ret, frame = camera.read()
        if not ret:
            print("Error: Could not read frame.")
            break

        # 🔁 Horizontal flip (mirror effect)
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Detect faces
        results = face_detection.process(rgb_frame)

        if results.detections:
            for detection in results.detections:
                # Get bounding box
                bboxC = detection.location_data.relative_bounding_box
                ih, iw, _ = frame.shape
                x, y, w, h = int(bboxC.xmin * iw), int(bboxC.ymin * ih), int(bboxC.width * iw), int(bboxC.height * ih)

                # Draw bounding box
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                # Extract face crop for emotion detection
                # Ensure coordinates are within frame boundaries
                y1, y2 = max(0, y), min(ih, y + h)
                x1, x2 = max(0, x), min(iw, x + w)
                face_crop = frame[y1:y2, x1:x2]
                
                if face_crop.size > 0:
                    emotion, scores = detect_emotion(detector, face_crop)
                    
                    # Display results
                    label = f"{emotion}"
                    cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        cv2.imshow("Deceptron - Emotion Detection", frame)

        # 1ms wait, 'q' to exit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Cleanup
    camera.release()
    cv2.destroyAllWindows()
