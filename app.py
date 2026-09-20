"""Colabvid 2.0 application entry point."""

from telethon import TelegramClient

from bot.handlers import register_handlers
from config import Settings


SESSION_NAME = "colabvid2_session"


def main() -> None:
    settings = Settings.from_env()
    client = TelegramClient(SESSION_NAME, settings.api_id, settings.api_hash)
    register_handlers(client)

    print("Colabvid 2.0 bot is starting...")
    client.start(bot_token=settings.bot_token)
    print("Colabvid 2.0 bot is running.")
    client.run_until_disconnected()


if __name__ == "__main__":
    main()
