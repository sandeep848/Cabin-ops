"""Optional server-side transcription; never fabricate a passenger request."""

import os
import tempfile
from functools import lru_cache


@lru_cache(maxsize=1)
def get_whisper_model():
    try:
        import whisper
    except ImportError as exc:
        raise RuntimeError(
            "Server voice input is unavailable. Use browser voice input or type your request."
        ) from exc
    return whisper.load_model(os.getenv("WHISPER_MODEL", "base"))


def transcribe_audio(audio_bytes: bytes) -> str:
    if not audio_bytes:
        raise ValueError("Audio is empty.")
    model = get_whisper_model()
    path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as audio:
            audio.write(audio_bytes)
            path = audio.name
        text = model.transcribe(path).get("text", "").strip()
        if not text:
            raise ValueError(
                "No speech was recognized. Please type your request or record again."
            )
        return text
    finally:
        if path:
            os.unlink(path)
