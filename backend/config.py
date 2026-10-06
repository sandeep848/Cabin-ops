# Configuration parameters and path constants. Imported by backend modules and database services.
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = Path(
    os.getenv("CABINOPS_DB_PATH", str(BASE_DIR / "cabinops.db"))
).expanduser()

CATALOG_PATH = Path(
    os.getenv("CABIN_ATLAS_CATALOG_PATH", str(DATA_DIR / "content_catalog.json"))
).expanduser()
MEDIA_DIR = Path(
    os.getenv("CABIN_ATLAS_MEDIA_DIR", str(BASE_DIR / "media"))
).expanduser()
