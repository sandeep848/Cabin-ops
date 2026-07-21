import asyncio
import threading
from typing import Set, Any

class EventManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._queues: Set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        """Register a new subscriber queue."""
        queue = asyncio.Queue()
        with self._lock:
            self._queues.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Remove a subscriber queue."""
        with self._lock:
            self._queues.discard(queue)

    async def broadcast(self, message: Any) -> None:
        """Broadcast a message to all active queues."""
        with self._lock:
            active_queues = list(self._queues)
        
        for queue in active_queues:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                pass
            except Exception:
                pass

event_manager = EventManager()
