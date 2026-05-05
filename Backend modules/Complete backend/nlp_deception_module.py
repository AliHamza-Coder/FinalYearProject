"""
nlp_deception_module.py

Text-based deception analysis using Groq's Llama-3.3-70B-versatile.
Detects evasion, over-explanation, irrelevance, contradiction, vagueness,
improbable details, and emotion mismatch with a voice stress score.

Class:
    NLPDeceptionAnalyzer
        analyze(text, voice_stress=0, question_context="") -> dict
"""

import os
import json
import time
from typing import Optional, Dict, Any

try:
    from groq import Groq
except ImportError:
    raise ImportError("Please install 'groq' package: pip install groq")

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file
except ImportError:
    pass  # python-dotenv not installed, continue without it


class NLPDeceptionAnalyzer:
    """Uses Groq's LLM to detect deception indicators in a transcript."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with Groq API key.

        Args:
            api_key: If None, reads from environment variable GROQ_API_KEY.
        """
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Groq API key not provided. Set GROQ_API_KEY environment variable "
                "or pass api_key to constructor."
            )
        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.3-70b-versatile"
        self.temperature = 0.1

    def analyze(
        self, text: str, voice_stress: float = 0, question_context: str = ""
    ) -> Dict[str, Any]:
        """Analyze a transcript for deception indicators.

        Args:
            text: The transcript (can be English, Roman Urdu, or Urdu).
            voice_stress: Score from 0 to 100 from external voice stress module.
            question_context: Optional question that was asked (for context).

        Returns:
            A dict with all deception indicators, translations, and overall score.
        """
        if not text.strip():
            return self._unanalyzable_result("Empty input.")

        # Build the prompt
        prompt = self._build_prompt(text, voice_stress, question_context)

        # Call Groq API with retries
        response_json = self._call_groq_with_retries(prompt)

        if response_json is None:
            # Fallback if API fails entirely
            return self._unanalyzable_result("API call failed.")

        # Parse and validate the JSON response
        result = self._parse_response(response_json, text)

        return result

    # ------------------------------------------------------------------
    #   Private helpers
    # ------------------------------------------------------------------
    def _build_prompt(self, text: str, voice_stress: float, question: str) -> str:
        """Construct the system + user prompt."""
        sys_msg = (
            "You are a forensic linguistics expert analyzing a transcript for deception. "
            "Your task is to output a single JSON object with the following fields:\n"
            "- translated_urdu: Roman Urdu translation of the text (if already Roman Urdu, keep it as-is)\n"
            "- translated_english: English translation of the text\n"
            "- language_detected: one of 'english', 'roman_urdu', 'urdu'\n"
            "- deception_indicators: object with six sub-objects (evasion, over_explanation, "
            "irrelevance, contradiction, vagueness, improbable_details), each containing:\n"
            "    'score': integer 0-100, 'flagged': boolean (true if score > 60)\n"
            "- emotion_mismatch: object with 'score' (integer 0-100) and 'flagged' (boolean). "
            "Set score>60 only if voice_stress>70 but text claims calm/normal.\n"
            "- overall_deception_score: integer 0-100, average of all indicator scores plus a bonus from emotion mismatch (max 100)\n"
            "- triggered_flags: list of indicator names that were flagged\n"
            "- summary: one short sentence in Roman Urdu + English (e.g., 'Roman Urdu: ... | English: ...')\n"
            "- is_analyzable: boolean. False for greetings, single words, incomplete sentences, or pure filler. True otherwise.\n"
            "\nRules:\n"
            "- Evasion: not answering the question directly.\n"
            "- Over-explanation: unnecessary details to build credibility.\n"
            "- Irrelevance: off-topic or semantic drift.\n"
            "- Contradiction: self-contradicting within the response.\n"
            "- Vagueness: hedge words like 'maybe', 'I think', 'probably', 'kind of', 'around'.\n"
            "- Improbable details: too-specific timestamps, perfect memory of trivial things.\n"
            "- Emotion mismatch: only flag if voice_stress > 70 but text is calm/normal.\n"
            "Be objective. Respond ONLY with the JSON object, no extra text."
        )

        user_parts = [
            f"Transcript: \"{text}\"",
            f"Voice stress score (0-100): {voice_stress}" if voice_stress else "",
            f"Question context: \"{question}\"" if question else "",
        ]
        user_msg = "\n".join(filter(None, user_parts))

        return f"System: {sys_msg}\nUser: {user_msg}"

    def _call_groq_with_retries(self, prompt: str, max_retries: int = 2) -> Optional[str]:
        """Call Groq API and return raw JSON string. Retries on failure."""
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=self.temperature,
                    max_tokens=1024,
                )
                content = response.choices[0].message.content.strip()
                # Remove markdown code fences if present
                if content.startswith("```"):
                    content = content.strip("`")
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.strip()
                return content
            except Exception as e:
                print(f"Groq API attempt {attempt+1} failed: {e}")
                time.sleep(2 ** attempt)  # simple backoff
        print("All Groq API retries exhausted.")
        return None

    def _parse_response(self, json_str: str, original_text: str) -> Dict[str, Any]:
        """Parse the LLM JSON output and return a clean result dict."""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            print("Failed to parse LLM response. Falling back.")
            return self._unanalyzable_result("Invalid JSON from API.")

        # Enforce required fields
        if "deception_indicators" not in data or "is_analyzable" not in data:
            return self._unanalyzable_result("Missing fields in API response.")

        # If not analyzable, zero out scores
        if not data.get("is_analyzable", False):
            return self._unanalyzable_result("Text not suitable for analysis.", data)

        # Normalize scores: ensure integers 0-100
        indicators = data["deception_indicators"]
        for key in ("evasion", "over_explanation", "irrelevance", "contradiction",
                    "vagueness", "improbable_details"):
            if key in indicators:
                indicators[key]["score"] = max(0, min(100, int(indicators[key].get("score", 0))))
                indicators[key]["flagged"] = indicators[key]["score"] > 60
            else:
                indicators[key] = {"score": 0, "flagged": False}

        # Emotion mismatch
        mismatch = data.get("emotion_mismatch", {})
        mismatch["score"] = max(0, min(100, int(mismatch.get("score", 0))))
        mismatch["flagged"] = mismatch["score"] > 60
        data["emotion_mismatch"] = mismatch

        # Overall score = average of indicators + extra from mismatch (simple bonus)
        indicator_scores = [indicators[k]["score"] for k in indicators]
        avg_score = sum(indicator_scores) / len(indicator_scores) if indicator_scores else 0
        # Add mismatch bonus: up to 20 extra points proportionally
        bonus = min(20, mismatch["score"] * 0.2)
        overall = min(100, round(avg_score + bonus))
        data["overall_deception_score"] = overall

        # Triggered flags
        triggered = [k for k, v in indicators.items() if v["flagged"]]
        if mismatch["flagged"]:
            triggered.append("emotion_mismatch")
        data["triggered_flags"] = triggered

        # Ensure summary and translations exist
        data.setdefault("translated_urdu", original_text)
        data.setdefault("translated_english", original_text)
        data.setdefault("language_detected", "unknown")
        data.setdefault("summary", f"Roman Urdu: {original_text[:100]}... | English: {original_text[:100]}...")

        return data

    def _unanalyzable_result(self, reason: str, partial: Optional[Dict] = None) -> Dict[str, Any]:
        """Return a default result when analysis is impossible."""
        base = {
            "translated_urdu": "",
            "translated_english": "",
            "language_detected": "unknown",
            "deception_indicators": {
                "evasion": {"score": 0, "flagged": False},
                "over_explanation": {"score": 0, "flagged": False},
                "irrelevance": {"score": 0, "flagged": False},
                "contradiction": {"score": 0, "flagged": False},
                "vagueness": {"score": 0, "flagged": False},
                "improbable_details": {"score": 0, "flagged": False},
            },
            "emotion_mismatch": {"score": 0, "flagged": False},
            "overall_deception_score": 0,
            "triggered_flags": [],
            "summary": "Text not suitable for analysis.",
            "is_analyzable": False,
        }
        if partial:
            base.update({k: v for k, v in partial.items() if k in base})
        return base


# -------------------------------------------------------------------------
#   Example usage
# -------------------------------------------------------------------------
if __name__ == "__main__":
    analyzer = NLPDeceptionAnalyzer()  # requires GROQ_API_KEY env var

    # Example test
    sample_text = (
        "Main ghar par tha, Netflix dekh raha tha, Stranger Things season 3 episode 4, "
        "bilkul 9:15 baje, aur mere paas popcorn bhi tha"
    )
    question = "Tum kal raat kahan the?"
    result = analyzer.analyze(sample_text, voice_stress=20, question_context=question)

    print(json.dumps(result, indent=2, ensure_ascii=False))