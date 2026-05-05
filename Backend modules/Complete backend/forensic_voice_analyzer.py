"""
forensic_voice_analyzer.py

Deceptron FYP – Forensic Voice Stress & Deception Analyzer.
Acoustic markers (Praat) + Whisper transcription (full‑file & segment).
All audio analysis now uses soundfile + pure numpy (no librosa imports
that trigger the speechbrain/k2 bug).

Class:
    ForensicVoiceAnalyzer
        calibrate(neutral_wav_path)
        analyze(wav_path) -> dict
        analyze_segment(wav_path, start, end) -> dict
        generate_report(result, output_path)
"""

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import soundfile as sf
import parselmouth

try:
    import whisper
except ImportError:
    raise ImportError(
        "OpenAI Whisper is required. Install with: pip install openai-whisper"
    )

# We do NOT import librosa anywhere that could trigger the lazy loading.
# Only use librosa.resample if needed – that function is safe.
import librosa as _librosa_resample_only


class ForensicVoiceAnalyzer:
    """Forensic voice analyzer – acoustic features + transcription."""

    def __init__(self, whisper_model_size: str = "base"):
        print(f"Loading Whisper model '{whisper_model_size}' …")
        self.whisper_model = whisper.load_model(whisper_model_size)
        self.sample_rate = 16000
        self.baseline = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def calibrate(self, neutral_wav_path: str) -> Dict[str, float]:
        features = self._analyze_core_from_file(neutral_wav_path)
        if features is None:
            raise RuntimeError("Calibration failed – could not extract features.")
        self.baseline = {
            'f0_std_hz': features['fundamental_frequency']['f0_std_hz'],
            'jitter_local_percent': features['micro_tremors']['jitter_local_percent']
        }
        return self.baseline

    def analyze(self, wav_path: str) -> Optional[Dict[str, Any]]:
        y, sr = self._load_audio(wav_path)
        if y is None:
            return None
        duration = len(y) / sr

        core = self._analyze_core_from_array(y, sr, duration)
        if core is None:
            return None

        deception = self._score_deception(core)
        transcript_original, transcript_english = self._full_transcription(y)

        result = {
            "session_id": str(uuid.uuid4())[:8],
            "timestamp": datetime.now().isoformat(),
            "audio_duration_sec": core['audio_duration_sec'],
            "fundamental_frequency": core['fundamental_frequency'],
            "micro_tremors": core['micro_tremors'],
            "spectral_clarity": core['spectral_clarity'],
            "temporal_dynamics": core['temporal_dynamics'],
            "energy_profile": core['energy_profile'],
            "deception_analysis": deception,
            "transcription_original": transcript_original,
            "transcription_english": transcript_english
        }

        self._print_mini_report(result, wav_path)
        return result

    def analyze_segment(self, wav_path: str, start: float, end: float,
                        suppress_terminal: bool = False) -> Optional[Dict[str, Any]]:
        y_full, sr = self._load_audio(wav_path)
        if y_full is None:
            return None
        full_dur = len(y_full) / sr

        if start < 0 or end > full_dur or start >= end:
            print(f"Segment [{start}-{end}] out of range (duration {full_dur}s).")
            return None

        sample_start = int(start * sr)
        sample_end = int(end * sr)
        y_seg = y_full[sample_start:sample_end].astype(np.float64)
        seg_duration = end - start

        core = self._analyze_core_from_array(y_seg, sr, seg_duration)
        if core is None:
            return None

        deception = self._score_deception(core)

        original_text = ""
        english_text = ""
        try:
            audio_whisper = y_seg.astype(np.float32)
            res_orig = self.whisper_model.transcribe(audio_whisper, task="transcribe")
            original_text = res_orig['text'].strip()
            res_en = self.whisper_model.transcribe(audio_whisper, task="translate")
            english_text = res_en['text'].strip()
        except Exception as e:
            print(f"Segment transcription failed: {e}")

        result = {
            "segment_id": f"SEG_{start:.2f}-{end:.2f}",
            "segment_start_sec": start,
            "segment_end_sec": end,
            "audio_duration_sec": seg_duration,
            "fundamental_frequency": core['fundamental_frequency'],
            "micro_tremors": core['micro_tremors'],
            "spectral_clarity": core['spectral_clarity'],
            "temporal_dynamics": core['temporal_dynamics'],
            "energy_profile": core['energy_profile'],
            "deception_analysis": deception,
            "transcription_original": original_text,
            "transcription_english": english_text
        }

        if not suppress_terminal:
            self._print_segment_report(result)

        return result

    def generate_report(self, result: Dict[str, Any], output_path: str):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Report saved to {output_path}")

    # ------------------------------------------------------------------
    # Audio loading (soundfile, no librosa.load)
    # ------------------------------------------------------------------
    def _load_audio(self, path: str):
        try:
            y, orig_sr = sf.read(path)
            if y.ndim > 1:
                y = np.mean(y, axis=1)           # mono
            if orig_sr != self.sample_rate:
                y = _librosa_resample_only.resample(y, orig_sr=orig_sr, target_sr=self.sample_rate)
            y = y.astype(np.float64)
            return y, self.sample_rate
        except Exception as e:
            print(f"[Voice] Error loading audio file: {e}")
            return None, None

    # ------------------------------------------------------------------
    # Core extraction
    # ------------------------------------------------------------------
    def _analyze_core_from_file(self, wav_path: str) -> Optional[Dict[str, Any]]:
        y, sr = self._load_audio(wav_path)
        if y is None:
            return None
        duration = len(y) / sr
        return self._analyze_core_from_array(y, sr, duration)

    def _analyze_core_from_array(self, y: np.ndarray, sr: int,
                                 duration: float) -> Optional[Dict[str, Any]]:
        snd = self._to_parselmouth_sound_from_array(y, sr)
        if snd is None:
            return None
        f0_stats = self._extract_f0(snd)
        tremor_stats = self._extract_tremors(snd)
        hnr_stats = self._extract_hnr(snd)
        temporal_stats = self._extract_temporal(y, sr, duration)
        energy_stats = self._extract_energy(y, sr)

        # Compute spectral centroid with pure numpy
        cent_mean, cent_std = self._compute_spectral_centroid(y, sr)

        return {
            "audio_duration_sec": round(duration, 3),
            "fundamental_frequency": f0_stats,
            "micro_tremors": tremor_stats,
            "spectral_clarity": {
                "hnr_db": hnr_stats,
                "spectral_centroid_mean": round(cent_mean, 1),
                "spectral_centroid_std": round(cent_std, 1),
                "status": ("Clear" if hnr_stats > 20 else ("Degraded" if hnr_stats > 10 else "Noisy"))
            },
            "temporal_dynamics": temporal_stats,
            "energy_profile": energy_stats
        }

    def _to_parselmouth_sound_from_array(self, y, sr):
        try:
            return parselmouth.Sound(y, sampling_frequency=sr)
        except Exception as e:
            print(f"Cannot create Parselmouth Sound from array: {e}")
            return None

    # ------------------------------------------------------------------
    # Spectral centroid (pure numpy)
    # ------------------------------------------------------------------
    def _compute_spectral_centroid(self, y, sr):
        """Compute mean and std of spectral centroid using numpy FFT."""
        try:
            frame_length = 2048
            hop_length = 512
            frames = [y[i:i+frame_length] for i in range(0, len(y)-frame_length, hop_length)]
            centroids = []
            for frame in frames:
                spectrum = np.abs(np.fft.rfft(frame))
                freqs = np.fft.rfftfreq(frame_length, 1/sr)
                if np.sum(spectrum) > 0:
                    cent = np.sum(freqs * spectrum) / np.sum(spectrum)
                else:
                    cent = 0
                centroids.append(cent)
            if centroids:
                return float(np.mean(centroids)), float(np.std(centroids))
        except:
            pass
        return 0.0, 0.0

    # ------------------------------------------------------------------
    # Temporal dynamics – pure numpy
    # ------------------------------------------------------------------
    def _extract_temporal(self, y: np.ndarray, sr: int, duration: float) -> Dict[str, Any]:
        # 1. Compute RMS energy manually
        frame_length = 1024
        hop_length = 256
        num_frames = 1 + (len(y) - frame_length) // hop_length
        rms = np.zeros(num_frames)
        for i in range(num_frames):
            segment = y[i*hop_length : i*hop_length + frame_length]
            rms[i] = np.sqrt(np.mean(segment**2))

        # 2. Syllable rate via RMS peaks
        rms_mean = np.mean(rms)
        peak_frames = (rms > rms_mean * 1.2).astype(int)
        syllable_count = np.sum(np.diff(peak_frames) == 1)
        sps = syllable_count / duration if duration > 0 else 0
        wpm = sps * 60 / 2

        # 3. Silence detection via RMS threshold
        silence_thresh = 0.01
        silent_mask = rms < silence_thresh
        silent_regions = []
        in_silence = False
        start_idx = 0
        for i, s in enumerate(silent_mask):
            if s and not in_silence:
                start_idx = i
                in_silence = True
            elif not s and in_silence:
                silent_regions.append((start_idx, i))
                in_silence = False
        if in_silence:
            silent_regions.append((start_idx, len(silent_mask)))

        frame_time = hop_length / sr
        pauses = []
        prev_end = 0.0
        for s, e in silent_regions:
            start_sec = s * frame_time
            end_sec = e * frame_time
            gap = start_sec - prev_end
            if gap > 0.15:
                pauses.append(gap)
            prev_end = end_sec
        gap = duration - prev_end
        if gap > 0.15:
            pauses.append(gap)

        total_silent = sum(pauses)
        pause_count = len(pauses)
        longest_pause = max(pauses) if pauses else 0.0
        pause_ratio = (total_silent / duration * 100) if duration > 0 else 0.0

        if pause_ratio < 15:
            status = "Fluent"
        elif pause_ratio < 30:
            status = "Hesitant"
        else:
            status = "Blocked"

        return {
            "speaking_rate_wpm": round(wpm, 1),
            "speaking_rate_syllables_per_sec": round(sps, 2),
            "pause_ratio_percent": round(pause_ratio, 1),
            "pause_count": pause_count,
            "longest_pause_sec": round(longest_pause, 3),
            "status": status
        }

    # ------------------------------------------------------------------
    # Energy profile – pure numpy
    # ------------------------------------------------------------------
    def _extract_energy(self, y, sr):
        # RMS energy
        frame_length = 1024
        hop_length = 256
        num_frames = 1 + (len(y) - frame_length) // hop_length
        rms = np.zeros(num_frames)
        for i in range(num_frames):
            segment = y[i*hop_length : i*hop_length + frame_length]
            rms[i] = np.sqrt(np.mean(segment**2))

        rms_mean = float(np.mean(rms))
        rms_std = float(np.std(rms))
        half = len(rms) // 2
        if half > 0:
            first = np.mean(rms[:half])
            second = np.mean(rms[half:])
            if second > first * 1.05:
                trend = "Rising"
            elif second < first * 0.95:
                trend = "Falling"
            else:
                trend = "Stable"
        else:
            trend = "Stable"

        # Zero crossing rate
        zcr = np.sum(np.abs(np.diff(np.sign(y)))) / (2 * len(y))

        return {"rms_mean": round(rms_mean, 5), "rms_std": round(rms_std, 5),
                "rms_trend": trend, "zcr_mean": round(zcr, 5)}

    # ------------------------------------------------------------------
    # All other extractors (Praat) – unchanged
    # ------------------------------------------------------------------
    def _extract_f0(self, snd):
        pitch = snd.to_pitch(time_step=0.01, pitch_floor=75, pitch_ceiling=600)
        pitches = pitch.selected_array['frequency']
        voiced = pitches[pitches > 0]
        if len(voiced) < 10:
            return {"f0_mean_hz": 0.0, "f0_std_hz": 0.0, "f0_min_hz": 0.0,
                    "f0_max_hz": 0.0, "f0_range_hz": 0.0, "stability_status": "Flat"}
        f0_mean = float(np.mean(voiced))
        f0_std = float(np.std(voiced))
        f0_min = float(np.min(voiced))
        f0_max = float(np.max(voiced))
        f0_range = f0_max - f0_min
        if f0_range < 50:
            stability = "Flat"
        elif f0_std < 20:
            stability = "Stable"
        else:
            stability = "Unstable"
        return {"f0_mean_hz": round(f0_mean, 1), "f0_std_hz": round(f0_std, 1),
                "f0_min_hz": round(f0_min, 1), "f0_max_hz": round(f0_max, 1),
                "f0_range_hz": round(f0_range, 1), "stability_status": stability}

    def _extract_tremors(self, snd):
        try:
            pitch = snd.to_pitch(time_step=0.01, pitch_floor=75, pitch_ceiling=600)
            pp = parselmouth.praat.call(snd, "To PointProcess (cc)", pitch)
            jitter_local = parselmouth.praat.call(snd, "Get jitter (local)", 0.0, 0.0, 0.0001, 0.02, 1.3) * 100
            jitter_ppq5 = parselmouth.praat.call(snd, "Get jitter (ppq5)", 0.0, 0.0, 0.0001, 0.02, 1.3) * 100
            shimmer_local = parselmouth.praat.call([snd, pp], "Get shimmer (local)", 0.0, 0.0, 0.0001, 0.02, 1.3, 1.6) * 100
            shimmer_apq11 = parselmouth.praat.call([snd, pp], "Get shimmer (apq11)", 0.0, 0.0, 0.0001, 0.02, 1.3, 1.6) * 100
        except:
            jitter_local = jitter_ppq5 = shimmer_local = shimmer_apq11 = 0.0
        stab = 100 - (jitter_local * 20 + shimmer_local * 10)
        stability_score = max(0.0, min(100.0, stab))
        if jitter_local < 0.5 and shimmer_local < 3:
            status = "Optimal"
        elif jitter_local < 1.5:
            status = "Elevated"
        else:
            status = "Critical"
        return {"jitter_local_percent": round(jitter_local, 2),
                "jitter_ppq5_percent": round(jitter_ppq5, 2),
                "shimmer_local_percent": round(shimmer_local, 2),
                "shimmer_apq11_percent": round(shimmer_apq11, 2),
                "stability_score": round(stability_score, 1), "status": status}

    def _extract_hnr(self, snd):
        try:
            harmonicity = snd.to_harmonicity(time_step=0.01, minimum_pitch=75)
            hn = harmonicity.values
            hn = hn[hn > -200]
            if len(hn) == 0:
                return 0.0
            return float(10 * np.log10(np.mean(hn) + 1e-10))
        except:
            return 0.0

    def _score_deception(self, core):
        f0 = core['fundamental_frequency']
        trem = core['micro_tremors']
        spec = core['spectral_clarity']
        tmp = core['temporal_dynamics']
        pitch_std = f0['f0_std_hz']
        jitter = trem['jitter_local_percent']
        shimmer = trem['shimmer_local_percent']
        hnr = spec['hnr_db']
        pause_ratio = tmp['pause_ratio_percent']
        pause_count = tmp['pause_count']
        longest_pause = tmp['longest_pause_sec']
        wpm = tmp['speaking_rate_wpm']
        sps = tmp['speaking_rate_syllables_per_sec']
        f0_range = f0['f0_range_hz']
        controlled = 0
        if jitter > 1.0: controlled += 30
        if pitch_std < 20: controlled += 40
        if shimmer > 4: controlled += 20
        if hnr < 15: controlled += 10
        controlled = min(controlled, 100)
        vocal = 0
        if shimmer > 5: vocal += 40
        if hnr < 10: vocal += 40
        if jitter > 2: vocal += 20
        vocal = min(vocal, 100)
        hesitation = pause_ratio * 2
        duration_min = core['audio_duration_sec'] / 60
        if duration_min > 0 and (pause_count / duration_min) > 10:
            hesitation += 20
        if longest_pause > 2.0:
            hesitation += 20
        hesitation = min(hesitation, 100)
        rate_anomaly = 0
        if wpm < 80 or wpm > 180: rate_anomaly += 50
        if sps < 2 or sps > 5: rate_anomaly += 50
        rate_anomaly = min(rate_anomaly, 100)
        flat = 0
        if f0_range < 50: flat += 60
        if pitch_std < 15: flat += 40
        flat = min(flat, 100)
        base = (controlled * 0.30 + vocal * 0.25 + hesitation * 0.20 +
                rate_anomaly * 0.15 + flat * 0.10)
        scores = [controlled, vocal, hesitation, rate_anomaly, flat]
        if sum(1 for s in scores if s > 60) >= 3:
            overall = min(base * 1.15, 100)
        else:
            overall = base
        overall = round(overall, 1)
        if overall < 30:
            stress_cat = "Low"
        elif overall < 50:
            stress_cat = "Moderate"
        elif overall < 75:
            stress_cat = "High-Controlled" if controlled > vocal else "High-Genuine"
        else:
            stress_cat = "Critical"
        flags = []
        if controlled > 60: flags.append("controlled_stress")
        if vocal > 60: flags.append("vocal_strain")
        if hesitation > 60: flags.append("hesitation")
        if rate_anomaly > 60: flags.append("rate_anomaly")
        if flat > 60: flags.append("flat_affect")
        missing = 0
        if f0['f0_mean_hz'] == 0: missing += 1
        confidence = 100 - (missing * 10)
        if overall > 75:
            verd_en = "Strong deception indicators across multiple dimensions."
            verd_ur = "Mazboot dhoka dene ki nishaniyaan mojood hain."
        elif overall > 50:
            verd_en = "Moderate stress cues; potential deception cannot be ruled out."
            verd_ur = "Halka tanav, dhoka ho sakta hai."
        elif overall > 30:
            verd_en = "Mild tension detected; generally truthful."
            verd_ur = "Halka sa tanav, aam taur par sachhai."
        else:
            verd_en = "Low stress, consistent with truthful speech."
            verd_ur = "Kam tanav, sachai se milti hui awaz."
        return {
            "controlled_stress_score": round(controlled, 1),
            "vocal_strain_score": round(vocal, 1),
            "hesitation_score": round(hesitation, 1),
            "rate_anomaly_score": round(rate_anomaly, 1),
            "flat_affect_score": round(flat, 1),
            "overall_deception_score": overall,
            "stress_category": stress_cat,
            "triggered_flags": flags,
            "confidence_percent": confidence,
            "verdict_english": verd_en,
            "verdict_urdu": verd_ur
        }

    def _full_transcription(self, y):
        original = ""
        english = ""
        try:
            audio_whisper = y.astype(np.float32)
            res_orig = self.whisper_model.transcribe(audio_whisper, task="transcribe")
            original = res_orig['text'].strip()
            res_en = self.whisper_model.transcribe(audio_whisper, task="translate")
            english = res_en['text'].strip()
        except Exception as e:
            print(f"Full transcription failed: {e}")
        return original, english

    # Terminal output helpers (unchanged)
    def _print_mini_report(self, result, path):
        dec = result['deception_analysis']
        print("=" * 65)
        print("   FINAL FORENSIC VOICE STRESS ANALYSIS")
        print("=" * 65)
        print(f"File: {path}")
        print(f"Duration: {result['audio_duration_sec']:.1f} sec")
        print(f"F0 mean: {result['fundamental_frequency']['f0_mean_hz']:.1f} Hz")
        print(f"Jitter: {result['micro_tremors']['jitter_local_percent']:.2f} %  "
              f"Shimmer: {result['micro_tremors']['shimmer_local_percent']:.2f} %")
        print(f"HNR: {result['spectral_clarity']['hnr_db']:.1f} dB")
        print(f"WPM: {result['temporal_dynamics']['speaking_rate_wpm']:.0f}  "
              f"Pause%: {result['temporal_dynamics']['pause_ratio_percent']:.1f}%")
        print("-" * 65)
        print(f"Overall Deception Score: {dec['overall_deception_score']:.1f}%")
        print(f"Stress Category: {dec['stress_category']}")
        print(f"Flags: {dec['triggered_flags']}")
        print(f"Confidence: {dec['confidence_percent']}%")
        print(f"Verdict (EN): {dec['verdict_english']}")
        print(f"Verdict (UR): {dec['verdict_urdu']}")
        print("-" * 65)
        print("TRANSCRIPTION (English translation):")
        print(result.get('transcription_english', 'N/A'))
        print("=" * 65 + "\n")

    def _print_segment_report(self, result):
        dec = result['deception_analysis']
        print(f"\n--- Segment {result['segment_start_sec']:.2f}-{result['segment_end_sec']:.2f}s ---")
        print(f"  Pitch: {result['fundamental_frequency']['f0_mean_hz']:.1f} Hz, "
              f"Jitter: {result['micro_tremors']['jitter_local_percent']:.2f}%, "
              f"HNR: {result['spectral_clarity']['hnr_db']:.1f} dB")
        print(f"  WPM: {result['temporal_dynamics']['speaking_rate_wpm']:.0f}, "
              f"Pause%: {result['temporal_dynamics']['pause_ratio_percent']:.1f}%")
        print(f"  Deception Score: {dec['overall_deception_score']:.1f}%  "
              f"({dec['stress_category']})  Flags: {dec['triggered_flags']}")
        print(f"  Transcript (EN): {result['transcription_english'][:120]}...\n")


if __name__ == "__main__":
    audio_path = input("Enter the audio file path (.wav / .mp3): ").strip().strip('"').strip("'")
    if not os.path.exists(audio_path):
        print(f"Error: File '{audio_path}' not found.")
        exit(1)

    analyzer = ForensicVoiceAnalyzer()
    result = analyzer.analyze(audio_path)

    if result:
        stem = os.path.splitext(os.path.basename(audio_path))[0]
        report_dir = os.path.dirname(audio_path) or "."
        report_path = os.path.join(report_dir, f"{stem}_forensic.json")
        analyzer.generate_report(result, report_path)