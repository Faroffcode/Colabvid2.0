"""Colabvid 2.0 application entry point."""

from pathlib import Path

from pyrogram import Client as PyrogramClient
from telethon import TelegramClient

from bot.handlers import register_handlers
from config import Settings
from services.jobs import JobManager


SESSION_NAME = "colabvid2_session"
PYROGRAM_SESSION_NAME = "colabvid2_uploads"
PYROGRAM_WORKDIR = Path("/content/colabvid")


def main() -> None:
    settings = Settings.from_env()
    if settings.channel_id is None:
        raise RuntimeError(
            "COLABVID_CHANNEL_ID is required for uploading rendered clips."
        )

    # Ensure Pyrogram can create its SQLite session database in Colab.
    PYROGRAM_WORKDIR.mkdir(parents=True, exist_ok=True)

    # Telethon remains responsible for commands and the unified status message.
    client = TelegramClient(SESSION_NAME, settings.api_id, settings.api_hash)

    # Pyrogram is responsible for video uploads and upload progress callbacks.
    upload_client = PyrogramClient(
        PYROGRAM_SESSION_NAME,
        api_id=settings.api_id,
        api_hash=settings.api_hash,
        bot_token=settings.bot_token,
        workdir=str(PYROGRAM_WORKDIR),
    )

    print("Starting Pyrogram upload client...")
    upload_client.start()

    try:
        # Resolve the destination with the SAME Pyrogram session that performs
        # uploads. This primes Pyrogram's peer cache and catches an inaccessible
        # channel before the first video reaches the upload pipeline.
        try:
            resolved_chat = upload_client.get_chat(settings.channel_id)
        except Exception as exc:
            raise RuntimeError(
                "Pyrogram cannot access COLABVID_CHANNEL_ID "
                f"({settings.channel_id}). Make sure this bot is a member/admin "
                "of the destination channel. Pyrogram error: {type(exc).__name__}: {exc}"
            ) from exc

        resolved_channel_id = int(resolved_chat.id)
        print(
            "Pyrogram destination resolved: "
            f"{getattr(resolved_chat, 'title', None) or 'Unknown'} "
            f"({resolved_channel_id})",
            flush=True,
        )

        job_manager = JobManager()
        register_handlers(
            client,
            upload_client=upload_client,
            channel_id=resolved_channel_id,
            job_manager=job_manager,
        )

        print("Starting Colabvid 2.0 Telethon bot...")
        client.start(bot_token=settings.bot_token)
        print("Colabvid 2.0 bot is running with Pyrogram uploads.")

        try:
            client.run_until_disconnected()
        finally:
            client.disconnect()
    finally:
        upload_client.stop()


if __name__ == "__main__":
    main()
