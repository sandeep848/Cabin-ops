import pytest
from backend.services import speech_to_text


def test_empty_audio_is_not_invented():
    with pytest.raises(ValueError, match="empty"):
        speech_to_text.transcribe_audio(b"")


def test_unavailable_engine_is_not_invented(monkeypatch):
    def unavailable():
        raise RuntimeError("Voice unavailable")

    monkeypatch.setattr(speech_to_text, "get_whisper_model", unavailable)
    with pytest.raises(RuntimeError):
        speech_to_text.transcribe_audio(b"audio")


def test_transcription_and_tempfile_cleanup(monkeypatch):
    from pathlib import Path

    paths = []

    class Model:
        def transcribe(self, path):
            paths.append(path)
            assert Path(path).read_bytes() == b"actual audio"
            return {"text": " I need help. "}

    monkeypatch.setattr(speech_to_text, "get_whisper_model", lambda: Model())
    assert speech_to_text.transcribe_audio(b"actual audio") == "I need help."
    assert not Path(paths[0]).exists()
