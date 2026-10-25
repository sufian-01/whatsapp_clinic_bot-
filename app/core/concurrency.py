"""Concurrency and thread serialization utilities for WhatsApp channel."""

import asyncio
from collections import OrderedDict
import logging
import threading
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class PerThreadLockManager:
    """Manages per-thread asyncio locks to serialize concurrent messages from the same patient.
    
    Prevents race conditions where two rapid WhatsApp messages from the same user
    execute LangGraph concurrently and overwrite checkpoint state.
    Different threads (different patients or different clinics) run concurrently.
    """

    def __init__(self, max_locks: int = 1000) -> None:
        self._locks: OrderedDict[str, Tuple[asyncio.Lock, asyncio.AbstractEventLoop]] = OrderedDict()
        self._mutex = threading.Lock()
        self._max_locks = max_locks

    async def get_lock(self, thread_id: str) -> asyncio.Lock:
        clean_id = (thread_id or "default").strip()
        current_loop = asyncio.get_running_loop()

        with self._mutex:
            if clean_id in self._locks:
                lock, loop = self._locks[clean_id]
                if loop is current_loop and not loop.is_closed():
                    self._locks.move_to_end(clean_id)
                    return lock

            # Prune oldest if at capacity
            if len(self._locks) >= self._max_locks:
                self._locks.popitem(last=False)

            lock = asyncio.Lock()
            self._locks[clean_id] = (lock, current_loop)
            return lock


_GLOBAL_THREAD_LOCK_MANAGER: Optional[PerThreadLockManager] = None
_INIT_LOCK = threading.Lock()


def get_thread_lock_manager() -> PerThreadLockManager:
    global _GLOBAL_THREAD_LOCK_MANAGER
    if _GLOBAL_THREAD_LOCK_MANAGER is None:
        with _INIT_LOCK:
            if _GLOBAL_THREAD_LOCK_MANAGER is None:
                _GLOBAL_THREAD_LOCK_MANAGER = PerThreadLockManager()
    return _GLOBAL_THREAD_LOCK_MANAGER
