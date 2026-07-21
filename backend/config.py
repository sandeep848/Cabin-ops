# Configuration parameters and path constants. Imported by backend modules and database services.
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "cabinops.db"
