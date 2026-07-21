# High-accuracy regex/rules based intent classifier and parser. Imported by backend/main.py.
import re
from backend.services.router import seat_to_zone

# Regex patterns with word boundaries
INTENT_PATTERNS = [
    ("emergency", [
        r"\bemergency\b", r"\bfire\b", r"\bsmoke\b", r"\baccident\b", r"\bcrashing\b"
    ], 0.90, "high", "urgent_pending", "Safety Alert: Immediate crew response required."),
    
    ("medical_assistance", [
        r"\bdizzy\b", r"\bsick\b", r"\bfaint\b", r"\bdoctor\b", r"\bmedical\b",
        r"\bchest\s+pain\b", r"\bpain\b", r"\bnauseous\b", r"\bpassed\s+out\b",
        r"\bhurt\b", r"\bbleeding\b", r"\bmedication\b", r"\bmedicine\b",
        r"\bbreath\w*", r"\bchok\w*", r"\bsuffocat\w*", r"\bheart\w*", r"\bseiz\w*", r"\bunconscious\b"
    ], 0.90, "high", "urgent_pending", "Medical Alert: Flight attendant dispatch required."),
    
    ("allergy_question", [
        r"\ballergy\b", r"\ballergic\b", r"\bcontain\b", r"\bwalnut\b", r"\bpeanuts?\b",
        r"\bnuts?\b", r"\bdairy\b", r"\bgluten\b"
    ], 0.85, "high", "urgent_pending", "Verify dietary ingredients with galley team."),
    
    ("missed_announcement", [
        r"\bcaptain\b", r"\bannouncements?\b", r"\bannounced\b", r"\bwhat\s+did\s+they\s+say\b",
        r"\breplay\s+announcement\b", r"\bmissed\s+announcement\b"
    ], 0.80, "low", "answered", "Playback request for public announcements."),
    
    ("connection_help", [
        r"\bconnecting\s+flight\b", r"\bconnection\s+gate\b", r"\bnext\s+flight\b",
        r"\blayover\b", r"\bflight\s+connection\b", r"\bgate\s+for\s+flight\b"
    ], 0.85, "low", "answered", "Gate information will be updated upon approach."),
    
    ("lavatory_question", [
        r"\blavatory\b", r"\brestroom\b", r"\bbathroom\b", r"\btoilet\b", r"\bwashroom\b"
    ], 0.85, "low", "answered", "Lavatories are located at the front and back of each section."),
    
    ("meal_issue", [
        r"\bwrong\s+meal\b", r"\bwrong\s+food\b", r"\bcold\s+food\b", r"\bcold\s+meal\b",
        r"\bspilled\s+my\b", r"\bwrong\s+tray\b", r"\bhair\s+in\b"
    ], 0.85, "medium", "pending", "Prepare replacement meal/beverage tray."),
    
    ("meal_request", [
        r"\bcoffee\b", r"\btea\b", r"\bdrink\b", r"\bfood\b", r"\bchicken\b", r"\bmeal\b",
        r"\bvegetarian\b", r"\bbreakfast\b", r"\blunch\b", r"\bdinner\b", r"\bsnack\b"
    ], 0.80, "low", "pending", "Deliver meal service items."),
    
    ("water_request", [
        r"\bwater\b"
    ], 0.80, "low", "pending", "Deliver fresh drinking water."),
    
    ("blanket_request", [
        r"\bblanket\b", r"\bpillow\b", r"\bheadphones?\b", r"\bearphones?\b"
    ], 0.80, "low", "pending", "Deliver requested comfort amenities."),
    
    ("screen_issue", [
        r"\bscreen\b", r"\btv\b", r"\bfrozen\b", r"\bife\b", r"\btouchscreen\b"
    ], 0.80, "medium", "pending", "Perform entertainment screen system reset."),
    
    ("seat_issue", [
        r"\brecline\b", r"\bseatbelt\s+stuck\b", r"\btray\s+table\b", r"\barmrest\b",
        r"\bheadrest\b", r"\bseat\s+button\b", r"\bpocket\s+is\s+ripped\b"
    ], 0.85, "medium", "pending", "Inspect seat safety and mechanical functions."),
    
    ("child_assistance", [
        r"\bbaby\s+food\b", r"\bwarm\s+up\s+bottle\b", r"\bheat\s+the\s+milk\b", r"\bdiaper\b",
        r"\bbaby\s+wipes\b", r"\btoddler\s+seat\b", r"\binfant\b"
    ], 0.85, "low", "pending", "Provide infant care/amenity support."),
    
    ("complaint", [
        r"\bsnoring\b", r"\bkicking\s+my\b", r"\btoo\s+loud\b", r"\btoo\s+noisy\b",
        r"\brude\s+passenger\b", r"\bslow\s+service\b"
    ], 0.85, "medium", "pending", "Supervisor response requested for cabin service dispute."),
    
    ("out_of_scope", [
        r"\bweather\s+in\b", r"\bhotel\s+in\b", r"\btrain\s+ticket\b", r"\bflying\s+over\b"
    ], 0.85, "none", "ignored", "Query outside crew scope. Automatic response sent.")
]

def parse_request(text: str, seat: str) -> dict:
    lower = text.lower().strip()
    
    # Defaults
    intent = "out_of_scope"
    urgency = "none"
    slots = {}
    crew_required = False
    status = "ignored"
    action = "Do not create crew task."
    confidence = 0.55
    
    # 1. Match Intent using Regexes with Word Boundaries
    for int_name, patterns, conf, urg, stat, act in INTENT_PATTERNS:
        matched = False
        for pattern in patterns:
            if re.search(pattern, lower):
                matched = True
                break
        if matched:
            intent = int_name
            confidence = conf
            urgency = urg
            status = stat
            action = act
            # Determine if crew is required based on intent status
            crew_required = status in {"pending", "urgent_pending"}
            break

    # 2. Slot Extraction and Catalog Mapping
    if intent == "medical_assistance":
        symptom = "medical"
        if re.search(r"\bchest\s+pain\b", lower):
            symptom = "chest pain"
        elif re.search(r"\bnauseous\b", lower):
            symptom = "nauseous"
        elif re.search(r"\bdizzy\b", lower):
            symptom = "dizzy"
        slots = {"symptom": symptom}
        
    elif intent == "meal_request":
        # Check canonical items
        if re.search(r"\bcoffee\b", lower):
            slots = {"item": "coffee"}
        elif re.search(r"\bvegetarian\b|\bveg\b", lower):
            slots = {"item": "vegetarian_meal"}
        elif re.search(r"\bfruit\b|\bfruits\b", lower):
            slots = {"item": "fruit_plate"}
        else:
            # Generic/unstocked items (e.g. tea, meal, chicken, food, snack, etc.)
            # Do NOT set item in slots, which avoids inventory check & deduction.
            # Keep crew_required = True so it's a crew task.
            pass
            
    elif intent == "water_request":
        slots = {"item": "water"}
        
    elif intent == "blanket_request":
        if re.search(r"\bblanket\b", lower):
            slots = {"item": "blanket"}
        elif re.search(r"\bheadphones?\b|\bearphones?\b", lower):
            slots = {"item": "headphones"}
        # Generic/unstocked items (e.g. pillow) do not get cataloged, but crew is still required
        
    elif intent == "screen_issue":
        slots = {"device": "seatback_screen"}

    # Apply seat zone routing if crew is required
    zone = seat_to_zone(seat) if crew_required else None

    return {
        "seat": seat,
        "intent": intent,
        "urgency": urgency,
        "slots": slots,
        "crew_required": crew_required,
        "assigned_zone": zone,
        "status": status,
        "confidence": confidence,
        "action": action,
    }
