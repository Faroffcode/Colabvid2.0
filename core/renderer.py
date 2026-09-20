"""FFmpeg-based vertical video rendering helpers."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Callable


ProgressCallback = Callable[[dict[str, object]], None]


class RendererError(RuntimeError):
    """Raised when video rendering cannot be completed."""


def ensure_ffmpeg() -> str:
    """Return the FFmpeg executable path or raise a clear error."""
    executable = shutil.which("ffmpeg")
    if not executable:
        raise RendererError(
            "FFmpeg was not found. Install FFmpeg before rendering videos."
        )
    return executable


def build_vertical_filter(width: int = 1080, height: int = 1920) -> str:
    """Build a scale-and-pad filter that preserves the complete video frame."""
    if width <= 0 or height <= 0:
        raise ValueError("Output width and height must be positive")

    return (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
        "setsar=1"
    )


def render_clip(
    input_path: str | Path,
    output_path: str | Path,
    start_seconds: float,
    duration_seconds: float,
    *,
    width: int = 1080,
    height: int = 1920,
    crf: int = 23,
    preset: str = "medium",
    progress_callback: ProgressCallback | None = None,
) -> Path:
    """Render one padded vertical clip using FFmpeg."""
    source = Path(input_path)
    destination = Path(output_path)

    if not source.is_file():
        raise RendererError(f"Input video does not exist: {source}")
    if start_seconds < 0:
        raise ValueError("start_seconds cannot be negative")
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be greater than zero")
    if not 0 <= crf <= 51:
        raise ValueError("crf must be between 0 and 51")

    ffmpeg = ensure_ffmpeg()
    destination.parent.mkdir(parents=True, exist_ok=True)

    command = [
        ffmpeg,
        "-y",
        "-ss",
        str(start_seconds),
        "-i",
        str(source),
        "-t",
        str(duration_seconds),
        "-vf",
        build_vertical_filter(width, height),
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        str(crf),
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(destination),
    ]

    if progress_callback:
        progress_callback(
            {
                "stage": "encoding",
                "status": "starting",
                "input": str(source),
                "output": str(destination),
                "start_seconds": start_seconds,
                "duration_seconds": duration_seconds,
            }
        )

    process = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    if process.returncode != 0:
        error = process.stderr.strip() or "FFmpeg exited with an unknown error"
        raise RendererError(error)

    if progress_callback:
        progress_callback(
            {
                "stage": "encoding",
                "status": "complete",
                "output": str(destination),
                "start_seconds": start_seconds,
                "duration_seconds": duration_seconds,
            }
        )

    return destination
