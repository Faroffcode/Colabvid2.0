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
    """Render one padded vertical clip using FFmpeg with live progress events."""
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
        ffmpeg, "-y", "-ss", str(start_seconds), "-i", str(source),
        "-t", str(duration_seconds), "-vf", build_vertical_filter(width, height),
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
        "-c:a", "aac", "-progress", "pipe:1", "-nostats",
        "-movflags", "+faststart", str(destination),
    ]

    print(
        f"[ENCODING] Starting | clip start={start_seconds}s | duration={duration_seconds}s",
        flush=True,
    )
    print(f"[ENCODING] Input: {source}", flush=True)
    print(f"[ENCODING] Output: {destination}", flush=True)

    if progress_callback:
        progress_callback({
            "stage": "encoding", "status": "starting", "input": str(source),
            "output": str(destination), "start_seconds": start_seconds,
            "duration_seconds": duration_seconds, "percent": 0,
        })

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    last_percent = -1
    if process.stdout:
        for line in process.stdout:
            line = line.strip()
            if not line.startswith("out_time_ms="):
                continue
            try:
                elapsed_us = int(line.split("=", 1)[1])
                percent = min(99, max(0, int((elapsed_us / 1_000_000) / duration_seconds * 100)))
            except (ValueError, ZeroDivisionError):
                continue
            if percent != last_percent:
                last_percent = percent
                print(f"[ENCODING] Progress: {percent}%", flush=True)
                if progress_callback:
                    progress_callback({
                        "stage": "encoding", "status": "progress",
                        "percent": percent, "start_seconds": start_seconds,
                        "duration_seconds": duration_seconds,
                    })

    stderr = process.stderr.read().strip() if process.stderr else ""
    return_code = process.wait()
    if return_code != 0:
        error = stderr or "FFmpeg exited with an unknown error"
        print(f"[ENCODING] FAILED: {error}", flush=True)
        if progress_callback:
            progress_callback({"stage": "encoding", "status": "error", "error": error})
        raise RendererError(error)

    print(f"[ENCODING] Complete: {destination}", flush=True)
    if progress_callback:
        progress_callback({
            "stage": "encoding", "status": "complete", "output": str(destination),
            "start_seconds": start_seconds, "duration_seconds": duration_seconds,
            "percent": 100,
        })

    return destination
