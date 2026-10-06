"""Bounded per-principal throttling; shared cabin NAT cannot merge all passengers."""

import threading
import time
from collections import defaultdict
from fastapi import HTTPException, Request
from backend.security.tokens import verify_token


class RateLimiter:
    def __init__(self, requests_limit, window_seconds):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self.history = defaultdict(list)
        self.lock = threading.Lock()
        self.last_cleanup = 0

    async def __call__(self, request: Request):
        ip = request.client.host if request.client else "unknown"
        credential = request.headers.get("authorization", "")
        claims = (
            verify_token(credential[7:])
            if credential.lower().startswith("bearer ")
            else None
        )
        if claims:
            identity = (
                "crew:" + claims.get("username", "crew")
                if claims["role"] == "crew"
                else claims["flight_id"] + ":" + claims["seat"]
            )
        elif request.url.path in {"/auth/crew", "/auth/passenger"}:
            try:
                body = await request.json()
            except ValueError:
                body = {}
            name = (
                str(
                    body.get("username")
                    or str(body.get("flight_id", "")) + ":" + str(body.get("seat", ""))
                )[:120]
                if isinstance(body, dict)
                else "invalid"
            )
            identity = "login:" + name.lower()
        else:
            identity = "ip:" + ip
        key = identity + ":" + request.url.path
        now = time.monotonic()
        with self.lock:
            if now - self.last_cleanup > 30 or len(self.history) >= 10000:
                self.history = {
                    k: [t for t in values if now - t < self.window_seconds]
                    for k, values in self.history.items()
                    if values and now - values[-1] < self.window_seconds
                }
                self.last_cleanup = now
            if request.url.path in {"/auth/crew", "/auth/passenger"}:
                ip_key = "login-ip:" + ip
                attempts = [
                    t
                    for t in self.history.get(ip_key, [])
                    if now - t < self.window_seconds
                ]
                if len(attempts) >= 1000:
                    raise HTTPException(
                        status_code=429,
                        detail="Login rate exceeded",
                        headers={"Retry-After": str(self.window_seconds)},
                    )
                self.history[ip_key] = [*attempts, now]
            values = [
                t for t in self.history.get(key, []) if now - t < self.window_seconds
            ]
            if len(values) >= self.requests_limit or (
                key not in self.history and len(self.history) >= 10000
            ):
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests. Please try again later.",
                    headers={"Retry-After": str(self.window_seconds)},
                )
            self.history[key] = [*values, now]


auth_limiter = RateLimiter(10, 60)
request_limiter = RateLimiter(30, 60)
