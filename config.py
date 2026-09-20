"""Application configuration loaded from environment variables."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    api_id: int
    api_hash: str
    bot_token: str
    channel_id: int | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        api_id = os.getenv("COLABVID_API_ID", "").strip()
        api_hash = os.getenv("COLABVID_API_HASH", "").strip()
        bot_token = os.getenv("COLABVID_BOT_TOKEN", "").strip()
        channel_id = os.getenv("COLABVID_CHANNEL_ID", "").strip()

        missing = []
        if not api_id:
            missing.append("COLABVID_API_ID")
        if not api_hash:
            missing.append("COLABVID_API_HASH")
        if not bot_token:
            missing.append("COLABVID_BOT_TOKEN")

        if missing:
            names = ", ".join(missing)
            raise RuntimeError(f"Missing required environment variables: {names}")

        try:
            parsed_api_id = int(api_id)
        except ValueError as exc:
            raise RuntimeError("COLABVID_API_ID must be an integer") from exc

        parsed_channel_id = None
        if channel_id:
            try:
                parsed_channel_id = int(channel_id)
            except ValueError as exc:
                raise RuntimeError("COLABVID_CHANNEL_ID must be an integer") from exc

        return cls(
            api_id=parsed_api_id,
            api_hash=api_hash,
            bot_token=bot_token,
            channel_id=parsed_channel_id,
        )
