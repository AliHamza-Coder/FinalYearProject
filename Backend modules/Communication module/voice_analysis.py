
import os
import torch
import numpy as np
import librosa
import soundfile as sf
import parselmouth
import speech_recognition as sr
from speechbrain.inference.interfaces import foreign_class
from faster_whisper import WhisperModel
import datetime
import time

class VoiceAnalyzer:
    def __init__(self):
        print("\n" + "="*50)
        print("[INIT] Loading Voice Analysis Suite...")
        print("="*50)
        
        # 1. Load Emotion Recognition Model (SpeechBrain)
        try:
            print("[1/2] Loading Emotion Model (Wav2Vec2)...")
            self.emotion_classifier = foreign_class(
                source="speechbrain/emotion-recognition-wav2vec2-IEMOCAP", 
                pymodule_file="custom_interface.py", 
                classname="CustomEncoderWav2vec2Classifier"
            )
        except Exception as e:
            print(f"[ERROR] Emotion Model failed: {e}")
            self.emotion_classifier = None

        # 2. Load Whisper Model (for Transcription)
        try:
            print("[2/2] Loading Whisper Model (Faster-Whisper base)...")
            # Using 'base' for a balance of speed and accuracy
            self.whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
        except Exception as e:
            print(f"[ERROR] Whisper Model failed: {e}")
            self.whisper_model = None

    def record_audio(self, filename="recorded_voice.wav", duration=5):
        """Records audio from the microphone."""
        r = sr.Recognizer()
        with sr.Microphone() as source:
            print(f"\n[RECORDING] Listening for {duration} seconds...")
            r.adjust_for_ambient_noise(source, duration=1)
            audio = r.listen(source, timeout=duration, phrase_time_limit=duration)
            
            with open(filename, "wb") as f:
                f.write(audio.get_wav_data())
            
            print(f"[SUCCESS] Audio saved to {filename}")
            return filename

    def transcribe_audio(self, audio_path):
        """Transcribes audio using Faster-Whisper."""
        if not self.whisper_model or not os.path.exists(audio_path):
            return "Transcription Unavailable"
        
        segments, info = self.whisper_model.transcribe(audio_path, beam_size=5)
        text = " ".join([segment.text for segment in segments])
        return text.strip()

    def analyze_audio(self, audio_path):
        """Combines Emotion, Transcription, and Acoustic analysis with temporal segments."""
        if not os.path.exists(audio_path):
            return None

        # 1. Load Audio for Segmenting
        try:
            signal, fs = librosa.load(audio_path, sr=16000)
            duration = len(signal) / fs
        except Exception as e:
            print(f"[ERROR] Loading audio: {e}")
            return None

        results = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "file": os.path.basename(audio_path),
            "transcription": "",
            "segments": [], # List of (emotion, score)
            "distribution": {},
            "timeline": [],
            "pitch_mean": 0.0,
            "jitter": 0.0,
            "shimmer": 0.0,
            "stress_level": "Normal",
            "vibe_check": ""
        }

        # 2. Transcription
        results["transcription"] = self.transcribe_audio(audio_path)

        # 3. Segmented Emotion Detection (the "Frame-by-Frame" part)
        segment_len = 2.0  # seconds per "frame"
        num_segments = int(np.ceil(duration / segment_len))
        
        print("\n" + "-"*40)
        print(f"Processing started: {audio_path}")
        print(f"Total Duration: {duration:.2f}s | Segments (Frames): {num_segments}")
        print("-"*40)

        for i in range(num_segments):
            start = int(i * segment_len * fs)
            end = int(min((i + 1) * segment_len * fs, len(signal)))
            chunk = signal[start:end]
            
            # Save temporary chunk for model
            tmp_chunk_path = f"tmp_chunk_{i}.wav"
            sf.write(tmp_chunk_path, chunk, fs)
            
            emotion = "Unknown"
            score = 0.0
            
            if self.emotion_classifier:
                try:
                    _, prob, _, text_lab = self.emotion_classifier.classify_file(tmp_chunk_path)
                    emotion = text_lab[0]
                    score = prob[0].item()
                except Exception as e:
                    pass
            
            results["segments"].append((emotion, score))
            print(f"Frame {i+1:04d}: {emotion.capitalize()} ({score:.1%})")
            
            # Cleanup
            if os.path.exists(tmp_chunk_path):
                os.remove(tmp_chunk_path)

        # 4. Process Distribution & Timeline
        for emo, _ in results["segments"]:
            results["distribution"][emo] = results["distribution"].get(emo, 0) + 1
        
        # Timeline grouping
        if results["segments"]:
            current_emo = results["segments"][0][0]
            start_idx = 1
            for idx, (emo, _) in enumerate(results["segments"], 1):
                if emo != current_emo:
                    results["timeline"].append((start_idx, idx-1, current_emo))
                    current_emo = emo
                    start_idx = idx
            results["timeline"].append((start_idx, len(results["segments"]), current_emo))

        # 5. Acoustic Features (Overall File for accuracy)
        try:
            sound = parselmouth.Sound(audio_path)
            
            # Pitch Dynamics
            pitch = sound.to_pitch()
            pitch_values = pitch.selected_array['frequency']
            pitch_values = pitch_values[pitch_values != 0]
            if len(pitch_values) > 0: 
                results["pitch_mean"] = np.mean(pitch_values)
                results["pitch_min"] = np.min(pitch_values)
                results["pitch_max"] = np.max(pitch_values)
                results["pitch_sd"] = np.std(pitch_values)
            
            # Harmonic-to-Noise Ratio (HNR - Clarity)
            hnr = sound.to_harmonicity()
            hnr_values = hnr.values
            hnr_values = hnr_values[hnr_values != -200] # Praat uses -200 for undefined
            if len(hnr_values) > 0:
                results["hnr"] = np.mean(hnr_values)

            # Voice Profiling (Jitter/Shimmer)
            point_process = parselmouth.praat.call(sound, "To PointProcess (periodic, cc)", 75, 500)
            results["jitter"] = parselmouth.praat.call(point_process, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3) * 100
            results["shimmer"] = parselmouth.praat.call([sound, point_process], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6) * 100

            # Spectral Centroid (Vocal Brightness via librosa)
            spectral_centroids = librosa.feature.spectral_centroid(y=signal, sr=fs)[0]
            results["brightness"] = np.mean(spectral_centroids)

            # Stress Heuristic
            if results["jitter"] > 1.0 or results["shimmer"] > 3.0:
                results["stress_level"] = "High (Physiological Stress detected)"
            elif results["jitter"] > 0.5 or results["shimmer"] > 1.5:
                results["stress_level"] = "Elevated"

            # Dominant Emotion for Vibe Check
            dominant_emo = max(results["distribution"], key=results["distribution"].get) if results["distribution"] else "neu"
            if dominant_emo == "ang" or results["stress_level"] == "High":
                results["vibe_check"] = "CRITICAL: High Tension Detected"
            elif dominant_emo == "hap":
                results["vibe_check"] = "POSITIVE: Speaker sounds energetic/happy"
            elif dominant_emo == "sad":
                results["vibe_check"] = "CONCERN: Speaker sounds low-energy/sad"
            else:
                results["vibe_check"] = "NEUTRAL: Speaker sounds stable"

        except Exception as e:
            print(f"[ERROR] Acoustic analysis: {e}")

        # 6. Fluency & Hesitation Analysis
        try:
            # Filler Words (from transcription)
            fillers = ["um", "uh", "ah", "er", "hm", "hmm", "like", "you know"]
            words = results["transcription"].lower().split()
            found_fillers = [w for w in words if w.strip(".,!?") in fillers]
            results["filler_count"] = len(found_fillers)
            
            # Speaking Rate (Words Per Minute)
            if duration > 0:
                results["wpm"] = (len(words) / duration) * 60
            else:
                results["wpm"] = 0

            # Silence Ratio (Non-silent vs Silence)
            # frame_length and hop_length for 16k mono
            non_silent_intervals = librosa.effects.split(signal, top_db=30)
            non_silent_duration = sum([(end - start) for start, end in non_silent_intervals]) / fs
            results["silence_ratio"] = (duration - non_silent_duration) / duration if duration > 0 else 0
            
            # Hesitation Score (Heuristic: 0-100)
            # High fillers, low WPM, and high silence increase the score
            h_score = (results["filler_count"] * 5) + (results["silence_ratio"] * 100)
            if results["wpm"] < 100 and results["wpm"] > 0: h_score += 20
            results["hesitation_score"] = min(h_score, 100)

            if results["hesitation_score"] > 60:
                results["fluency_status"] = "High Hesitation (Potential Uncertainty)"
            elif results["hesitation_score"] > 30:
                results["fluency_status"] = "Moderate"
            else:
                results["fluency_status"] = "Fluent"

        except Exception as e:
            print(f"[ERROR] Fluency analysis: {e}")

        return results

    def display_report(self, results):
        """Displays a beautiful segmented report in the terminal."""
        if not results: return

        print("\n" + "="*40)
        print("         FINAL VOICE ANALYSIS")
        print("="*40)
        print(f"Total Segments Processed: {len(results['segments'])}")
        print(f"Transcription: \"{results['transcription']}\"")
        print("-"*40)
        
        print("EMOTION DISTRIBUTION:")
        total = len(results["segments"])
        for emo, count in results["distribution"].items():
            pct = (count / total) * 100
            print(f"- {emo.capitalize():<10}: {pct:>5.1f}% ({count} segments)")
        
        print("-"*40)
        print("EMOTION TIMELINE (Segment Sequences):")
        for start, end, emo in results["timeline"]:
            duration = (end - start + 1)
            print(f"[{start:04d} to {end:04d}] : {emo.capitalize()} (for {duration} segments)")
        
        print("-"*40)
        print("🗣️  [FLUENCY & HESITATION]")
        print(f"  - Speaking Rate  : {results.get('wpm', 0):.1f} WPM")
        print(f"  - Filler Words   : {results.get('filler_count', 0)} detected")
        print(f"  - Silence Ratio  : {results.get('silence_ratio', 0):.1%}")
        print(f"  - Hesitation Lvl : {results.get('fluency_status', 'N/A')} ({results.get('hesitation_score', 0):.0f}/100)")

        print("-"*40)
        print("🔍 [FORENSIC VOICE PROFILE]")
        print(f"  - Pitch Dynamics:")
        print(f"    • Mean: {results.get('pitch_mean', 0):.2f} Hz")
        print(f"    • Range: {results.get('pitch_min', 0):.2f} - {results.get('pitch_max', 0):.2f} Hz")
        print(f"    • Variation (SD): {results.get('pitch_sd', 0):.2f} Hz")
        print(f"  - Vocal Clarity (HNR): {results.get('hnr', 0):.2f} dB")
        print(f"  - Spectral Brightness: {results.get('brightness', 0):.2f} Hz")
        print(f"  - Micro-Tremors:")
        print(f"    • Jitter: {results.get('jitter', 0):.3f}%")
        print(f"    • Shimmer: {results.get('shimmer', 0):.3f}%")
        print(f"  - Stress Index: {results['stress_level']}")
        
        print("\n" + "="*40)
        print(f"VIBE CHECK: {results['vibe_check']}")
        print("="*40 + "\n")

if __name__ == "__main__":
    analyzer = VoiceAnalyzer()
    
    while True:
        print("\n--- DEceptron Voice Analysis Menu ---")
        print("1. Analyze from File Path")
        print("2. Live Listening (Mic)")
        print("3. Exit")
        choice = input("Select an option (1-3): ")

        if choice == "1":
            path = input("Enter voice file path: ").strip().strip('"')
            if os.path.exists(path):
                print(f"\n[PROCESS] Analyzing {path}...")
                report = analyzer.analyze_audio(path)
                analyzer.display_report(report)
            else:
                print("[ERROR] File not found.")
        
        elif choice == "2":
            try:
                recorded_file = analyzer.record_audio(duration=5)
                print(f"\n[PROCESS] Analyzing live recording...")
                report = analyzer.analyze_audio(recorded_file)
                analyzer.display_report(report)
            except Exception as e:
                print(f"[ERROR] Recording failed: {e}")
                print("Make sure PyAudio and a microphone are available.")
        
        elif choice == "3":
            print("Exiting Voice Suite. Goodbye!")
            break
        else:
            print("Invalid selection.")
