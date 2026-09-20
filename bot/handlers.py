"""Telegram command and URL handlers for the Colabvid pipeline."""

from __future__ import annotations

import asyncio
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from telethon import events

from bot.messages import HELP_MESSAGE, START_MESSAGE
from core.full_pipeline import run_full_pipeline
from services.jobs import JobManager
from services.telegram_progress import TelegramProgressReporter


DEFAULT_CLIP_DURATION = 60.0
DEFAULT_CLIP_COUNT = 5


def register_handlers(client, *, channel_id: int, job_manager: JobManager) -> None:
    """Register Telegram handlers using the authenticated Telethon client."""

    @client.on(events.NewMessage(pattern=r"^/start$"))
    async def start_handler(event):
        await event.respond(START_MESSAGE, parse_mode="md")

    @client.on(events.NewMessage(pattern=r"^/help$"))
    async def help_handler(event):
        await event.respond(HELP_MESSAGE, parse_mode="md")

    @client.on(events.NewMessage(func=lambda event: bool(event.raw_text)))
    async def text_handler(event):
        text = event.raw_text.strip()
        if text.startswith("/"):
            return
        if not text.startswith(("http://", "https://")):
            return

        await _start_url_job(
            event,
            client=client,
            channel_id=channel_id,
            job_manager=job_manager,
            source_url=text,
        )


async def _start_url_job(event, *, client, channel_id: int, job_manager: JobManager, source_url: str) -> None:
    """Start one URL job and keep all progress in one Telegram message."""
    job_id = uuid4().hex[:12]
    parsed_name = Path(urlparse(source_url).path).name or f"video_{job_id}"
    file_name = Path(parsed_name).stem[:80] or f"video_{job_id}"

    reporter = TelegramProgressReporter(event)
    await reporter.start(file_name=file_name, total=DEFAULT_CLIP_COUNT)
    loop = asyncio.get_running_loop()
    callback = TelegramProgressReporter.callback(reporter, loop)

    job_manager.create(
        job_id,
        source_url,
        filename=file_name,
        clip_duration=DEFAULT_CLIP_DURATION,
        clip_count=DEFAULT_CLIP_COUNT,
    )

    try:
        await run_full_pipeline(
            client=client,
            channel=channel_id,
            job_manager=job_manager,
            job_id=job_id,
            source_url=source_url,
            download_path=f"/content/colabvid/downloads/{job_id}.mp4",
            output_dir=f"/content/colabvid/outputs/{job_id}",
            clip_duration=DEFAULT_CLIP_DURATION,
            clip_count=DEFAULT_CLIP_COUNT,
            progress_callback=callback,
            caption_template=f"🎬 {file_name} · Clip {{index}}/{{total}}",
        )
        await reporter.finish({"stage": "completed"})
    except Exception as exc:
        await reporter.finish({"stage": "failed", "error": str(exc)})
