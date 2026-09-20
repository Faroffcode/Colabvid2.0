"""Streaming download helpers for direct media URLs and Pixeldrain links."""

from __future__ import annotations

import time
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
    """Download a URL to disk using streamed chunks and Colab diagnostics."""
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    source_url = normalize_url(url)
    started = time.monotonic()
    last_log = started
    last_downloaded = 0

    print(f"[DOWNLOAD] Starting: {source_url}", flush=True)
    print(f"[DOWNLOAD] Destination: {target}", flush=True)

    try:
        with requests.get(
            source_url,
            stream=True,
            timeout=(10, timeout),
            headers={"Accept-Encoding": "identity"},
        ) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0)) or None
            print(
                f"[DOWNLOAD] HTTP {response.status_code} | total={total or 'unknown'} bytes",
                flush=True,
            )
            downloaded = 0

            with target.open("wb") as output:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if not chunk:
                        continue
                    output.write(chunk)
                    downloaded += len(chunk)
                    now = time.monotonic()

                    if progress_callback:
                        progress_callback(downloaded, total)

                    if now - last_log >= 1.0:
                        elapsed = max(now - started, 0.001)
                        speed = (downloaded - last_downloaded) / max(now - last_log, 0.001)
                        percent = (
                            f"{downloaded * 100 / total:.1f}%" if total else "unknown%"
                        )
                        print(
                            f"[DOWNLOAD] {percent} | {downloaded} bytes | "
                            f"speed={speed / 1024 / 1024:.2f} MB/s | elapsed={elapsed:.1f}s",
                            flush=True,
                        )
                        last_log = now
                        last_downloaded = downloaded

            elapsed = max(time.monotonic() - started, 0.001)
            print(
                f"[DOWNLOAD] Complete: {downloaded} bytes in {elapsed:.1f}s "
                f"({downloaded / elapsed / 1024 / 1024:.2f} MB/s)",
                flush=True,
            )

    except Exception as exc:
        print(f"[DOWNLOAD] FAILED: {type(exc).__name__}: {exc}", flush=True)
        raise

    return target
