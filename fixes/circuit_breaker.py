"""
circuit_breaker.py — standalone circuit-breaker module for agent_office.
Drop into agent_office/core/ and import:
    from core.circuit_breaker import CircuitBreaker, cb
"""
import time
import threading
import logging

log = logging.getLogger("circuit_breaker")


class CircuitBreaker:
    """Thread-safe dead-endpoint registry with TTL expiry."""

    def __init__(self, default_ttl: int = 1800):
        self._dead: dict[str, float] = {}
        self._lock = threading.Lock()
        self.default_ttl = default_ttl

    def is_dead(self, name: str) -> bool:
        with self._lock:
            exp = self._dead.get(name)
            if exp is None:
                return False
            if time.time() < exp:
                return True
            del self._dead[name]
            log.info(f"[circuit] {name} — TTL истёк, снова активен")
            return False

    def mark_dead(self, name: str, ttl: int | None = None):
        ttl = ttl or self.default_ttl
        with self._lock:
            self._dead[name] = time.time() + ttl
        log.warning(f"[circuit] {name} → мёртвый на {ttl // 60} мин")

    def revive(self, name: str):
        with self._lock:
            self._dead.pop(name, None)
        log.info(f"[circuit] {name} — принудительно оживлён")

    def dead_list(self) -> list[str]:
        now = time.time()
        with self._lock:
            return [k for k, v in self._dead.items() if v > now]

    def alive_from(self, pool: list) -> list:
        """Filter a pool list, skipping dead entries.
        Pool entries are expected to have name as first element: (name, ...).
        """
        return [entry for entry in pool if not self.is_dead(entry[0])]

    def wrap_call(self, name: str, fn, dead_on=(404, 429, 503)):
        """
        Call fn(), auto-mark name dead on HTTP errors in dead_on codes.
        Returns fn()'s result or raises.
        Usage:
            result = cb.wrap_call("my-model", lambda: _openai_call(...))
        """
        import requests as _req
        try:
            return fn()
        except _req.HTTPError as e:
            code = e.response.status_code if e.response else 0
            if code in dead_on:
                self.mark_dead(name)
            raise
        except Exception:
            raise


# Module-level default instance — import and use directly
cb = CircuitBreaker(default_ttl=1800)
