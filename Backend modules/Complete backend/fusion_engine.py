"""
fusion_engine.py

Multi-modal deception fusion engine.
Combines face behavioural cues, voice stress, and NLP text analysis
using psychological rules to compute a final deception score and verdict.

Class:
    FusionEngine
        fuse(face, voice, nlp, timestamps=None) -> dict
        explain() -> str
        generate_report(session_id, filepath=None) -> None
"""

import json
import os
import numpy as np
from typing import Dict, List, Optional, Any


class FusionEngine:
    """Fuses face, voice, and NLP data into a single deception assessment."""

    def __init__(self):
        self.last_result = None
        self.last_face = None
        self.last_voice = None
        self.last_nlp = None

    # ------------------------------------------------------------------
    #   Main fusion method
    # ------------------------------------------------------------------
    def fuse(
        self,
        face_data: Dict[str, Any],
        voice_data: Dict[str, Any],
        nlp_data: Dict[str, Any],
        timestamps: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Args:
            face_data: dict with sub-keys: eye_gaze, lip_jaw, head_pose, asymmetry, hand_touch, emotion_timeline.
            voice_data: dict with jitter, shimmer, pitch_std, etc.
            nlp_data: dict with overall_deception_score, triggered_flags, emotion_mismatch.
            timestamps: optional list of per-frame activation times for temporal analysis.

        Returns:
            dict with final_deception_score, confidence_level, active_cues, cross_modal_flags, etc.
        """
        self.last_face = face_data
        self.last_voice = voice_data
        self.last_nlp = nlp_data

        # ---- Extract behavioural scores ----
        face_scores = self._extract_face_scores(face_data)

        # ---- Base weighted sum ----
        base = self._compute_base_score(face_scores, voice_data, nlp_data)

        # ---- Apply psychological rule bonuses ----
        triggered_rules = []
        bonus = 0

        # RULE 1: Multi-cue clustering (~3 active face cues >60)
        active_cue_count = sum(1 for s in face_scores if s > 60)
        if active_cue_count >= 3:
            bonus += 15
            triggered_rules.append("RULE1: multi_cue_clustering")

        # RULE 2: Cross-modal mismatch (Neutral face + high voice stress)
        emotion = face_data.get('emotion_timeline', {}).get('dominant_emotion', '')
        voice_stress = voice_data.get('deception_score', 0)
        if emotion.lower() == 'neutral' and voice_stress > 70:
            bonus += 10
            triggered_rules.append("RULE2: face_voice_mismatch")

        # RULE 3: NLP confirms face (over_explanation + lip_disappear)
        nlp_flags = nlp_data.get('triggered_flags', [])
        lip_disappear = face_data.get('lip_jaw', {}).get('lip_disappear', False)
        if 'over_explanation' in nlp_flags and lip_disappear:
            bonus += 10
            triggered_rules.append("RULE3: nlp_lip_confirmation")

        # Apply bonuses and cap at 100
        score = min(100, base + bonus)

        # RULE 4: Temporal gate (reduce 20% if no cue persists >2 sec)
        if timestamps is not None and len(timestamps) > 0:
            persisted = self._max_cue_duration(face_scores, timestamps)
            if persisted < 2.0:
                score = score * 0.8
                triggered_rules.append("RULE4: temporal_gate_applied")

        # Final score (capped)
        score = max(0.0, min(100.0, round(score, 1)))

        # ---- Confidence level ----
        if score <= 30:
            confidence = "LOW"
        elif score <= 50:
            confidence = "MEDIUM"
        elif score <= 75:
            confidence = "HIGH"
        else:
            confidence = "CRITICAL"

        # ---- Build active_cues list ----
        active_cues = self._build_active_cues(face_scores, face_data, timestamps)

        # ---- Cross-modal flags ----
        cross_flags = []
        if emotion.lower() == 'neutral' and voice_stress > 70:
            cross_flags.append("face_neutral_but_voice_high_stress")
        if nlp_data.get('emotion_mismatch', {}).get('flagged'):
            cross_flags.append("nlp_emotion_mismatch")
        if triggered_rules:
            cross_flags.extend(triggered_rules)

        # ---- Verdict ----
        verdict = self._generate_verdict(score, triggered_rules)

        # ---- Temporal summary ----
        temporal_summary = self._temporal_summary(face_data, voice_data, nlp_data, triggered_rules)

        # ---- Breakdown ----
        breakdown = {
            "face_behavioral": round(np.mean(face_scores) if face_scores else 0, 1),
            "face_emotion": round(100 - face_data.get('emotion_timeline', {}).get('emotion_variance', 0), 1),
            "voice_stress": voice_data.get('deception_score', 0),
            "nlp_deception": nlp_data.get('overall_deception_score', 0),
            "mismatch_bonus": self._mismatch_score(face_data, voice_data, nlp_data)
        }

        result = {
            "final_deception_score": score,
            "confidence_level": confidence,
            "active_cues": active_cues,
            "cross_modal_flags": cross_flags,
            "temporal_summary": temporal_summary,
            "breakdown": breakdown,
            "verdict": verdict,
            "is_deceptive": score > 50
        }

        self.last_result = result
        return result

    # ------------------------------------------------------------------
    #   Explanation
    # ------------------------------------------------------------------
    def explain(self) -> str:
        """Return a human-readable breakdown of the last fusion result."""
        if self.last_result is None:
            return "No analysis performed yet."

        r = self.last_result
        lines = [
            f"FINAL DECEPTION SCORE: {r['final_deception_score']}/100 ({r['confidence_level']})",
            f"VERDICT: {'DECEPTIVE' if r['is_deceptive'] else 'TRUTHFUL'}",
            "--- Breakdown ---",
            f" Face behavioral: {r['breakdown']['face_behavioral']}",
            f" Face emotion (controlled): {r['breakdown']['face_emotion']}",
            f" Voice stress: {r['breakdown']['voice_stress']}",
            f" NLP deception: {r['breakdown']['nlp_deception']}",
            f" Cross-modal mismatch: {r['breakdown']['mismatch_bonus']}",
            "--- Active Cues ---",
        ]
        for cue in r['active_cues']:
            lines.append(f" {cue['module']} -> {cue['cue']} (severity {cue['severity']})")
        lines.append("--- Cross-Modal Flags ---")
        for flag in r['cross_modal_flags']:
            lines.append(f" - {flag}")
        return "\n".join(lines)

    def generate_report(self, session_id: str, filepath: Optional[str] = None) -> None:
        """Save last fusion result as JSON to disk."""
        if self.last_result is None:
            print("No result to save.")
            return
        if filepath is None:
            filepath = f"deception_report_{session_id}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.last_result, f, indent=2, ensure_ascii=False)
        print(f"Report saved to {filepath}")

    # ------------------------------------------------------------------
    #   Private helpers
    # ------------------------------------------------------------------
    def _extract_face_scores(self, face: Dict) -> List[float]:
        """Return a list of individual cue scores (0-100) from face data."""
        scores = []

        eye = face.get('eye_gaze', {})
        # direction_changes -> scale to 0-100 (assume max 20)
        dir_score = min(eye.get('direction_changes', 0) * 5, 100)
        scores.append(eye.get('gaze_stability', 0))
        scores.append(dir_score)
        scores.append(eye.get('fixation_score', 0))
        scores.append(100 if eye.get('blink_rate_spike', False) else 0)

        lip = face.get('lip_jaw', {})
        scores.append(lip.get('jaw_tightness', 0))
        scores.append(lip.get('lip_compression', 0))
        scores.append(lip.get('chin_tremor', 0))
        scores.append(100 if lip.get('lip_disappear', False) else 0)

        head = face.get('head_pose', {})
        scores.append(head.get('withdrawal_score', 0))
        scores.append(head.get('stiffness', 0))
        scores.append(100 if head.get('is_nodding', False) else 0)
        scores.append(100 if head.get('is_shaking', False) else 0)

        asym = face.get('asymmetry', {})
        scores.append(asym.get('total_asym', 0))
        scores.append(asym.get('mouth_asym', 0))
        scores.append(asym.get('brow_asym', 0))

        touch = face.get('hand_touch', {})
        scores.append(touch.get('touch_score', 0))
        # Add duration score (scale: max 30 frames -> 100)
        dur = touch.get('touch_duration', 0)
        scores.append(min(dur / 30 * 100, 100))

        return scores

    def _compute_base_score(self, face_scores: List[float],
                            voice: Dict, nlp: Dict) -> float:
        # Module averages
        eye_score = np.mean(face_scores[0:4])
        lip_score = np.mean(face_scores[4:8])
        head_score = np.mean(face_scores[8:12])
        asym_score = np.mean(face_scores[12:15])
        touch_score = np.mean(face_scores[15:17])
        face_behavioral = np.mean([eye_score, lip_score, head_score, asym_score, touch_score])

        # Emotion (controlled = high score)
        emotion_var = self.last_face.get('emotion_timeline', {}).get('emotion_variance', 50)
        face_emotion = 100 - emotion_var

        voice_score = voice.get('deception_score', 0)
        nlp_score = nlp.get('overall_deception_score', 0)

        mismatch = self._mismatch_score(self.last_face, voice, nlp)

        weights = [0.35, 0.10, 0.25, 0.25, 0.05]
        base = (weights[0]*face_behavioral + weights[1]*face_emotion +
                weights[2]*voice_score + weights[3]*nlp_score +
                weights[4]*mismatch)
        return base

    def _mismatch_score(self, face: Dict, voice: Dict, nlp: Dict) -> float:
        """Returns 0-100 indicating cross-modal inconsistency."""
        mis = 0
        emotion = face.get('emotion_timeline', {}).get('dominant_emotion', '')
        voice_stress = voice.get('deception_score', 0)
        nlp_mismatch_flag = nlp.get('emotion_mismatch', {}).get('flagged', False)

        if emotion.lower() == 'neutral' and voice_stress > 70:
            mis = min(voice_stress, 100)
        if nlp_mismatch_flag:
            mis = max(mis, nlp.get('emotion_mismatch', {}).get('score', 0))
        return mis

    def _max_cue_duration(self, face_scores: List[float],
                          timestamps: List[float]) -> float:
        """Estimate longest continuous period where any cue >60 was active.
        We assume timestamps list corresponds to face_scores per frame (but we only have one aggregated set).
        This is a simplified simulation: if any of the extracted scores >60, treat as active during that timestamp.
        """
        active = [1 if max(face_scores) > 60 else 0] * len(timestamps)  # dummy
        # If we had per-frame scores, we'd use those. Here we pretend constant activity.
        if len(timestamps) > 0:
            # Simulate: if any cue is >60, it's active throughout
            if max(face_scores) > 60:
                return timestamps[-1] - timestamps[0]
        return 0.0

    def _build_active_cues(self, face_scores: List[float],
                           face: Dict, timestamps: Optional[List[float]]) -> List[Dict]:
        """Create a list of active cues (score >60)."""
        cues = []
        # Mapping of score index ranges to modules/cue names
        mapping = [
            (0, 'eye_gaze', 'gaze_stability'),
            (1, 'eye_gaze', 'direction_changes'),
            (2, 'eye_gaze', 'fixation_score'),
            (3, 'eye_gaze', 'blink_rate_spike'),
            (4, 'lip_jaw', 'jaw_tightness'),
            (5, 'lip_jaw', 'lip_compression'),
            (6, 'lip_jaw', 'chin_tremor'),
            (7, 'lip_jaw', 'lip_disappear'),
            (8, 'head_pose', 'withdrawal_score'),
            (9, 'head_pose', 'stiffness'),
            (10,'head_pose', 'is_nodding'),
            (11,'head_pose', 'is_shaking'),
            (12,'asymmetry', 'total_asym'),
            (13,'asymmetry', 'mouth_asym'),
            (14,'asymmetry', 'brow_asym'),
            (15,'hand_touch', 'touch_score'),
            (16,'hand_touch', 'touch_duration_score')
        ]
        for idx, (i, mod, cue) in enumerate(mapping):
            score = face_scores[i]
            if score > 60:
                # approximate duration (if timestamps available, use average)
                duration = 0
                timestamp = "00:00.000"
                if timestamps and len(timestamps) > 0:
                    timestamp = f"{int(timestamps[0]//60):02d}:{timestamps[0]%60:06.3f}"
                    duration = (timestamps[-1] - timestamps[0]) if len(timestamps) > 1 else 0
                cues.append({
                    "module": mod,
                    "cue": cue,
                    "severity": round(score, 1),
                    "timestamp": timestamp,
                    "duration": round(duration, 2)
                })
        return cues

    def _generate_verdict(self, score: float, rules: List[str]) -> str:
        """One-line bilingual verdict."""
        if score > 75:
            return ("Kai nishani milaap dekhe gaye hain / "
                    "Multiple deception indicators detected")
        elif score > 50:
            return ("Kuch shak ki nishaniyaan hain / "
                    "Some suspicion indicators present")
        elif score > 30:
            return ("Mamuli tanav, par deception nahi / "
                    "Minor stress, no deception")
        else:
            return ("Saaf awaz, sachai lagti hai / "
                    "Clean signal, truthfulness likely")

    def _temporal_summary(self, face, voice, nlp, rules) -> str:
        # placeholder
        return "Analysis performed on the provided cue averages."