"""Concurrency and thread serialization utilities for WhatsApp channel."""

import asyncio
from collections import OrderedDict
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PerThreadLockManager:
    """Manages per-thread asyncio locks to serialize concurrent messages from the same patient.
    
    Prevents race conditions where two rapid WhatsApp messages from the same user
    execute LangGraph concurrently and overwrite checkpoint state.
    Different threads (different patients or different clinics) run concurrently.
    """

    def __init__(self, max_locks: int = 1000) -> None:
        self._locks: OrderedDict[str, asyncio.Lock] = OrderedDict()
        self._global_lock = asyncio.Lock()
        self._max_locks = max_locks

    async def get_lock(self, thread_id: str) -> asyncio.Lock:
        clean_id = (thread_id or "default").strip()
        async with self._global_lock:
            if clean_id in self._locks:
                self._locks.move_to_end(clean_id)
                return self._locks[clean_id]

            # Prune oldest if at capacity
            if len(self._locks) >= self._max_locks:
                self._locks.popitem(last=False)

            lock = asyncio.Lock()
            self._locks[clean_id] = lock
            return lock


_GLOBAL_THREAD_LOCK_MANAGER: Optional[PerThreadLockManager] = None


def get_thread_lock_manager() -> PerThreadLockManager:
    global _GLOBAL_THREAD_LOCK_MANAGER
    if _GLOBAL_THREAD_LOCK_MANAGER is None:
        _GLOBAL_THREAD_LOCK_MANAGER = PerThreadLockManager()
    return _GLOBAL_THREAD_LOCK_MANAGER

