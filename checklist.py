"""Check required repository assets without claiming runtime validation."""
from pathlib import Path

REQUIRED = ["backend/main.py", "backend/database/schema.py", "backend/services/intent_parser.py", "frontend/passenger_screen/package-lock.json", "frontend/crew_dashboard/package-lock.json", "Dockerfile", "compose.yaml", ".env.example", ".github/workflows/ci.yml", "PRD.md"]

def main():
    root = Path(__file__).resolve().parent
    missing = [name for name in REQUIRED if not (root / name).is_file()]
    for name in REQUIRED:
        print(f"{'MISSING' if name in missing else 'OK'} {name}")
    print("Run python check.py and build both frontends for runtime validation.")
    return bool(missing)

if __name__ == "__main__":
    raise SystemExit(main())
