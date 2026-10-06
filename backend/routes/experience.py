"""Passenger-domain API. Identity and object scope always come from signed claims."""

import hashlib
import os
import secrets
import time
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ConfigDict
from backend.security.dependencies import require_role, require_crew, authorized_flight
from backend.security.limiter import request_limiter
from backend.database.connection import get_connection
from backend.database.operations import get_db_flight_context
from backend.services.recommendations import (
    catalog,
    public_item,
    rank,
    pack_plan,
    integrity_report,
)
from backend.config import MEDIA_DIR

router = APIRouter(prefix="/experience", tags=["Passenger experience"])
passenger = require_role(["passenger"])


class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    interests: list[
        Literal["science", "travel", "art", "music", "calm", "learning", "culture"]
    ] = Field(default_factory=list, max_length=7)
    mood: Literal["any", "slow", "curious", "energetic"] = "any"
    kind: Literal["all", "video", "audio"] = "all"
    captions_required: bool = True
    available_minutes: int = Field(10, ge=0, le=180)
    exclude_ids: list[str] = Field(default_factory=list, max_length=32)
    limit: int = Field(8, ge=1, le=8)


class Progress(BaseModel):
    model_config = ConfigDict(extra="forbid")
    position_seconds: float = Field(ge=0, le=36000, allow_inf_nan=False)


class PlaybackState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: Literal["playing", "paused", "ended", "error"]
    content_id: str


def item_by_id(content_id):
    item = next((row for row in catalog()["items"] if row["id"] == content_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    return item


def budget(payload, token_data):
    context = get_db_flight_context(authorized_flight(token_data))
    remaining = context.get("minutes_to_landing", 0)
    return min(payload.available_minutes, max(0, remaining - 5)) * 60


@router.post("/media-session", dependencies=[Depends(request_limiter)])
def media_session(response: Response, token_data=Depends(passenger)):
    grant = secrets.token_urlsafe(32)
    now = int(time.time())
    with get_connection() as conn:
        conn.execute("DELETE FROM media_grants WHERE expires_at <= ?", (now,))
        conn.execute(
            "INSERT INTO media_grants (token_id, digest, expires_at) VALUES (?, ?, ?) ON CONFLICT(token_id) DO UPDATE SET digest=excluded.digest, expires_at=excluded.expires_at",
            (
                token_data["jti"],
                hashlib.sha256(grant.encode()).hexdigest(),
                min(now + 900, token_data["exp"]),
            ),
        )
    # Media-only opaque cookie: no bearer credential in URLs, no data API privilege.
    response.set_cookie(
        "atlas_media",
        grant,
        httponly=True,
        secure=os.getenv("ENV") == "production",
        samesite="strict",
        max_age=900,
        path="/",
    )
    return {"expires_in": 900}


@router.get("/media/{asset}")
def media_asset(asset: str, atlas_media: str | None = Cookie(None)):
    allowed = {
        name
        for item in catalog()["items"]
        if item["family_safe"]
        for name in [item["asset"], item["poster"], item["caption_asset"]]
        if name
    }
    if asset not in allowed:
        raise HTTPException(status_code=404, detail="Media asset not found")
    if not atlas_media or len(atlas_media) > 128:
        raise HTTPException(status_code=401, detail="Media session required")
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM media_grants g JOIN sessions s ON s.token_id=g.token_id WHERE g.digest = ? AND g.expires_at > ? AND s.expires_at > ?",
            (
                hashlib.sha256(atlas_media.encode()).hexdigest(),
                time.time(),
                time.time(),
            ),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Media session expired")
    path = MEDIA_DIR / asset
    if not path.is_file():
        raise HTTPException(status_code=503, detail="Local media is unavailable")
    types = {
        ".webm": "video/webm",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
        ".mp4": "video/mp4",
        ".wav": "audio/wav",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".webp": "image/webp",
        ".vtt": "text/vtt",
    }
    return FileResponse(
        path,
        media_type=types[path.suffix],
        headers={"Cache-Control": "private, no-store"},
    )


@router.get("/catalog")
def get_catalog(token_data=Depends(passenger)):
    return {
        "version": catalog()["version"],
        "provenance": catalog()["provenance"],
        "items": [
            public_item(item) for item in catalog()["items"] if item["family_safe"]
        ],
    }


@router.post("/recommendations", dependencies=[Depends(request_limiter)])
def recommendations(payload: Preferences, token_data=Depends(passenger)):
    seconds = budget(payload, token_data)
    return {
        "algorithm": "metadata-tfidf-mmr-v1",
        "budget_seconds": seconds,
        "landing_buffer_minutes": 5,
        "preference_storage": "not retained by server",
        "items": rank(payload, seconds),
    }


@router.post("/plan", dependencies=[Depends(request_limiter)])
def journey_plan(payload: Preferences, token_data=Depends(passenger)):
    seconds = budget(payload, token_data)
    # Rank all eligible items before exact budget optimisation.
    payload.limit = 8
    return {
        "budget_seconds": seconds,
        "landing_buffer_minutes": 5,
        **pack_plan(rank(payload, seconds), seconds),
    }


@router.get("/progress")
def get_progress(token_data=Depends(passenger)):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT content_id, position_seconds, updated_at FROM media_progress WHERE flight_id=? AND seat=?",
            (authorized_flight(token_data), token_data["seat"]),
        ).fetchall()
    return [dict(row) for row in rows]


@router.put("/progress/{content_id}", dependencies=[Depends(request_limiter)])
def save_progress(content_id: str, payload: Progress, token_data=Depends(passenger)):
    item = item_by_id(content_id)
    if payload.position_seconds > item["duration_seconds"]:
        raise HTTPException(status_code=422, detail="Position exceeds content duration")
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO media_progress (flight_id,seat,content_id,position_seconds) VALUES (?,?,?,?) ON CONFLICT(flight_id,seat,content_id) DO UPDATE SET position_seconds=excluded.position_seconds,updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')",
            (
                authorized_flight(token_data),
                token_data["seat"],
                content_id,
                payload.position_seconds,
            ),
        )
    return {"status": "saved"}


@router.delete("/history")
def forget_history(token_data=Depends(passenger)):
    with get_connection() as conn:
        for table in ["media_progress", "playback_health"]:
            conn.execute(
                f"DELETE FROM {table} WHERE flight_id=? AND seat=?",
                (authorized_flight(token_data), token_data["seat"]),
            )
    return {"status": "forgotten"}


@router.post("/playback-health", dependencies=[Depends(request_limiter)])
def playback_health(payload: PlaybackState, token_data=Depends(passenger)):
    item_by_id(payload.content_id)
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO playback_health (flight_id,seat,state,content_id) VALUES (?,?,?,?) ON CONFLICT(flight_id,seat) DO UPDATE SET state=excluded.state,content_id=excluded.content_id,updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')",
            (
                authorized_flight(token_data),
                token_data["seat"],
                payload.state,
                payload.content_id,
            ),
        )
    return {"status": "recorded"}


@router.get("/diagnostics")
def diagnostics(token_data=Depends(require_crew)):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT state,COUNT(*) AS count FROM playback_health WHERE flight_id=? AND updated_at >= strftime('%Y-%m-%dT%H:%M:%fZ','now','-2 minutes') GROUP BY state",
            (authorized_flight(token_data),),
        ).fetchall()
    # Aggregate device health only. No passenger taste or watched titles in crew UI.
    return {
        "local_media": integrity_report(),
        "recent_terminals": {row["state"]: row["count"] for row in rows},
        "window_seconds": 120,
        "source": "browser-reported, not hardware telemetry",
    }


@router.get("/menu")
def onboard_menu(token_data=Depends(passenger)):
    from backend.database.operations import get_inventory_levels

    rows = get_inventory_levels(authorized_flight(token_data))
    return [
        {
            key: row[key]
            for key in [
                "item",
                "name",
                "category",
                "stock",
                "allergens",
                "dietary_tags",
            ]
        }
        for row in rows
    ]
