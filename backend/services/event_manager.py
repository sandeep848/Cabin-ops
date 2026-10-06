"""Flight-scoped invalidation events; reconnecting clients reload authoritative state."""

import asyncio
import threading


class EventManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._queues = {}

    def subscribe(self, flight_id: str, principal: str = "") -> asyncio.Queue:
        queue = asyncio.Queue(maxsize=32)
        with self._lock:
            if (
                len(self._queues) >= 256
                or sum(1 for value in self._queues.values() if value[1] == principal)
                >= 2
            ):
                from fastapi import HTTPException

                raise HTTPException(
                    status_code=503,
                    detail="Live update capacity reached; polling remains available",
                )
            self._queues[queue] = (flight_id, principal)
        return queue

    def unsubscribe(self, queue):
        with self._lock:
            self._queues.pop(queue, None)

    async def broadcast(self, message):
        with self._lock:
            queues = [
                q
                for q, scope in self._queues.items()
                if message.get("flight_id") == scope[0]
            ]
        public = {key: value for key, value in message.items() if key != "flight_id"}
        for queue in queues:
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(public)


event_manager = EventManager()
