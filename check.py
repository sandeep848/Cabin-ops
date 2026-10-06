"""Run isolated CabinOps regression checks using the active Python environment."""
import subprocess
import sys
from pathlib import Path

def main():
    root = Path(__file__).resolve().parent
    result = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=root)
    if result.returncode:
        return result.returncode
    return subprocess.run([sys.executable, "scripts/evaluate_parser.py"], cwd=root).returncode

if __name__ == "__main__":
    raise SystemExit(main())
