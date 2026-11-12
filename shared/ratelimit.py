"""In-process sliding-window limits. Each service runs as one process (see docker-compose)."""

from collections import deque
from threading import Lock
import time


class SlidingWindow:
    """Count events per key. Memory stays bounded however many distinct keys appear."""

    def __init__(self, limit, seconds, max_keys=20_000):
        self.limit, self.seconds, self.max_keys = limit, seconds, max_keys
        self._events, self._lock = {}, Lock()

    def _active(self, key, now):
        events = self._events.get(key)
        if events is None:
            return None
        while events and events[0] <= now - self.seconds:
            events.popleft()
        if not events:
            del self._events[key]
            return None
        return events

    def _add(self, key, now, events):
        if events is None:
            if len(self._events) >= self.max_keys:
                for existing in list(self._events):
                    self._active(existing, now)
                while len(self._events) >= self.max_keys:
                    del self._events[next(iter(self._events))]
            events = self._events[key] = deque()
        events.append(now)

    def exceeded(self, key):
        with self._lock:
            events = self._active(key, time.monotonic())
            return events is not None and len(events) >= self.limit

    def record(self, key):
        with self._lock:
            now = time.monotonic()
            self._add(key, now, self._active(key, now))

    def hit(self, key):
        """Count one event atomically; False when the key has reached its limit."""
        with self._lock:
            now = time.monotonic()
            events = self._active(key, now)
            if events is not None and len(events) >= self.limit:
                return False
            self._add(key, now, events)
            return True

    def clear(self, key):
        with self._lock:
            self._events.pop(key, None)
