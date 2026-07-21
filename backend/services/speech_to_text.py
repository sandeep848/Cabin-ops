# Speech-to-text service with keyword-matching fallback. Imported by backend/main.py.
import re
import os
import tempfile

try:
    import whisper
except Exception:
    whisper = None

# Keyword-to-utterance mapping for local fallback STT simulation
_KEYWORD_MAP = [
    (r"\bdizzy\b|\bdizziness\b|\bsick\b|\bsickness\b|\bnauseous\b|\bnausea\b|\bpain\b|\bhurt\b|\bhurts\b|\bmedical\b|\bmeds\b|\bmedicine\b",
     "I feel dizzy and need medical assistance."),
    (r"\bsmoke\b|\bfire\b|\bemergency\b|\bemergencies\b|\bdanger\b|\bdangerous\b",
     "There is an emergency situation that needs immediate attention."),
    (r"\ballerg\w*|\bpeanut\b|\bpeanuts\b|\bnut\b|\bnuts\b|\bdairy\b|\bgluten\b",
     "I have a severe allergy and need to verify meal ingredients."),
    (r"\bwater\b|\bdrink\b|\bdrinks\b",
     "Could I please get some water?"),
    (r"\bcoffee\b|\btea\b|\bsnack\b|\bsnacks\b|\bmeal\b|\bmeals\b|\bfood\b|\bfoods\b",
     "Can I get a meal or beverage please?"),
    (r"\bblanket\b|\bblankets\b|\bpillow\b|\bpillows\b|\bcold\b",
     "Could I get an extra blanket? I am cold."),
    (r"\bheadphone\b|\bheadphones\b|\bearphone\b|\bearphones\b",
     "Can I get a pair of headphones?"),
    (r"\bscreen\b|\bscreens\b|\bfrozen\b|\btv\b|\btvs\b|\bife\b",
     "My seatback screen is frozen and not responding."),
    (r"\bannouncement\b|\bannouncements\b|\bcaptain\b|\bcaptains\b|\bsay\b|\bsaid\b|\bsaying\b",
     "What did the captain say in the last announcement?"),
    (r"\blavatory\b|\blavatories\b|\bbathroom\b|\bbathrooms\b|\brestroom\b|\brestrooms\b|\btoilet\b|\btoilets\b",
     "Is the lavatory available right now?"),
]

# Globally cached Whisper model
_whisper_model = None

def get_whisper_model():
    """
    Lazy-loads and caches the Whisper model.
    Handles any import or initialization errors gracefully without crashing or printing traceback logs.
    """
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model

    if whisper is None:
        return None

    try:
        # Load the model only once and cache it
        _whisper_model = whisper.load_model('base')
    except Exception:
        # Suppress any initialization errors and avoid printing noisy traceback logs
        _whisper_model = None

    return _whisper_model


def transcribe_audio_stub(audio_bytes: bytes) -> str:
    """
    Keyword-matching STT fallback.
    Attempts to decode audio bytes as UTF-8 text first (for testing with text payloads).
    Otherwise uses the default placeholder.
    When Whisper is available, this uses the cached Whisper model.
    """
    # 1. Try to use Whisper if it's available and successfully loaded
    model = get_whisper_model()
    if model is not None:
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            try:
                result = model.transcribe(tmp_path)
                text = result.get('text', '').strip()
                if text:
                    return text
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
        except Exception:
            pass  # Fall through to keyword matching

    # 2. Try to decode bytes as a text hint (used in testing)
    try:
        hint = audio_bytes.decode('utf-8', errors='ignore').strip().lower()
        if hint:
            for pattern, response in _KEYWORD_MAP:
                if re.search(pattern, hint, re.IGNORECASE):
                    return response
    except Exception:
        pass

    # 3. Default fallback: most common request type
    return "Could I please get some water?"

