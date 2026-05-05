"""
reasoning_engine.py

Generates human‑readable deception reasoning using Groq LLM.

Class:
    ReasoningEngine
        explain(segment_data) -> str
"""

import os
import json
import time
from typing import Dict, Any

try:
    from groq import Groq
except ImportError:
    raise ImportError("Please install 'groq' package: pip install groq")


class ReasoningEngine:
    """Produces a natural‑language explanation for a deceptive segment."""

    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("Set GROQ_API_KEY env variable or pass api_key.")
        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.3-70b-versatile"

    def explain(self, segment_data: Dict[str, Any]) -> str:
        """Generate an explanation string.

        Args:
            segment_data: dict containing:
                - text: transcribed answer
                - face_cues: dict with aggregated behavioural metrics
                - voice_stress: dict with voice stress features
                - nlp_flags: list of triggered NLP deception flags
                - start_time, end_time: timestamp

        Returns:
            A human‑readable string explaining why this segment may indicate deception.
        """
        prompt = self._build_prompt(segment_data)
        for attempt in range(2):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a forensic psychologist assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=500,
                )
                explanation = response.choices[0].message.content.strip()
                return explanation
            except Exception as e:
                print(f"Groq API attempt {attempt+1} failed: {e}")
                time.sleep(2 ** attempt)
        return "Could not generate explanation due to API error."

    def _build_prompt(self, data: Dict) -> str:
        face = json.dumps(data.get('face_cues', {}), indent=2)
        voice = json.dumps(data.get('voice_stress', {}), indent=2)
        nlp = data.get('nlp_flags', [])
        text = data.get('text', '')
        start = data.get('start_time', 0)
        end = data.get('end_time', 0)

        prompt = f"""
A suspect was interviewed. During the time interval [{start:.2f}s - {end:.2f}s], they said:
"{text}"

Behavioural cues detected:
{face}

Voice stress metrics:
{voice}

NLP deception flags: {nlp}

Based on these observations, produce a short (2-3 sentence) explanation of WHY this segment appears deceptive.
Mention the most relevant cues (e.g., "hand touching face while over-explaining", "flat voice pitch with high jitter", etc).
Use plain English. Be concrete and avoid speculation.
"""
        return prompt


# ---------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------
if __name__ == "__main__":
    engine = ReasoningEngine()
    sample = {
        'text': "I was at home, watching Netflix, exactly at 9:15 PM, Stranger Things season 3 episode 4, and I had popcorn.",
        'face_cues': {
            'jaw_tightness': 78,
            'lip_compression': 82,
            'hand_touch': {'touched': True, 'region': 'NOSE'}
        },
        'voice_stress': {
            'jitter': 2.1,
            'pitch_std': 12,
            'pause_ratio': 35
        },
        'nlp_flags': ['over_explanation', 'improbable_details'],
        'start_time': 25.0,
        'end_time': 33.5
    }
    print(engine.explain(sample))