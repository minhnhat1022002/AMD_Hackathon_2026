from __future__ import annotations

import asyncio
import contextvars
import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


_BROWSER_EXECUTOR = ThreadPoolExecutor(
    max_workers=_env_int("OTA_BROWSER_THREAD_WORKERS", 4),
    thread_name_prefix="ota-crawl-browser",
)


async def run_in_clean_thread(
    func: Callable[P, T],
    /,
    *args: P.args,
    **kwargs: P.kwargs,
) -> T:
    """Run sync browser code in an executor without inheriting async contextvars."""
    loop = asyncio.get_running_loop()
    context = contextvars.Context()
    return await loop.run_in_executor(
        _BROWSER_EXECUTOR,
        context.run,
        partial(func, *args, **kwargs),
    )
