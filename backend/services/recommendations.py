"""Explainable cold-start ranking and exact, bounded playlist packing.

Metadata TF-IDF cosine relevance + explicit mood + duration fit; greedy MMR
reduces repeated genres. No learned engagement or medical inference is claimed.
"""

import json
import math
import re
from collections import Counter
from functools import lru_cache
from backend.config import CATALOG_PATH, MEDIA_DIR
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator

INTERESTS = {"science", "travel", "art", "music", "calm", "learning", "culture"}


class ContentItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")
    title: str = Field(min_length=1, max_length=120)
    kind: Literal["video", "audio"]
    genre: str = Field(min_length=1, max_length=40)
    duration_seconds: int = Field(ge=1, le=10800)
    mood: Literal["slow", "curious", "energetic"]
    tags: list[str] = Field(min_length=1, max_length=20)
    description: str = Field(min_length=1, max_length=500)
    language: str = Field(pattern=r"^[a-z]{2}$")
    captions: bool
    family_safe: bool
    asset: str = Field(pattern=r"^[a-z0-9_-]+\.(webm|mp4|ogg|flac|wav)$")
    poster: str = Field(pattern=r"^[a-z0-9_-]+\.(svg|png|webp|jpg)$")
    caption_asset: str | None = Field(None, pattern=r"^[a-z0-9_-]+\.vtt$")
    license: str = Field(min_length=1, max_length=100)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def captions_consistent(self):
        if self.kind == "video" and self.captions and not self.caption_asset:
            raise ValueError("Captioned video requires a local caption asset")
        if any(len(tag) > 40 for tag in self.tags):
            raise ValueError("Content tags are limited to 40 characters")
        return self


@lru_cache(maxsize=1)
def catalog():
    data = json.loads(CATALOG_PATH.read_text())
    items = [ContentItem.model_validate(item).model_dump() for item in data["items"]]
    if len(items) > 500 or len({item["id"] for item in items}) != len(items):
        raise ValueError("Use at most 500 titles with unique content IDs")
    return {
        "version": str(data["version"]),
        "provenance": str(data["provenance"]),
        "items": items,
    }


def public_item(item):
    return {
        key: value
        for key, value in item.items()
        if key not in {"asset", "poster", "caption_asset", "sha256"}
    } | {
        "media_url": f"/api/experience/media/{item['asset']}",
        "poster_url": f"/api/experience/media/{item['poster']}",
        "captions_url": (
            f"/api/experience/media/{item['caption_asset']}"
            if item["caption_asset"]
            else None
        ),
    }


def tokens(text):
    return re.findall(r"[a-z]+", text.lower())


def cosine(a, b):
    norm = math.sqrt(sum(x * x for x in a.values()) * sum(x * x for x in b.values()))
    return sum(value * b.get(key, 0) for key, value in a.items()) / norm if norm else 0


def rank(preferences, budget_seconds):
    items = [item for item in catalog()["items"] if item["family_safe"]]
    documents = [
        Counter(
            tokens(
                " ".join(
                    [item["title"], item["description"], item["genre"], *item["tags"]]
                )
            )
        )
        for item in items
    ]
    df = Counter(word for document in documents for word in document)
    idf = {
        word: math.log((len(items) + 1) / (count + 1)) + 1 for word, count in df.items()
    }
    vectors = [
        {word: (1 + math.log(count)) * idf[word] for word, count in document.items()}
        for document in documents
    ]
    query = {word: idf.get(word, 1) for word in preferences.interests}
    candidates = []
    for item, vector in zip(items, vectors):
        if item["id"] in preferences.exclude_ids or (
            preferences.captions_required
            and item["kind"] == "video"
            and not item["captions"]
        ):
            continue
        if preferences.kind != "all" and item["kind"] != preferences.kind:
            continue
        # A hard budget filter, not a label on a title that cannot finish.
        if item["duration_seconds"] > budget_seconds:
            continue
        relevance = cosine(query, vector)
        mood_match = preferences.mood == item["mood"]
        score = 0.6 * relevance + 0.2 * mood_match + 0.2
        overlap = sorted(set(preferences.interests) & set(item["tags"]))
        reasons = []
        if overlap:
            reasons.append("Matches " + ", ".join(overlap))
        if mood_match:
            reasons.append("A " + preferences.mood + " pace")
        reasons.append("Finishes within your available time")
        candidates.append(
            {"item": item, "score": score, "vector": vector, "reasons": reasons}
        )
    selected = []
    while candidates and len(selected) < preferences.limit:

        def marginal(candidate):
            similarity = max(
                (cosine(candidate["vector"], row["vector"]) for row in selected),
                default=0,
            )
            return 0.8 * candidate["score"] - 0.2 * similarity

        chosen = max(candidates, key=lambda row: (marginal(row), row["item"]["id"]))
        chosen["diversity_score"] = marginal(chosen)
        selected.append(chosen)
        candidates.remove(chosen)
    return [
        public_item(row["item"])
        | {"score": round(row["score"], 4), "reasons": row["reasons"]}
        for row in selected
    ]


def pack_plan(ranked, budget_seconds):
    """Exact 0/1 dynamic program, <=4 titles and 15-second transitions."""
    states = {(0, 0): (0.0, [])}
    for item in ranked[:8]:
        for (used, count), (value, sequence) in list(states.items()):
            cost = item["duration_seconds"] + (15 if count else 0)
            key = (used + cost, count + 1)
            if key[0] <= budget_seconds and key[1] <= 4:
                proposed = value + item["score"] + 0.1
                if proposed > states.get(key, (-1, []))[0]:
                    states[key] = (proposed, [*sequence, item])
    (used, _), (_, sequence) = max(
        states.items(), key=lambda row: (row[1][0], -row[0][0])
    )
    return {
        "items": sequence,
        "total_seconds": used,
        "remaining_seconds": budget_seconds - used,
        "transition_seconds": 15,
    }


def integrity_report():
    import hashlib

    items = catalog()["items"]
    errors = []
    for item in items:
        asset = MEDIA_DIR / item["asset"]
        if (
            not asset.is_file()
            or hashlib.sha256(asset.read_bytes()).hexdigest() != item["sha256"]
        ):
            errors.append(item["id"])
        for name in [item["poster"], item["caption_asset"]]:
            if name and not (MEDIA_DIR / name).is_file():
                errors.append(item["id"])
    return {
        "catalog_version": catalog()["version"],
        "titles": len(items),
        "verified": not errors,
        "invalid_titles": sorted(set(errors)),
    }
