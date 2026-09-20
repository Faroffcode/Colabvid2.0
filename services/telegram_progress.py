"""Single-message Telegram progress reporting for the Colabvid pipeline."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from telethon.errors import MessageNotModifiedError

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
        self._completed_upload_clips: set[int] = set()
        self._transfer_samples: dict[str, tuple[int, float]] = {}
        self._last_text = ""

    async def start(self, *, file_name: str, total: int = 0) -> Any:
        """Create the only status message used by this reporter."""
        self.progress.file_name = file_name
        self.progress.total = total
        text = format_pipeline_status(self.progress)
        self.message = await self.event.respond(text, parse_mode="md")
        self._last_text = text
        self._last_render = time.monotonic()
        return self.message

    def callback(self, loop: Any | None = None):
        """Return the async progress callback expected by the pipeline."""

        async def _callback(payload: dict[str, Any]) -> None:
            await self.update(payload)

        return _callback

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

            text = format_pipeline_status(self.progress)
            if text == self._last_text:
                self._last_render = now
                return

            try:
                await self.message.edit(text, parse_mode="md")
            except MessageNotModifiedError:
                pass
            self._last_text = text
            self._last_render = now

    async def finish(self, payload: dict[str, Any] | None = None) -> None:
        """Apply a final event and force the final status message edit."""
        if payload:
            self._apply_payload(payload)
        await self.update({}, force=True)

    def _apply_payload(self, payload: dict[str, Any]) -> None:
        stage = str(payload.get("stage", ""))
        status = str(payload.get("status", ""))
        now = time.monotonic()

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
            self.progress.download_speed = _speed_text(
                self._transfer_samples, "download", downloaded, now
            )

        elif stage == "encoding":
            clip = payload.get("clip")
            total_clips = payload.get("total_clips") or self.progress.total
            start = payload.get("start_seconds")
            duration = payload.get("duration_seconds", 0)

            # The renderer supplies the clip's start and duration but not its
            # index. Derive the index so the unified status never shows '-'.
            if clip is None and start is not None and duration:
                try:
                    clip = int(float(start) / float(duration)) + 1
                except (TypeError, ValueError, ZeroDivisionError):
                    clip = None

            if clip is not None:
                self.progress.encoding_clip = f"{clip}/{total_clips or '-'}"

            if start is not None:
                self.progress.encoding_range = f"{start}s → {float(start) + float(duration)}s"

            if payload.get("percent") is not None:
                self.progress.encoding_percent = max(
                    0, min(100, round(float(payload["percent"])))
                )

        elif stage == "uploading":
            path = str(payload.get("path", ""))
            if path:
                self.progress.uploading_clip = path.rsplit("/", 1)[-1]
            if payload.get("percent") is not None:
                self.progress.upload_percent = round(float(payload["percent"]))
            if payload.get("sent_bytes") is not None:
                self.progress.upload_speed = _speed_text(
                    self._transfer_samples,
                    "upload",
                    int(payload.get("sent_bytes") or 0),
                    now,
                )
            if status == "complete":
                clip = payload.get("clip")
                if clip is not None:
                    clip_number = int(clip)
                    if clip_number not in self._completed_upload_clips:
                        self._completed_upload_clips.add(clip_number)
                        self.progress.completed = min(
                            self.progress.total, self.progress.completed + 1
                        )
                else:
                    self.progress.completed = min(
                        self.progress.total, self.progress.completed + 1
                    )

        if payload.get("retries") is not None:
            self.progress.retries = int(payload["retries"])
        if payload.get("error"):
            self.progress.error = str(payload["error"])


def _speed_text(
    samples: dict[str, tuple[int, float]],
    key: str,
    current_bytes: int,
    now: float,
) -> str:
    """Calculate transfer speed from consecutive progress samples."""
    previous = samples.get(key)
    samples[key] = (current_bytes, now)
    if previous is None:
        return "-"
    previous_bytes, previous_time = previous
    elapsed = now - previous_time
    if elapsed <= 0 or current_bytes < previous_bytes:
        return "-"
    return f"{(current_bytes - previous_bytes) / elapsed / 1024 / 1024:.2f} MB/s"


def _size(value: int) -> str:
    """Format bytes using a compact binary unit."""
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{value} B"
