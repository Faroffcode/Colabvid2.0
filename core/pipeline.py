"""Download and render pipeline orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from core.downloader import download_file
from core.renderer import render_clip


ProgressCallback = Callable[[dict[str, Any]], None]


def run_pipeline(
    url: str,
    output_dir: str | Path,
    *,
    clip_duration: float,
    clip_count: int,
    progress_callback: ProgressCallback | None = None,
) -> list[Path]:
    """Download a source and render clips sequentially."""
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    source_path = output_root / "source.mp4"

    print("[PIPELINE] Downloading source", flush=True)
    download_file(url, source_path, progress_callback=progress_callback)
    print(f"[PIPELINE] Download complete: {source_path}", flush=True)

    clips: list[Path] = []
    for index in range(clip_count):
        start_seconds = index * clip_duration
        destination = output_root / f"clip_{index + 1:03d}.mp4"
        print(
            f"[PIPELINE] Encoding clip {index + 1}/{clip_count} | "
            f"start={start_seconds}s duration={clip_duration}s",
            flush=True,
        )
        clip = render_clip(
            source_path,
            destination,
            start_seconds,
            clip_duration,
            progress_callback=progress_callback,
        )
        clips.append(clip)

    print(f"[PIPELINE] Rendering complete: {len(clips)} clips", flush=True)
    return clips
