"""Telegram command and URL handlers for the Colabvid pipeline."""

from __future__ import annotations

import asyncio
import re
import subprocess
from typing import Any
from uuid import uuid4

from telethon import events

from bot.messages import HELP_MESSAGE, START_MESSAGE
from core.full_pipeline import run_full_pipeline
from services.jobs import JobManager
from services.telegram_progress import TelegramProgressReporter


DEFAULT_CLIP_DURATION = 60.0
DEFAULT_CLIP_COUNT = 5
MIN_CLIP_DURATION = 1.0
MAX_CLIP_DURATION = 3600.0
MIN_CLIP_COUNT = 1
MAX_CLIP_COUNT = 100


def register_handlers(
    client,
    *,
    upload_client,
    channel_id: int,
    job_manager: JobManager,
) -> None:
    """Register Telethon handlers while using Pyrogram for video uploads."""
    pending: dict[int, dict[str, Any]] = {}
    destination = {"channel_id": channel_id}

    @client.on(events.NewMessage(pattern=r"^/start$"))
    async def start_handler(event):
        await event.respond(START_MESSAGE, parse_mode="md")

    @client.on(events.NewMessage(pattern=r"^/help$"))
    async def help_handler(event):
        await event.respond(HELP_MESSAGE, parse_mode="md")

    @client.on(events.NewMessage(pattern=r"^/setchannel$"))
    async def set_channel_handler(event):
        conversation_key = event.chat_id or event.sender_id
        pending[conversation_key] = {"step": "channel_forward"}
        await event.respond(
            "📢 **Set upload destination**\n\n"
            "Forward any message from the destination channel to me.\n"
            "I will extract the channel ID automatically.\n\n"
            "Send `/cancel` to cancel."
        )

    @client.on(events.NewMessage(func=lambda event: bool(event.message and event.message.fwd_from)))
    async def forwarded_channel_handler(event):
        conversation_key = event.chat_id or event.sender_id
        setup = pending.get(conversation_key)
        if not setup or setup.get("step") != "channel_forward":
            return

        try:
            forward_header = event.message.fwd_from
            forward_peer = getattr(forward_header, "from_id", None)
            if forward_peer is None:
                forward_peer = getattr(forward_header, "saved_from_peer", None)

            if forward_peer is None:
                raise ValueError("The forwarded message does not contain a source channel")

            forwarded_chat = await client.get_entity(forward_peer)
            extracted_id = getattr(forwarded_chat, "id", None)
            title = getattr(forwarded_chat, "title", None) or getattr(
                forwarded_chat, "username", None
            ) or "Unknown channel"
            is_channel = bool(getattr(forwarded_chat, "broadcast", False))

            if extracted_id is None or not is_channel:
                await event.respond(
                    "⚠️ I could not identify a channel from that forwarded message. "
                    "Please forward a post directly from the destination channel."
                )
                return

            destination["channel_id"] = int(extracted_id)
            pending.pop(conversation_key, None)
            await event.respond(
                "✅ **Upload destination updated**\n\n"
                f"📢 Channel: `{title}`\n"
                f"🆔 Channel ID: `{destination['channel_id']}`\n\n"
                "Future uploads will use this destination."
            )
        except Exception as exc:
            await event.respond(
                "⚠️ Could not extract the channel ID from that forward.\n"
                f"`{exc}`"
            )

    @client.on(events.NewMessage(func=lambda event: bool(event.raw_text)))
    async def text_handler(event):
        text = event.raw_text.strip()
        conversation_key = event.chat_id or event.sender_id

        if text.lower() == "/cancel":
            if pending.pop(conversation_key, None) is not None:
                await event.respond("❌ Operation cancelled.")
            return

        if text.startswith("/"):
            return

        if text.startswith(("http://", "https://")):
            await event.respond("🔎 Detecting video information... Please wait.")
            metadata = await _detect_video_metadata(text)
            pending[conversation_key] = {
                "source_url": text,
                "step": "filename",
                "source_title": metadata.get("title"),
                "source_duration": metadata.get("duration"),
            }

            details = _format_video_metadata(metadata)
            await event.respond(
                "📝 **Custom file name**\n\n"
                f"{details}\n\n"
                "Send the name you want to use for this video.\n"
                "Example: `My Movie`\n\n"
                "Send `/cancel` to cancel."
            )
            return

        setup = pending.get(conversation_key)
        if setup is None:
            return

        step = setup["step"]

        if step == "filename":
            file_name = _clean_file_name(text)
            if not file_name:
                await event.respond("⚠️ Please send a valid file name.")
                return
            setup["file_name"] = file_name
            setup["step"] = "duration"
            source_duration = setup.get("source_duration")
            source_hint = (
                f"\nDetected source duration: `{_format_seconds(source_duration)}`\n"
                if source_duration is not None
                else "\n⚠️ Source duration could not be detected automatically.\n"
            )
            await event.respond(
                "⏱️ **Clip duration**\n\n"
                "How many seconds should each clip contain?\n"
                "Example: `60`\n"
                f"{source_hint}\n"
                f"Allowed range: {MIN_CLIP_DURATION:g}–{MAX_CLIP_DURATION:g} seconds."
            )
            return

        if step == "duration":
            duration = _parse_duration(text)
            if duration is None:
                await event.respond(
                    f"⚠️ Enter a number between {MIN_CLIP_DURATION:g} and "
                    f"{MAX_CLIP_DURATION:g} seconds. Example: `60`"
                )
                return
            setup["clip_duration"] = duration
            setup["step"] = "count"
            await event.respond(
                "🎞️ **Number of clips**\n\n"
                "How many clips should be created?\n"
                "Example: `5`\n\n"
                f"Allowed range: {MIN_CLIP_COUNT}–{MAX_CLIP_COUNT}."
            )
            return

        if step == "count":
            clip_count = _parse_clip_count(text)
            if clip_count is None:
                await event.respond(
                    f"⚠️ Enter a whole number between {MIN_CLIP_COUNT} and "
                    f"{MAX_CLIP_COUNT}. Example: `5`"
                )
                return

            setup["clip_count"] = clip_count
            pending.pop(conversation_key, None)
            await event.respond(
                "✅ **Video settings received**\n\n"
                f"📁 File: `{setup['file_name']}`\n"
                f"🎬 Source: `{_format_seconds(setup.get('source_duration'))}`\n"
                f"⏱️ Clip duration: `{setup['clip_duration']:g}s`\n"
                f"🎞️ Clips: `{clip_count}`\n\n"
                "🚀 Starting pipeline..."
            )
            await _start_url_job(
                event,
                client=client,
                upload_client=upload_client,
                channel_id=destination["channel_id"],
                job_manager=job_manager,
                source_url=setup["source_url"],
                file_name=setup["file_name"],
                clip_duration=setup["clip_duration"],
                clip_count=clip_count,
            )

    return None


async def _detect_video_metadata(url: str) -> dict[str, Any]:
    """Detect title and duration without downloading the complete video."""
    return await asyncio.to_thread(_detect_video_metadata_sync, url)


def _detect_video_metadata_sync(url: str) -> dict[str, Any]:
    """Use yt-dlp first, then ffprobe for direct media URLs."""
    result: dict[str, Any] = {"title": None, "duration": None}

    try:
        import yt_dlp

        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "extract_flat": False,
        }
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
        if info:
            result["title"] = info.get("title")
            duration = info.get("duration")
            if duration is not None:
                result["duration"] = float(duration)
    except Exception:
        pass

    if result["duration"] is None:
        try:
            completed = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=25,
                check=False,
            )
            value = completed.stdout.strip()
            if value:
                result["duration"] = float(value)
        except (OSError, ValueError, subprocess.SubprocessError):
            pass

    return result


def _format_video_metadata(metadata: dict[str, Any]) -> str:
    title = metadata.get("title") or "Unknown title"
    duration = _format_seconds(metadata.get("duration"))
    return f"🎬 Title: `{title[:120]}`\n⏱️ Duration: `{duration}`"


def _format_seconds(value: Any) -> str:
    if value is None:
        return "Unknown"
    try:
        total = max(0, int(round(float(value))))
    except (TypeError, ValueError):
        return "Unknown"
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


async def _start_url_job(
    event,
    *,
    client,
    upload_client,
    channel_id: int,
    job_manager: JobManager,
    source_url: str,
    file_name: str,
    clip_duration: float,
    clip_count: int,
) -> None:
    """Start one URL job with Telethon notifications and Pyrogram uploads."""
    job_id = uuid4().hex[:12]

    reporter = TelegramProgressReporter(event)
    await reporter.start(file_name=file_name, total=clip_count)
    loop = asyncio.get_running_loop()
    callback = reporter.callback(loop)

    job_manager.create(
        job_id,
        source_url,
        filename=file_name,
        clip_duration=clip_duration,
        clip_count=clip_count,
    )

    try:
        await run_full_pipeline(
            client=upload_client,
            channel=channel_id,
            job_manager=job_manager,
            job_id=job_id,
            source_url=source_url,
            download_path=f"/content/colabvid/downloads/{job_id}.mp4",
            output_dir=f"/content/colabvid/outputs/{job_id}",
            clip_duration=clip_duration,
            clip_count=clip_count,
            progress_callback=callback,
            caption_template=f"🎬 {file_name} · Clip {{index}}/{{total}}",
        )
        await reporter.finish({"stage": "completed"})
    except Exception as exc:
        await reporter.finish({"stage": "failed", "error": str(exc)})


def _clean_file_name(value: str) -> str:
    """Normalize a user-provided filename into a safe display/storage name."""
    cleaned = re.sub(r"[\\/:*?\"<>|\n\r\t]", " ", value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned[:80]


def _parse_duration(value: str) -> float | None:
    """Parse and validate a clip duration supplied by the user."""
    try:
        duration = float(value)
    except ValueError:
        return None
    if not MIN_CLIP_DURATION <= duration <= MAX_CLIP_DURATION:
        return None
    return duration


def _parse_clip_count(value: str) -> int | None:
    """Parse and validate a clip count supplied by the user."""
    if not value.isdigit():
        return None
    count = int(value)
    if not MIN_CLIP_COUNT <= count <= MAX_CLIP_COUNT:
        return None
    return count
