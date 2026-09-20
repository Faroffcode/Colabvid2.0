"""Colabvid 2.0 application entry point."""

from telethon import TelegramClient

from bot.handlers import register_handlers
from config import Settings
from services.jobs import JobManager


SESSION_NAME = "colabvid2_session"


def main() -> None:
    settings = Settings.from_env()
    if settings.channel_id is None:
        raise RuntimeError(
            "COLABVID_CHANNEL_ID is required for uploading rendered clips."
        )

    # API ID and API hash authenticate the Telegram client used for uploads.
    client = TelegramClient(SESSION_NAME, settings.api_id, settings.api_hash)
    job_manager = JobManager()
    register_handlers(
        client,
        channel_id=settings.channel_id,
        job_manager=job_manager,
    )

    print("Colabvid 2.0 bot is starting...")
    client.start(bot_token=settings.bot_token)
    print("Colabvid 2.0 bot is running.")
    client.run_until_disconnected()


if __name__ == "__main__":
    main()
