"""Colabvid 2.0 application entry point."""

from pyrogram import Client as PyrogramClient
from telethon import TelegramClient

from bot.handlers import register_handlers
from config import Settings
from services.jobs import JobManager


SESSION_NAME = "colabvid2_session"
PYROGRAM_SESSION_NAME = "colabvid2_uploads"


def main() -> None:
    settings = Settings.from_env()
    if settings.channel_id is None:
        raise RuntimeError(
            "COLABVID_CHANNEL_ID is required for uploading rendered clips."
        )

    # Telethon remains responsible for commands and the unified status message.
    client = TelegramClient(SESSION_NAME, settings.api_id, settings.api_hash)

    # Pyrogram is responsible for video uploads and upload progress callbacks.
    upload_client = PyrogramClient(
        PYROGRAM_SESSION_NAME,
        api_id=settings.api_id,
        api_hash=settings.api_hash,
        bot_token=settings.bot_token,
        workdir="/content/colabvid",
    )

    job_manager = JobManager()
    register_handlers(
        client,
        upload_client=upload_client,
        channel_id=settings.channel_id,
        job_manager=job_manager,
    )

    print("Starting Pyrogram upload client...")
    upload_client.start()
    print("Starting Colabvid 2.0 Telethon bot...")
    client.start(bot_token=settings.bot_token)
    print("Colabvid 2.0 bot is running with Pyrogram uploads.")

    try:
        client.run_until_disconnected()
    finally:
        upload_client.stop()


if __name__ == "__main__":
    main()
