"""Telegram upload helpers for rendered video clips."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Awaitable, Callable


ProgressCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


class UploadError(RuntimeError):
    """Raised when a Telegram upload cannot be completed."""


async def upload_clip(
    client: Any,
    channel: Any,
    clip_path: str | Path,
    *,
    caption: str | None = None,
    progress_callback: ProgressCallback | None = None,
    retries: int = 2,
) -> Any:
    """Upload one clip to Telegram with retry support."""
    path = Path(clip_path)
    if not path.is_file():
        raise UploadError(f"Clip does not exist: {path}")
    if retries < 0:
        raise ValueError("retries cannot be negative")

    async def notify(payload: dict[str, Any]) -> None:
        if progress_callback:
            result = progress_callback(payload)
            if result is not None:
                await result

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            await notify({"stage": "uploading", "status": "starting", "path": str(path), "attempt": attempt + 1})
            message = await client.send_file(
                channel,
                str(path),
                caption=caption,
                progress_callback=lambda sent, total: _notify_progress(
                    progress_callback, sent, total, path
                ),
            )
            await notify({"stage": "uploading", "status": "complete", "path": str(path)})
            return message
        except Exception as exc:
            last_error = exc
            await notify({"stage": "uploading", "status": "retry", "path": str(path), "attempt": attempt + 1, "error": str(exc)})

    raise UploadError(f"Upload failed for {path}: {last_error}") from last_error


def _notify_progress(
    callback: ProgressCallback | None,
    sent: int,
    total: int,
    path: Path,
) -> None:
    """Forward Telethon's synchronous progress callback safely."""
    if callback is None:
        return

    import asyncio

    payload = {
        "stage": "uploading",
        "status": "progress",
        "path": str(path),
        "sent_bytes": sent,
        "total_bytes": total,
        "percent": round((sent / total) * 100, 1) if total else 0,
    }
    result = callback(payload)
    if asyncio.iscoroutine(result):
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(result)
        except RuntimeError:
            result.close()
