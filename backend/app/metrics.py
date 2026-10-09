"""In-process QA counters for the admin panel. Reset on restart; good enough for a 10–20 person beta.
Nothing here ever holds client text, prompts, keys or tokens."""

import threading
import time

_lock = threading.Lock()
_counters: dict[str, int] = {"model_errors": 0, "extraction_failures": 0, "synthesis_failures": 0, "rate_limited": 0}
_last: dict[str, dict] = {}
_usage: dict[str, int] = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}


def add_usage(prompt_tokens: int, completion_tokens: int) -> None:
    """Token accounting for cost estimates (QA panel). Counts only."""
    with _lock:
        _usage["calls"] += 1
        _usage["prompt_tokens"] += int(prompt_tokens or 0)
        _usage["completion_tokens"] += int(completion_tokens or 0)


def bump(name: str, detail: str | None = None) -> None:
    with _lock:
        _counters[name] = _counters.get(name, 0) + 1
        if detail is not None:
            _last[name] = {"at": time.time(), "detail": detail[:120]}


def snapshot() -> dict:
    with _lock:
        return {"counters": dict(_counters), "last": {k: dict(v) for k, v in _last.items()}, "usage": dict(_usage)}
