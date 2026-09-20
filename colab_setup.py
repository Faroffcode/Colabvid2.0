"""Interactive Google Colab environment setup for Colabvid 2.0."""

from __future__ import annotations

import getpass
import os


REQUIRED_KEYS = (
    "COLABVID_API_ID",
    "COLABVID_API_HASH",
    "COLABVID_BOT_TOKEN",
    "COLABVID_CHANNEL_ID",
)


def _read_value(key: str, *, secret: bool = False) -> str:
    """Read one configuration value without displaying secrets when needed."""
    reader = getpass.getpass if secret else input
    value = reader(f"{key}: ").strip()
    if not value:
        raise ValueError(f"{key} cannot be empty")
    return value


def setup_environment() -> None:
    """Ask for all Colabvid settings and load them into os.environ."""
    print("🎬 Colabvid 2.0 · Google Colab setup")
    print("Paste the requested values below. Secrets are not saved to GitHub.\n")

    values = {
        "COLABVID_API_ID": _read_value("COLABVID_API_ID"),
        "COLABVID_API_HASH": _read_value("COLABVID_API_HASH", secret=True),
        "COLABVID_BOT_TOKEN": _read_value("COLABVID_BOT_TOKEN", secret=True),
        "COLABVID_CHANNEL_ID": _read_value("COLABVID_CHANNEL_ID"),
    }

    for key, value in values.items():
        os.environ[key] = value

    print("\n✅ Colabvid environment variables loaded for this Colab session.")
    print("You can now start the bot with: !python app.py")


if __name__ == "__main__":
    setup_environment()
