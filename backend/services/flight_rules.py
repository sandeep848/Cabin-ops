# Flight rules engine restricting/blocking crew tasks based on cabin phase. Imported by backend/main.py.
def apply_flight_rules(parsed: dict, flight_context: dict) -> dict:
    # Copy the parsed object to prevent mutating the original input in place
    parsed_copy = dict(parsed)
    if "slots" in parsed:
        parsed_copy["slots"] = dict(parsed["slots"])

    phase = flight_context.get("flight_phase", "cruise")
    seatbelt = flight_context.get("seatbelt_sign", False)
    meal_active = flight_context.get("meal_service_active", True)
    intent = parsed_copy["intent"]

    # Safety-critical intents always bypass all restrictions
    if intent in {"medical_assistance", "emergency", "allergy_question"}:
        return parsed_copy

    # Phases where standard cabin service is suspended by the application policy
    RESTRICTED_PHASES = {"takeoff", "landing_preparation", "landing", "taxi", "boarding"}

    if phase in RESTRICTED_PHASES:
        if intent in {"water_request", "meal_request", "blanket_request"}:
            parsed_copy["crew_required"] = False
            parsed_copy["assigned_zone"] = None
            parsed_copy["status"] = "delayed"
            parsed_copy["action"] = f"Delay; service paused during {phase.replace('_', ' ')} phase."
            return parsed_copy

    if not meal_active and intent == "meal_request":
        parsed_copy["crew_required"] = False
        parsed_copy["assigned_zone"] = None
        parsed_copy["status"] = "delayed"
        parsed_copy["action"] = "Delay; meal service is currently inactive."
        return parsed_copy

    if seatbelt and intent == "lavatory_question":
        parsed_copy["crew_required"] = False
        parsed_copy["assigned_zone"] = None
        parsed_copy["status"] = "answered"
        parsed_copy["action"] = "Auto-answer: lavatory unavailable while seatbelt sign is on."
        return parsed_copy

    return parsed_copy
