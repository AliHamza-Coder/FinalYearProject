import os
import time
import json
import logging
import threading
import queue
import io
import speech_recognition as sr
from groq import Groq
from dotenv import load_dotenv
from faster_whisper import WhisperModel

# Reduce faster-whisper logging noise
logging.basicConfig()
logging.getLogger("faster_whisper").setLevel(logging.ERROR)

# Load environment variables
load_dotenv()

class DeceptronContextFilter:
    def __init__(self):
        print("[INIT] Loading Deceptron Context Filter...")
        
        # Concurrency setup
        self.audio_queue = queue.Queue()
        self.is_running = False
        
        # Audio setup
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Configure thresholds
        self.recognizer.energy_threshold = 300
        self.recognizer.pause_threshold = 1.0  # Slightly reduced for snappier response
        self.recognizer.dynamic_energy_threshold = True

        # 1. Initialize Groq (LLaMA 3 70B)
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("[ERROR] GROQ_API_KEY not found in .env file.")
            exit(1)
        
        try:
            self.client = Groq(api_key=api_key)
        except Exception as e:
            print(f"[ERROR] Failed to initialize Groq client: {e}")
            exit(1)
        
        # 2. Initialize Faster-Whisper (Local Transcription)
        print("[INIT] Loading Faster-Whisper (base model)...")
        try:
            # Using 'base' model for speed/accuracy balance. compute_type="int8" is good for CPU.
            self.whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
        except Exception as e:
            print(f"[ERROR] Failed to load Whisper model: {e}")
            exit(1)

    def listen_worker(self):
        """Producer thread: continuously listens and puts audio into the queue."""
        print(f"[LISTENER] Background thread started.")
        
        with self.microphone as source:
            print("[LISTENER] Adjusting for ambient noise...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1.0)
            print("[LISTENER] Ready. Speak now.")
            
            while self.is_running:
                try:
                    # Listen strictly for the phrase
                    audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=10)
                    self.audio_queue.put(audio)
                    print(f"[LISTENER] Audio captured. Queue size: {self.audio_queue.qsize()}")
                except sr.WaitTimeoutError:
                    continue # Just keep listening
                except Exception as e:
                    print(f"[LISTENER ERROR] {e}")
                    time.sleep(1) # Prevent tight loop on error

    def process_file(self, file_path):
        """Processes a single audio file."""
        if not os.path.exists(file_path):
            print(f"[ERROR] File not found: {file_path}")
            return

        print(f"\n[PROCESSING FILE] {file_path}")
        try:
            # 1. Voice Analysis (before transcription to have data ready)
            print("[ANALYZING VOICE FEATURES...]")
            voice_data = self.voice_analyzer.analyze_audio(file_path)
            
            # 2. Transcribe
            segments, info = self.whisper_model.transcribe(
                file_path, 
                beam_size=5, 
                initial_prompt="Kese ho yar? Haan main theek hun. Kya haal hai. This is a Roman Urdu conversation."
            )
            
            transcript = " ".join([segment.text for segment in segments]).strip()
            
            if transcript:
                print(f"\nTranscript: \"{transcript}\"")
                # 3. Classify with Voice Context
                analysis = self.classify_intent(transcript, voice_data)
                
                if analysis:
                    self._print_decision(analysis, voice_data)
            else:
                print("[INFO] No speech detected in file.")
                
        except Exception as e:
            print(f"[FILE ERROR] {e}")

    def process_worker(self):
        """Consumer thread: processes audio from the queue."""
        print(f"[PROCESSOR] Background thread started.")
        
        while self.is_running:
            try:
                # Block until audio is available, with a timeout
                try:
                    audio = self.audio_queue.get(timeout=1)
                except queue.Empty:
                    continue

                # 1. Save to temp file for Voice Analysis (SpeechBrain/Parselmouth need file)
                temp_filename = "temp_live.wav"
                try:
                    with open(temp_filename, "wb") as f:
                        f.write(audio.get_wav_data())
                    
                    # Analyze Voice
                    voice_data = self.voice_analyzer.analyze_audio(temp_filename)
                except Exception as e:
                    print(f"[VOICE PROC ERROR] {e}")
                    voice_data = None
                finally:
                    # We keep the file for a split second for analysis, then logic continues
                    # Note: faster-whisper can read from memory, but we needed file for voice tools
                    pass 

                # 2. Transcribe (using in-memory or file)
                transcript = self.transcribe(audio)
                
                # Cleanup temp file
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)
                
                if transcript:
                    print(f"\nTranscript: \"{transcript}\"")
                    # 3. Classify with Voice Context
                    analysis = self.classify_intent(transcript, voice_data)
                    
                    if analysis:
                        self._print_decision(analysis, voice_data)
                
                self.audio_queue.task_done()
                
            except Exception as e:
                print(f"[PROCESSOR ERROR] {e}")

    def transcribe(self, audio):
        """Converts audio to text using Local Faster-Whisper (In-Memory)."""
        if audio is None:
            return None
            
        try:
            # Convert AudioData to in-memory WAV file (BytesIO)
            wav_data = io.BytesIO(audio.get_wav_data())
            wav_data.name = "audio.wav" 
            
            # Transcribe
            segments, info = self.whisper_model.transcribe(
                wav_data, 
                beam_size=5, 
                initial_prompt="Kese ho yar? Haan main theek hun. Kya haal hai. This is a Roman Urdu conversation."
            )
            
            transcript = " ".join([segment.text for segment in segments]).strip()
            return transcript
            
        except Exception as e:
            print(f"[TRANSCRIPTION ERROR] {e}")
            return None

    def classify_intent(self, text, voice_data=None):
        """Classifies the transcript using Groq (LLaMA 3 70B) with retry logic and Voice Context."""
        if not text:
            return None
            
        # Construct Voice Context String
        voice_context = ""
        if voice_data:
            voice_context = (
                f"\n[VOICE ANALYSIS DATA]\n"
                f"- Detected Emotion: {voice_data.get('emotion', 'Unknown')}\n"
                f"- Stress/Tremor Level: {voice_data.get('stress_level', 'Unknown')}\n"
                f"- Jitter (Tremor): {voice_data.get('jitter', 0):.2f}%\n"
                f"- Shimmer (Stress): {voice_data.get('shimmer', 0):.2f}%\n"
                f"INSTRUCTION: Compare the TEXT content with the VOICE EMOTION. "
                f"If text is positive but voice is Fear/Sad/Angry, or Jitter is High, mark as suspicious/RELEVANT.\n"
            )

        system_prompt = (
            "You are the 'Context-Aware Filter' for a Lie Detection System named Deceptron, tailored for Pakistan.\n"
            "Your task is to analyze a sentence (which might be in English, Roman Urdu, or Pure Urdu) "
            "and decide if it's worth analyzing for deception.\n\n"
            "PROCESS:\n"
            "1. TRANSLATE: Convert text into clear **Roman Urdu** (e.g., 'Main wahan nahi tha').\n"
            "2. CLASSIFY: specific factual claims, denials, or answers are RELEVANT.\n"
            "   - Greetings/Small talk (PHATIC) are usually IGNORED.\n"
            "   - **CRITICAL EXCEPTION**: If there is an **Emotion Mismatch** (e.g., Saying 'I'm fine' with FEAR/TREMORS), it is **RELEVANT** for deception analysis.\n\n"
            f"{voice_context}\n"
            "Categories:\n"
            "1. PHATIC: Greetings, pleasantries, filler words (unless voice shows high stress/fear).\n"
            "2. RELEVANT: Factual claims, specific denials, emotional outbursts, or **Text-Tone Mismatches**.\n\n"
            "You MUST respond ONLY in JSON format with exactly these keys:\n"
            "- translated_text: \"<The text translated to Roman Urdu>\"\n"
            "- intent: \"PHATIC\" or \"RELEVANT\"\n"
            "- is_analyzable: true or false\n"
            "- reasoning: \"<short explanation in Roman Urdu, mentioning voice mismatch if found>\"\n"
        )

        retries = 2
        for attempt in range(retries + 1):
            try:
                completion = self.client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Analyze this sentence: \"{text}\""}
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                
                response_data = json.loads(completion.choices[0].message.content)
                return response_data
            
            except Exception as e:
                print(f"[CLASSIFICATION ERROR] Attempt {attempt+1}/{retries+1}: {e}")
                if attempt < retries:
                    time.sleep(1) # Backoff before retry
                else:
                    return None

    def _print_decision(self, analysis, voice_data=None):
        """Helper to pretty-print the decision."""
        translated_text = analysis.get('translated_text', 'N/A')
        intent = analysis.get('intent', 'UNKNOWN')
        is_analyzable = analysis.get('is_analyzable', False)
        reasoning = analysis.get('reasoning', 'N/A')
        
        symbol = "✅" if is_analyzable else "⏸️"
        
        print(f"   Tarjuma (Roman): \"{translated_text}\"")
        if voice_data:
            emo = voice_data.get('emotion', 'N/A')
            stress = voice_data.get('stress_level', 'N/A')
            print(f"   Voice Emotion: {emo} | Stress: {stress}")
            
        print(f"{symbol} Intent: {intent}")
        print(f"   Wajah: {reasoning}")
        print(f"   Faisla: {'ANALYZE' if is_analyzable else 'IGNORE'}")
        print("-" * 40)

    def run(self):
        print("\n=== DECEPTRON CONTEXT FILTER ACTIVE ===")
        print("Models: Faster-Whisper (Local) + LLaMA 3.3 70B (Cloud)")
        print("Mode:   Continuous Asynchronous Listening")
        print("Lang:   Output in Roman Urdu")
        
        self.is_running = True
        
        # Create threads
        listener = threading.Thread(target=self.listen_worker, daemon=True)
        processor = threading.Thread(target=self.process_worker, daemon=True)
        
        # Start threads
        listener.start()
        processor.start()
        
        try:
            # Keep main thread alive to allow Daemon threads to run
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n[STOPPING] Shutting down...")
            self.is_running = False
            # Allow threads a moment to finish current task if needed, but daemons will die on exit
            time.sleep(0.5)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Deceptron Context Filter")
    parser.add_argument("--file", type=str, help="Path to audio file to process")
    args = parser.parse_args()
    
    filter_mod = DeceptronContextFilter()
    
    if args.file:
        filter_mod.process_file(args.file)
    else:
        filter_mod.run()
