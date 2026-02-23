import cv2
import torch
from hsemotion.facial_emotions import HSEmotionRecognizer

class EmotionDetector:
    def __init__(self, model_name='enet_b0_8_best_vgaf', device=None):
        """
        Initialize the HSEmotion Recognizer.
        model_name: Supported values: enet_b0_8_best_vgaf, enet_b0_8_best_afew, enet_b2_8, enet_b0_8_va_mtl, enet_b2_7
        device: 'cpu' or 'cuda'. If None, it auto-detects.
        """
        if device is None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        print(f"Loading Emotion Detection Model ({model_name}) on {device}...")
        # Fix for weights_only error in newer torch versions
        try:
            self.fer = HSEmotionRecognizer(model_name=model_name, device=device)
        except Exception as e:
            if "WeightsUnpickler" in str(e) or "unpickle" in str(e):
                print("Patching torch.load for compatibility...")
                original_load = torch.load
                torch.load = lambda *args, **kwargs: original_load(*args, **{**kwargs, 'weights_only': False})
                self.fer = HSEmotionRecognizer(model_name=model_name, device=device)
                torch.load = original_load
            else:
                raise e
        print("Model Loaded successfully.")

    def detect_emotion(self, face_image):
        """
        Predicts emotion for a given face crop.
        Returns: emotion_label, confidence_score
        """
        if face_image is None or face_image.size == 0:
            return None, 0.0
        
        # HSEmotion expects a BGR image (OpenCV default)
        emotion, scores = self.fer.predict_emotions(face_image, logits=False)
        return emotion, scores

if __name__ == "__main__":
    # Test block
    detector = EmotionDetector()
    print("Test: Detector initialized.")
