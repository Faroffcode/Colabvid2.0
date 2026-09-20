"""Telegram command and message handlers."""

from telethon import events

from bot.messages import HELP_MESSAGE, START_MESSAGE, URL_RECEIVED_MESSAGE


def register_handlers(client) -> None:
    """Register the initial bot handlers on a Telethon client."""

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
        if text.startswith(("http://", "https://")):
            await event.respond(URL_RECEIVED_MESSAGE, parse_mode="md")
