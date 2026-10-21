"""Render & Cloud Platform Keep-Alive Anti-Sleep Service.

Automatically pings the application's public URL (/health) every 10 minutes
to prevent Render free tier (and similar serverless/PaaS providers) from spinning down
after 15 minutes of inactivity.
"""

import asyncio
from datetime import datetime, timezone
import logging
import os
from typing import Any, Dict, Optional
import httpx

logger = logging.getLogger("app.keep_alive")

_task: Optional[asyncio.Task] = None
_stats: Dict[str, Any] = {
    "enabled": False,
    "target_url": None,
    "interval_minutes": 10,
    "total_pings": 0,
    "successful_pings": 0,
    "last_ping_at": None,
    "last_status_code": None,
    "last_error": None,
}


def resolve_keep_alive_url() -> Optional[str]:
    """Resolve the external URL to ping from Render or user environment variables."""
    # 1. Explicit user override
    explicit_url = os.getenv("KEEP_ALIVE_URL", "").strip()
    if explicit_url:
        return explicit_url.rstrip("/")

    # 2. Render standard environment variables (auto-injected by Render platform)
    render_url = os.getenv("RENDER_EXTERNAL_URL", "").strip()
    if render_url:
        return render_url.rstrip("/")

    render_hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()
    if render_hostname:
        prefix = "https://" if not render_hostname.startswith("http") else ""
        return f"{prefix}{render_hostname}".rstrip("/")

    # 3. Local test fallback if explicitly enabled
    if os.getenv("KEEP_ALIVE_FORCE_LOCAL", "").casefold() in ("true", "1", "yes"):
        port = os.getenv("PORT", "8000")
        return f"http://127.0.0.1:{port}"

    return None


async def _ping_health(client: httpx.AsyncClient, target_url: str) -> None:
    """Send an async GET request to the /health endpoint to prevent cloud sleep."""
    health_url = f"{target_url}/health"
    _stats["total_pings"] += 1
    _stats["last_ping_at"] = datetime.now(timezone.utc).isoformat()

    try:
        response = await client.get(
            health_url,
            timeout=15.0,
            headers={"User-Agent": "Kodnexus-Render-KeepAlive/1.0"},
        )
        _stats["last_status_code"] = response.status_code
        _stats["last_error"] = None
        if response.status_code == 200:
            _stats["successful_pings"] += 1
            logger.info(
                "[KEEP-ALIVE] Ping sent to %s -> Status: %d OK (Render anti-sleep active)",
                health_url,
                response.status_code,
            )
        else:
            logger.warning(
                "[KEEP-ALIVE] Ping sent to %s -> Unexpected status: %d",
                health_url,
                response.status_code,
            )
    except Exception as exc:
        _stats["last_status_code"] = None
        _stats["last_error"] = str(exc)
        logger.warning(
            "[KEEP-ALIVE] Failed to ping %s: %s (will retry next interval)",
            health_url,
            exc,
        )


async def _keep_alive_loop(interval_seconds: int, target_url: str) -> None:
    """Background loop that periodically pings the public health endpoint."""
    logger.info(
        "[KEEP-ALIVE] Anti-sleep worker started. Pinging '%s/health' every %d seconds (%d minutes).",
        target_url,
        interval_seconds,
        interval_seconds // 60,
    )
    async with httpx.AsyncClient(follow_redirects=True) as client:
        # Initial small delay before first ping to allow server startup to complete
        await asyncio.sleep(10)
        while True:
            await _ping_health(client, target_url)
            await asyncio.sleep(interval_seconds)


def start_keep_alive() -> Optional[asyncio.Task]:
    """Start the background keep-alive task if target URL is resolved."""
    global _task, _stats

    # Allow disabling via env var if on paid 24/7 plan or local testing
    if os.getenv("KEEP_ALIVE_ENABLED", "true").casefold() in ("false", "0", "no"):
        logger.info("[KEEP-ALIVE] Keep-alive service disabled via KEEP_ALIVE_ENABLED=false.")
        return None

    target_url = resolve_keep_alive_url()
    try:
        interval_mins = int(os.getenv("KEEP_ALIVE_INTERVAL_MINUTES", "10"))
    except ValueError:
        interval_mins = 10
    interval_seconds = max(60, interval_mins * 60)

    _stats["enabled"] = bool(target_url)
    _stats["target_url"] = target_url
    _stats["interval_minutes"] = interval_mins

    if not target_url:
        logger.info(
            "[KEEP-ALIVE] No RENDER_EXTERNAL_URL or KEEP_ALIVE_URL found. "
            "Anti-sleep worker will remain dormant until configured."
        )
        return None

    if _task is not None and not _task.done():
        return _task

    _task = asyncio.create_task(_keep_alive_loop(interval_seconds, target_url))
    return _task


def stop_keep_alive() -> None:
    """Cancel and clean up the background keep-alive task."""
    global _task
    if _task is not None:
        _task.cancel()
        _task = None
        logger.info("[KEEP-ALIVE] Anti-sleep worker stopped.")


def get_keep_alive_stats() -> Dict[str, Any]:
    """Return runtime diagnostic statistics about the keep-alive service."""
    return dict(_stats)

