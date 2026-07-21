import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import csv
from backend.services.intent_parser import parse_request

DATASET_PATH = ROOT / "backend" / "data" / "cabinops_requests.csv"

def evaluate() -> None:
    print("=" * 72)
    print("CabinOps AI Intent Parser Evaluation")
    print("=" * 72)
    
    if not DATASET_PATH.exists():
        print(f"[ERROR] Dataset not found at: {DATASET_PATH}")
        return
        
    records = []
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if any(row.values()): # skip empty lines
                records.append(row)
                
    total = len(records)
    if total == 0:
        print("[WARN] Dataset is empty.")
        return
        
    correct_intent = 0
    correct_urgency = 0
    correct_crew = 0
    
    print(f"Evaluating {total} samples...\n")
    print(f"{'UTTERANCE':<35} | {'EXPECTED INTENT':<20} | {'PREDICTED INTENT':<20} | {'MATCH'}")
    print("-" * 90)
    
    for row in records:
        text = row["utterance_text"]
        seat = row["seat"]
        expected_intent = row["intent"]
        expected_urgency = row["urgency"]
        expected_crew = row["crew_required"].lower() == "true"
        flight_phase = row.get("flight_phase", "cruise")
        
        parsed = parse_request(text, seat)
        
        # Apply flight rules based on the phase in the dataset row
        from backend.services.flight_rules import apply_flight_rules
        flight_context = {
            "flight_phase": flight_phase,
            "seatbelt_sign": flight_phase == "landing_preparation",
            "meal_service_active": flight_phase == "cruise",
            "minutes_to_landing": 20 if flight_phase == "landing_preparation" else 90
        }
        parsed = apply_flight_rules(parsed, flight_context)
        
        pred_intent = parsed["intent"]
        pred_urgency = parsed["urgency"]
        pred_crew = parsed["crew_required"]

        
        intent_match = expected_intent == pred_intent
        urgency_match = expected_urgency == pred_urgency
        crew_match = expected_crew == pred_crew
        
        if intent_match:
            correct_intent += 1
        if urgency_match:
            correct_urgency += 1
        if crew_match:
            correct_crew += 1
            
        short_text = text[:32] + "..." if len(text) > 35 else text
        match_str = "OK" if intent_match else "FAIL"
        print(f"{short_text:<35} | {expected_intent:<20} | {pred_intent:<20} | {match_str}")
        
    print("-" * 90)
    print("METRICS SUMMARY:")
    print(f"  Intent Accuracy:  {correct_intent}/{total} ({correct_intent/total*100:.2f}%)")
    print(f"  Urgency Accuracy: {correct_urgency}/{total} ({correct_urgency/total*100:.2f}%)")
    print(f"  Crew Req Accuracy: {correct_crew}/{total} ({correct_crew/total*100:.2f}%)")
    print("=" * 72)

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    evaluate()
