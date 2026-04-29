from __future__ import annotations

import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any


def get_logger(name: str) -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    return logging.getLogger(name)


def timed(fn: Callable) -> Callable:
    @wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        t0 = time.monotonic()
        result = await fn(*args, **kwargs)
        elapsed = time.monotonic() - t0
        get_logger(fn.__module__).debug("%s completed in %.3fs", fn.__name__, elapsed)
        return result

    return wrapper
