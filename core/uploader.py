"""Pyrogram-based Telegram upload helpers for rendered video clips."""

from __future__ import annotations

import asyncio
import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Awaitable, Callable

ProgressCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


class UploadError(RuntimeError):
    """Raised when a Telegram upload cannot be completed."""


def _video_metadata(path: Path) -> dict[str, int]:
    """Read video metadata for Pyrogram's send_video method."""
    command = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,duration", "-of", "json", str(path)]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        streams = json.loads(result.stdout).get("streams", [])
        if not streams:
            raise ValueError("No video stream found")
        stream = streams[0]
        return {
            "width": int(stream.get("width") or 1080),
            "height": int(stream.get("height") or 1920),
            "duration": max(1, round(float(stream.get("duration") or 0))),
        }
    except (OSError, ValueError, TypeError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        raise UploadError(f"Could not read video metadata for {path}: {exc}") from exc


def _create_thumbnail(video: Path, duration: int) -> Path:
    """Extract a JPEG thumbnail compatible with Telegram's thumbnail limits."""
    handle = tempfile.NamedTemporaryFile(prefix="colabvid_thumb_", suffix=".jpg", delete=False)
    thumb = Path(handle.name)
    handle.close()
    timestamp = min(max(duration // 10, 0), 5)
    command = [
        "ffmpeg", "-y", "-ss", str(timestamp), "-i", str(video),
        "-frames:v", "1", "-vf", "scale=320:320:force_original_aspect_ratio=decrease",
        "-q:v", "3", str(thumb),
    ]
    try:
        subprocess.run(command, capture_output=True, text=True, check=True)
        if not thumb.is_file() or thumb.stat().st_size == 0:
            raise UploadError("FFmpeg created an empty thumbnail")
        return thumb
    except (OSError, subprocess.CalledProcessError) as exc:
        thumb.unlink(missing_ok=True)
        raise UploadError(f"Could not create thumbnail for {video}: {exc}") from exc


async def upload_clip(client: Any, channel: Any, clip_path: str | Path, *, caption: str | None = None, progress_callback: ProgressCallback | None = None, retries: int = 2) -> Any:
    """Upload one video using Pyrogram, including a generated thumbnail."""
    path = Path(clip_path)
    if not path.is_file():
        raise UploadError(f"Clip does not exist: {path}")
    if retries < 0:
        raise ValueError("retries cannot be negative")

    metadata = _video_metadata(path)
    total_bytes = path.stat().st_size
    event_loop = asyncio.get_running_loop()

    async def notify(payload: dict[str, Any]) -> None:
        if progress_callback:
            result = progress_callback(payload)
            if result is not None:
                await result

    def dispatch(payload: dict[str, Any]) -> None:
        if progress_callback is None:
            return
        result = progress_callback(payload)
        if result is None:
            return
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run_coroutine_threadsafe(result, event_loop)
        elif running_loop is event_loop:
            running_loop.create_task(result)
        else:
            asyncio.run_coroutine_threadsafe(result, event_loop)

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        started = time.monotonic()
        last_report = 0.0
        last_sent = 0
        thumb: Path | None = None
        try:
            thumb = _create_thumbnail(path, metadata["duration"])

            def progress(current: int, total: int, *_: Any) -> None:
                nonlocal last_report, last_sent
                now = time.monotonic()
                if current < total and now - last_report < 0.75:
                    return
                elapsed = max(now - started, 0.001)
                speed = (current - last_sent) / max(now - last_report, 0.001) if last_report else current / elapsed
                last_report = now
                last_sent = current
                dispatch({
                    "stage": "uploading", "status": "progress", "path": str(path),
                    "sent_bytes": current, "total_bytes": total,
                    "percent": round(current * 100 / total, 1) if total else 0.0,
                    "speed_bytes": speed, "elapsed_seconds": elapsed,
                })

            print(f"[UPLOAD] Pyrogram starting clip={path.name} attempt={attempt + 1}/{retries + 1} thumbnail={thumb.name}", flush=True)
            await notify({"stage": "uploading", "status": "starting", "path": str(path), "attempt": attempt + 1})
            message = await client.send_video(
                chat_id=channel, video=str(path), thumb=str(thumb), caption=caption,
                duration=metadata["duration"], width=metadata["width"], height=metadata["height"],
                supports_streaming=True, progress=progress,
            )
            elapsed = max(time.monotonic() - started, 0.001)
            average_speed = total_bytes / elapsed
            print(f"[UPLOAD] Complete: {path.name} | elapsed={elapsed:.2f}s | average={average_speed / 1024 / 1024:.2f} MB/s", flush=True)
            await notify({"stage": "uploading", "status": "complete", "path": str(path), "elapsed_seconds": elapsed, "average_speed_bytes": average_speed})
            return message
        except Exception as exc:
            last_error = exc
            print(f"[UPLOAD] FAILED clip={path.name} attempt={attempt + 1}: {type(exc).__name__}: {exc}", flush=True)
            await notify({"stage": "uploading", "status": "retry", "path": str(path), "attempt": attempt + 1, "error": str(exc)})
        finally:
            if thumb is not None:
                thumb.unlink(missing_ok=True)

    raise UploadError(f"Upload failed for {path}: {last_error}") from last_error
