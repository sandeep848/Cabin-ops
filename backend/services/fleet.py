"""Operator-provisioned aircraft layouts, flight instances and loading manifests."""

import json
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator
from fastapi import HTTPException
from backend.database.connection import get_connection


class CabinRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    row: int = Field(ge=1, le=999)
    blocks: list[str] = Field(min_length=1, max_length=4)
    zone: Literal["fore_cabin", "mid_cabin", "aft_cabin"]
    cabin: str = Field(min_length=1, max_length=40)

    @model_validator(mode="after")
    def validate_blocks(self):
        letters = "".join(self.blocks)
        if any(
            not block
            or len(block) > 10
            or not block.isascii()
            or not block.isalpha()
            or not block.isupper()
            for block in self.blocks
        ) or len(letters) != len(set(letters)):
            raise ValueError(
                "Use nonempty, unique uppercase seat letters in aisle-separated blocks"
            )
        return self


class AircraftProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    aircraft_id: str = Field(pattern=r"^[A-Za-z0-9_-]{2,40}$")
    name: str = Field(min_length=1, max_length=80)
    rows: list[CabinRow] = Field(min_length=1, max_length=250)

    @model_validator(mode="after")
    def validate_rows(self):
        if len({row.row for row in self.rows}) != len(self.rows):
            raise ValueError("Row numbers must be unique")
        if sum(len("".join(row.blocks)) for row in self.rows) > 1000:
            raise ValueError("At most 1000 configured seats are supported per aircraft")
        self.rows.sort(key=lambda row: row.row)
        return self


class StockItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    name: str = Field(min_length=1, max_length=80)
    category: Literal["food", "beverage", "comfort", "equipment"]
    stock: int = Field(ge=0, le=10000)
    capacity: int = Field(ge=1, le=10000)
    alternative: str | None = Field(None, pattern=r"^[a-z][a-z0-9_]{0,63}$")
    allergens: list[str] = Field(default_factory=list, max_length=20)
    dietary_tags: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_stock(self):
        if self.stock > self.capacity:
            raise ValueError("Loaded stock exceeds configured capacity")
        if any(len(value) > 40 for value in [*self.allergens, *self.dietary_tags]):
            raise ValueError("Food labels are limited to 40 characters")
        return self


def init_fleet(conn):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS aircraft (aircraft_id TEXT PRIMARY KEY, name TEXT NOT NULL, layout_json TEXT NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS flights (flight_id TEXT PRIMARY KEY, aircraft_id TEXT NOT NULL, origin TEXT NOT NULL, destination TEXT NOT NULL, layout_json TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'active')"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS crew_assignments (username TEXT NOT NULL, flight_id TEXT NOT NULL, PRIMARY KEY(username,flight_id))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS flight_inventory (flight_id TEXT NOT NULL, item TEXT NOT NULL, name TEXT NOT NULL, category TEXT NOT NULL, stock INTEGER NOT NULL CHECK(stock>=0), capacity INTEGER NOT NULL CHECK(capacity>=stock), alternative TEXT, allergens_json TEXT NOT NULL, dietary_json TEXT NOT NULL, PRIMARY KEY(flight_id,item))"
    )


def import_aircraft(payload):
    profile = AircraftProfile.model_validate(payload)
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO aircraft(aircraft_id,name,layout_json) VALUES(?,?,?) ON CONFLICT(aircraft_id) DO UPDATE SET name=excluded.name,layout_json=excluded.layout_json",
            (profile.aircraft_id, profile.name, profile.model_dump_json()),
        )
    return profile


def configure_flight(flight_id, aircraft_id, origin, destination):
    import re

    if not re.fullmatch(r"[A-Za-z0-9_-]{2,40}", flight_id) or not all(
        re.fullmatch(r"[A-Z]{3}", code) for code in [origin, destination]
    ):
        raise ValueError("Use a valid flight ID and three-letter airport codes")
    with get_connection() as conn:
        row = conn.execute(
            "SELECT layout_json FROM aircraft WHERE aircraft_id=?", (aircraft_id,)
        ).fetchone()
        if not row:
            raise ValueError("Provision the aircraft layout first")
        # The layout is a flight snapshot; updating a fleet template cannot move occupied seats.
        if conn.execute(
            "SELECT 1 FROM flights WHERE flight_id=?", (flight_id,)
        ).fetchone():
            raise ValueError(
                "Flight already exists; create a new flight instance instead of replacing its manifest"
            )
        conn.execute(
            "INSERT INTO flights(flight_id,aircraft_id,origin,destination,layout_json) VALUES(?,?,?,?,?)",
            (flight_id, aircraft_id, origin, destination, row["layout_json"]),
        )
        for key, value in {
            "flight_phase": "boarding",
            "seatbelt_sign": True,
            "meal_service_active": False,
            "minutes_to_landing": 0,
        }.items():
            conn.execute(
                "INSERT INTO flight_context(flight_id,key,value) VALUES(?,?,?)",
                (flight_id, key, str(value)),
            )


def profile_for_flight(flight_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM flights WHERE flight_id=?", (flight_id,)
        ).fetchone()
    if not row or row["state"] != "active":
        raise HTTPException(
            status_code=409, detail="Flight is not configured or is closed"
        )
    layout = json.loads(row["layout_json"])
    return {
        "flight_id": flight_id,
        "aircraft_id": row["aircraft_id"],
        "aircraft_name": layout["name"],
        "origin": row["origin"],
        "destination": row["destination"],
        "rows": layout["rows"],
        "seat_count": sum(len("".join(r["blocks"])) for r in layout["rows"]),
    }


def configured_seat(flight_id, seat):
    profile = profile_for_flight(flight_id)
    for row in profile["rows"]:
        if seat in [str(row["row"]) + letter for letter in "".join(row["blocks"])]:
            return {"seat": seat, "zone": row["zone"], "cabin": row["cabin"]}
    raise HTTPException(
        status_code=422, detail="Seat does not exist in this flight's aircraft layout"
    )


def load_stock(flight_id, items):
    profile_for_flight(flight_id)
    parsed = [StockItem.model_validate(item) for item in items]
    if (
        not parsed
        or len(parsed) > 100
        or len({row.item for row in parsed}) != len(parsed)
    ):
        raise ValueError("Supply 1–100 unique stock items")
    names = {row.item for row in parsed}
    if any(row.alternative and row.alternative not in names for row in parsed):
        raise ValueError("Alternatives must exist in the same loading manifest")
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        if conn.execute(
            "SELECT 1 FROM tasks WHERE flight_id=? LIMIT 1", (flight_id,)
        ).fetchone():
            raise ValueError(
                "Initial loading is locked after service requests exist; use audited restocking"
            )
        conn.execute("DELETE FROM flight_inventory WHERE flight_id=?", (flight_id,))
        conn.executemany(
            "INSERT INTO flight_inventory(flight_id,item,name,category,stock,capacity,alternative,allergens_json,dietary_json) VALUES(?,?,?,?,?,?,?,?,?)",
            [
                (
                    flight_id,
                    r.item,
                    r.name,
                    r.category,
                    r.stock,
                    r.capacity,
                    r.alternative,
                    json.dumps(r.allergens),
                    json.dumps(r.dietary_tags),
                )
                for r in parsed
            ],
        )


def assigned_flights(username):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT f.flight_id FROM flights f JOIN crew_assignments c ON c.flight_id=f.flight_id WHERE c.username=? AND f.state='active' ORDER BY f.flight_id",
            (username,),
        ).fetchall()
    return [row["flight_id"] for row in rows]
