import logging
import threading
import random
import time
from collections import defaultdict
from fastapi import Request, HTTPException, status

logger = logging.getLogger("cabinops.security.limiter")

class RateLimiter:
    def __init__(self, requests_limit: int, window_seconds: int):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self.history = defaultdict(list)
        self.lock = threading.Lock()
        
    def __call__(self, request: Request):
        ip = "unknown"
        if request.client:
            ip = request.client.host
            
        path = request.url.path
        key = f"{ip}:{path}"
        
        now = time.time()
        with self.lock:
            # Clean up old timestamps for current key
            self.history[key] = [t for t in self.history[key] if now - t < self.window_seconds]
            
            # Periodically clean up other keys to prevent memory leak
            if random.random() < 0.01:
                keys_to_delete = []
                for k, timestamps in list(self.history.items()):
                    cleaned = [t for t in timestamps if now - t < self.window_seconds]
                    if not cleaned:
                        keys_to_delete.append(k)
                    else:
                        self.history[k] = cleaned
                for k in keys_to_delete:
                    self.history.pop(k, None)
            
            if len(self.history[key]) >= self.requests_limit:
                logger.warning(f"Rate limit exceeded for key={key}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later."
                )
            self.history[key].append(now)

auth_limiter = RateLimiter(requests_limit=10, window_seconds=60)
request_limiter = RateLimiter(requests_limit=20, window_seconds=60)
