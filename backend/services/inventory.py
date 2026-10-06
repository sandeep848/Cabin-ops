# Inventory level manager verifying item stock limits. Imported by backend/main.py.
import json
import logging
from backend.config import DATA_DIR
from backend.database import get_connection

INVENTORY_PATH = DATA_DIR / "inventory.json"
logger = logging.getLogger("cabinops.inventory")

def init_inventory_db() -> None:
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                item TEXT PRIMARY KEY,
                stock INTEGER NOT NULL CHECK(stock >= 0),
                alternative TEXT
            )
        """)
        conn.commit()
        
        row = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()
        if row[0] == 0:
            if not INVENTORY_PATH.exists():
                logger.error(f"Required inventory file not found at {INVENTORY_PATH}")
                raise RuntimeError(f"Required inventory file not found at {INVENTORY_PATH}")
            try:
                data = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
                for k, v in data.items():
                    alt = None
                    if k.lower() == "coffee":
                        alt = "water"
                    elif k.lower() == "vegetarian_meal":
                        alt = "fruit_plate"
                    conn.execute(
                        "INSERT OR IGNORE INTO inventory (item, stock, alternative) VALUES (?, ?, ?)",
                        (k.lower(), int(v), alt)
                    )
                conn.commit()
            except Exception as exc:
                logger.error(f"Error seeding inventory from {INVENTORY_PATH}: {exc}", exc_info=True)
                raise RuntimeError(f"Error seeding inventory: {exc}") from exc

def reset_inventory_db() -> None:
    with get_connection() as conn:
        conn.execute("DROP TABLE IF EXISTS inventory")
        conn.commit()
    init_inventory_db()

def reserve_item(item: str | None, quantity: int = 1, connection=None) -> bool:
    if not item:
        return True
    if quantity < 1:
        raise ValueError("Reservation quantity must be positive")
    def reserve(conn):
        return conn.execute(
            "UPDATE inventory SET stock = stock - ? WHERE item = ? AND stock >= ?",
            (quantity, item.lower(), quantity),
        ).rowcount > 0
    if connection is not None:
        return reserve(connection)
    with get_connection() as conn:
        return reserve(conn)

def suggest_alternative(item: str | None) -> str | None:
    if not item:
        return None
    with get_connection() as conn:
        row = conn.execute("SELECT alternative FROM inventory WHERE item = ?", (item.lower(),)).fetchone()
        if row:
            return row["alternative"]
        return None
