"""Streaming download helpers for direct media URLs and Pixeldrain links."""

from __future__ import annotations

from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import requests

ProgressCallback = Callable[[int, int | None], None]


def normalize_url(url: str) -> str:
    """Convert supported public Pixeldrain links to a downloadable URL."""
    cleaned = url.strip()
    parsed = urlparse(cleaned)

    if parsed.netloc.endswith("pixeldrain.com"):
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[0] in {"u", "l"}:
            file_id = parts[1]
            return f"https://pixeldrain.com/api/file/{file_id}"

    return cleaned


def download_file(
    url: str,
    destination: str | Path,
    progress_callback: ProgressCallback | None = None,
    chunk_size: int = 1024 * 1024,
    timeout: int = 30,
) -> Path:
    """Download a URL to disk using streamed chunks."""
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    source_url = normalize_url(url)

    with requests.get(source_url, stream=True, timeout=timeout) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0)) or None
        downloaded = 0

        with target.open("wb") as output:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                output.write(chunk)
                downloaded += len(chunk)
                if progress_callback:
                    progress_callback(downloaded, total)

    return target
