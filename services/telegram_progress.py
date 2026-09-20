"""Single-message Telegram progress reporting for the Colabvid pipeline."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from services.progress import PipelineProgress, format_pipeline_status


class TelegramProgressReporter:
    """Own exactly one Telegram status message for a pipeline job."""

    def __init__(self, event: Any, *, min_interval: float = 1.0) -> None:
        self.event = event
        self.min_interval = max(0.0, min_interval)
        self.progress = PipelineProgress()
        self.message: Any | None = None
        self._last_render = 0.0
        self._lock = asyncio.Lock()

    async def start(self, *, file_name: str, total: int = 0) -> Any:
        """Create the only status message used by this reporter."""
        self.progress.file_name = file_name
        self.progress.total = total
        self.message = await self.event.respond(
            format_pipeline_status(self.progress),
            parse_mode="md",
        )
        self._last_render = time.monotonic()
        return self.message

    async def update(self, payload: dict[str, Any], *, force: bool = False) -> None:
        """Apply an event payload and edit the existing status message."""
        if self.message is None:
            raise RuntimeError("Progress reporter has not been started")

        self._apply_payload(payload)
        now = time.monotonic()
        if not force and now - self._last_render < self.min_interval:
            return

        async with self._lock:
            now = time.monotonic()
            if not force and now - self._last_render < self.min_interval:
                return
            await self.message.edit(
                format_pipeline_status(self.progress),
                parse_mode="md",
            )
            self._last_render = now

    async def finish(self, payload: dict[str, Any] | None = None) -> None:
        """Apply a final event and force the final status message edit."""
        if payload:
            self._apply_payload(payload)
        await self.update({}, force=True)

    def _apply_payload(self, payload: dict[str, Any]) -> None:
        stage = str(payload.get("stage", ""))
        status = str(payload.get("status", ""))

        if stage == "downloading":
            downloaded = int(payload.get("downloaded_bytes") or 0)
            total = payload.get("total_bytes")
            if total:
                self.progress.download_percent = min(
                    100, round(downloaded * 100 / int(total))
                )
                self.progress.download_size = (
                    f"{_size(downloaded)} / {_size(int(total))}"
                )
            else:
                self.progress.download_size = f"{_size(downloaded)} / ?"

        elif stage == "encoding":
            clip = payload.get("clip")
            total_clips = payload.get("total_clips")
            if clip is not None:
                self.progress.encoding_clip = (
                    f"{clip}/{total_clips or self.progress.total}"
                )
            if payload.get("start_seconds") is not None:
                start = payload["start_seconds"]
                duration = payload.get("duration_seconds", 0)
                self.progress.encoding_range = f"{start}s → {start + duration}s"
            if status == "complete" and clip and total_clips:
                self.progress.encoding_percent = round(
                    int(clip) * 100 / int(total_clips)
                )

        elif stage == "uploading":
            path = str(payload.get("path", ""))
            if path:
                self.progress.uploading_clip = path.rsplit("/", 1)[-1]
            if payload.get("percent") is not None:
                self.progress.upload_percent = round(float(payload["percent"]))
            if status == "complete":
                self.progress.completed = min(
                    self.progress.total, self.progress.completed + 1
                )

        if payload.get("retries") is not None:
            self.progress.retries = int(payload["retries"])
        if payload.get("error"):
            self.progress.error = str(payload["error"])


def _size(value: int) -> str:
    """Format bytes using a compact binary unit."""
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{value} B"
