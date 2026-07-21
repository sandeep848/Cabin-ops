# Speech-to-text service with keyword-matching fallback. Imported by backend/main.py.
try:
    import whisper
except ImportError:
    whisper = None

import re

# Keyword-to-utterance mapping for local fallback STT simulation
_KEYWORD_MAP = [
    (r"\bdizzy\b|\bsick\b|\bnauseous\b|\bpain\b|\bhurt\b|\bmedical\b",
     "I feel dizzy and need medical assistance."),
    (r"\bsmoke\b|\bfire\b|\bemergency\b|\bdanger\b",
     "There is an emergency situation that needs immediate attention."),
    (r"\ballerg\b|\bpeanut\b|\bnut\b|\bdairy\b|\bgluten\b",
     "I have a severe allergy and need to verify meal ingredients."),
    (r"\bwater\b|\bdrink\b",
     "Could I please get some water?"),
    (r"\bcoffee\b|\btea\b|\bsnack\b|\bmeal\b|\bfood\b",
     "Can I get a meal or beverage please?"),
    (r"\bblanket\b|\bpillow\b|\bcold\b",
     "Could I get an extra blanket? I am cold."),
    (r"\bheadphone\b|\bearphone\b",
     "Can I get a pair of headphones?"),
    (r"\bscreen\b|\bfrozen\b|\btv\b|\bife\b",
     "My seatback screen is frozen and not responding."),
    (r"\bannouncement\b|\bcaptain\b|\bsay\b",
     "What did the captain say in the last announcement?"),
    (r"\blavatory\b|\bbathroom\b|\brestroom\b|\btoilet\b",
     "Is the lavatory available right now?"),
]


def transcribe_audio_stub(audio_bytes: bytes) -> str:
    """
    Keyword-matching STT fallback.
    Attempts to decode audio bytes as UTF-8 text first (for testing with text payloads).
    Otherwise uses the default placeholder.
    When Whisper is available, this would call whisper.load_model('base').transcribe().
    """
    # If Whisper is installed, use it (production path)
    if whisper is not None:
        try:
            import tempfile, os
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            try:
                model = whisper.load_model('base')
                result = model.transcribe(tmp_path)
                return result.get('text', '').strip()
            finally:
                os.unlink(tmp_path)
        except Exception:
            pass  # Fall through to keyword matching

    # Try to decode bytes as a text hint (used in testing)
    try:
        hint = audio_bytes.decode('utf-8', errors='ignore').strip().lower()
        if hint:
            for pattern, response in _KEYWORD_MAP:
                if re.search(pattern, hint, re.IGNORECASE):
                    return response
    except Exception:
        pass

    # Default fallback: most common request type
    return "Could I please get some water?"
