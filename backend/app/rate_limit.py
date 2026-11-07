import time
from collections import defaultdict, deque
from threading import Lock

class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._windows: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            window = self._windows[key]
            while window and now - window[0] > self.window_seconds:
                window.popleft()
            if len(window) >= self.limit:
                return False
            window.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._windows.clear()


class RedisSlidingWindowLimiter:
    """Distributed sliding-window limiter for deployments with a Redis service."""

    _SCRIPT = """
    redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', tonumber(ARGV[1]) - tonumber(ARGV[2]))
    local current = redis.call('ZCARD', KEYS[1])
    if current >= tonumber(ARGV[3]) then
        return 0
    end
    redis.call('ZADD', KEYS[1], ARGV[1], ARGV[4])
    redis.call('PEXPIRE', KEYS[1], ARGV[2])
    return 1
    """

    def __init__(self, url: str, limit: int, window_seconds: int = 60):
        from redis import Redis

        self.client = Redis.from_url(
            url,
            socket_connect_timeout=2,
            socket_timeout=2,
            health_check_interval=30,
        )
        self.limit = limit
        self.window_ms = window_seconds * 1000
        self.script = self.client.register_script(self._SCRIPT)

    def allow(self, key: str) -> bool:
        import logging
        import time
        from uuid import uuid4

        try:
            now_ms = int(time.time() * 1000)
            return bool(self.script(
                keys=[f"scamshield:rate:{key}"],
                args=[now_ms, self.window_ms, self.limit, f"{now_ms}:{uuid4()}"],
            ))
        except Exception:
            logging.getLogger(__name__).exception("Redis rate limiter unavailable; rejecting request")
            return False

