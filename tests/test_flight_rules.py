from backend.services.flight_rules import apply_flight_rules


def test_service_paused_during_landing_preparation():
    parsed = {
        "seat": "3A",
        "intent": "water_request",
        "urgency": "low",
        "slots": {"item": "water"},
        "crew_required": True,
        "assigned_zone": "fore_cabin",
        "status": "pending",
        "confidence": 0.8,
        "action": "Create crew task.",
    }
    out = apply_flight_rules(
        parsed, {"flight_phase": "landing_preparation", "seatbelt_sign": True}
    )
    assert out["crew_required"] is False
    assert out["status"] == "delayed"
