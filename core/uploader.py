"""Telegram upload helpers for rendered video clips."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Awaitable, Callable

from telethon.tl.types import DocumentAttributeVideo


ProgressCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


class UploadError(RuntimeError):
    """Raised when a Telegram upload cannot be completed."""


def _video_attributes(path: Path) -> DocumentAttributeVideo:
    """Read video metadata so Telegram receives duration and dimensions."""
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,duration",
        "-of",
        "json",
        str(path),
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
        )
        streams = json.loads(result.stdout).get("streams", [])
        if not streams:
            raise ValueError("No video stream found")
        stream = streams[0]
        width = int(stream.get("width") or 1080)
        height = int(stream.get("height") or 1920)
        duration = max(1, round(float(stream.get("duration") or 0)))
    except (OSError, ValueError, TypeError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        raise UploadError(f"Could not read video metadata for {path}: {exc}") from exc

    return DocumentAttributeVideo(
        duration=duration,
        w=width,
        h=height,
        supports_streaming=True,
    )


async def upload_clip(
    client: Any,
    channel: Any,
    clip_path: str | Path,
    *,
    caption: str | None = None,
    progress_callback: ProgressCallback | None = None,
    retries: int = 2,
) -> Any:
    """Upload one clip to Telegram with explicit video metadata and retry support."""
    path = Path(clip_path)
    if not path.is_file():
        raise UploadError(f"Clip does not exist: {path}")
    if retries < 0:
        raise ValueError("retries cannot be negative")

    attributes = _video_attributes(path)

    async def notify(payload: dict[str, Any]) -> None:
        if progress_callback:
            result = progress_callback(payload)
            if result is not None:
                await result

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            print(
                f"[UPLOAD] Starting clip={path.name} attempt={attempt + 1}/{retries + 1}",
                flush=True,
            )
            await notify({"stage": "uploading", "status": "starting", "path": str(path), "attempt": attempt + 1})
            message = await client.send_file(
                channel,
                str(path),
                caption=caption,
                force_document=False,
                supports_streaming=True,
                attributes=[attributes],
                progress_callback=lambda sent, total: _notify_progress(
                    progress_callback, sent, total, path
                ),
            )
            print(f"[UPLOAD] Complete: {path.name}", flush=True)
            await notify({"stage": "uploading", "status": "complete", "path": str(path)})
            return message
        except Exception as exc:
            last_error = exc
            print(
                f"[UPLOAD] FAILED clip={path.name} attempt={attempt + 1}: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )
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
    now = time.monotonic()
    last_log = getattr(_notify_progress, "_last_log", {})
    last_time, last_path = last_log.get(str(path), (0.0, 0))
    if now - last_time >= 1.0 or sent >= total:
        speed = (sent - last_path) / max(now - last_time, 0.001) if last_time else 0.0
        print(
            f"[UPLOAD] {path.name} | {payload['percent']:.1f}% | "
            f"{sent}/{total} bytes | speed={speed / 1024 / 1024:.2f} MB/s",
            flush=True,
        )
        last_log[str(path)] = (now, sent)
        _notify_progress._last_log = last_log

    result = callback(payload)
    if asyncio.iscoroutine(result):
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(result)
        except RuntimeError:
            result.close()
