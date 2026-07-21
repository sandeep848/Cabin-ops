import pytest
from backend.services.speech_to_text import transcribe_audio_stub

def test_transcribe_audio_stub_medical_keywords():
    # Verify that when text hint (bytes) like b"dizzy" or b"medical" is passed,
    # it returns the medical emergency sentence.
    assert transcribe_audio_stub(b"dizzy") == "I feel dizzy and need medical assistance."
    assert transcribe_audio_stub(b"medical") == "I feel dizzy and need medical assistance."
    
    # Verify variations and casing
    assert transcribe_audio_stub(b"DiZzY") == "I feel dizzy and need medical assistance."
    assert transcribe_audio_stub(b"  medical  ") == "I feel dizzy and need medical assistance."
    assert transcribe_audio_stub(b"dizziness") == "I feel dizzy and need medical assistance."
    assert transcribe_audio_stub(b"nausea") == "I feel dizzy and need medical assistance."
    assert transcribe_audio_stub(b"pain") == "I feel dizzy and need medical assistance."

def test_transcribe_audio_stub_emergency_keywords():
    # Verify other mappings
    assert transcribe_audio_stub(b"smoke") == "There is an emergency situation that needs immediate attention."
    assert transcribe_audio_stub(b"emergency") == "There is an emergency situation that needs immediate attention."
    assert transcribe_audio_stub(b"danger") == "There is an emergency situation that needs immediate attention."

def test_transcribe_audio_stub_allergies():
    assert transcribe_audio_stub(b"allergic") == "I have a severe allergy and need to verify meal ingredients."
    assert transcribe_audio_stub(b"peanut") == "I have a severe allergy and need to verify meal ingredients."

def test_transcribe_audio_stub_fallback():
    # It gracefully falls back to the default water request for unmapped/empty content.
    assert transcribe_audio_stub(b"") == "Could I please get some water?"
    assert transcribe_audio_stub(b"random gibberish hello") == "Could I please get some water?"
