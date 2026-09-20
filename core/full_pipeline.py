"""End-to-end Colabvid processing with streaming encode and upload."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

from core.downloader import download_file
from core.renderer import render_clip
from core.uploader import upload_clip
from services.jobs import JobManager, JobStage

ProgressCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


@dataclass
class PipelineResult:
    """Result containing the clips produced and uploaded by the pipeline."""

    clip_paths: list[Path]


async def run_full_pipeline(
    *,
    client: Any,
    channel: Any,
    job_manager: JobManager,
    job_id: str,
    source_url: str,
    download_path: str | Path,
    output_dir: str | Path,
    clip_duration: float,
    clip_count: int,
    progress_callback: ProgressCallback | None = None,
    caption_template: str = "🎬 Clip {index}/{total}",
    retries: int = 2,
) -> tuple[PipelineResult, list[Any]]:
    """Download once, then encode and upload each clip immediately."""
    loop = asyncio.get_running_loop()
    source = Path(download_path)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    def emit(payload: dict[str, Any]) -> None:
        if progress_callback is None:
            return
        result = progress_callback({"job_id": job_id, **payload})
        if result is not None:
            asyncio.run_coroutine_threadsafe(result, loop)

    try:
        print("[PIPELINE] Downloading source", flush=True)
        await asyncio.to_thread(download_file, source_url, source, progress_callback=emit)
        print(f"[PIPELINE] Download complete: {source}", flush=True)

        job_manager.update(
            job_id,
            stage=JobStage.ENCODING,
            progress=0.0,
            current_clip=0,
            total_clips=clip_count,
        )

        clips: list[Path] = []
        messages: list[Any] = []

        for index in range(clip_count):
            start_seconds = index * clip_duration
            destination = output_root / f"clip_{index + 1:03d}.mp4"
            print(
                f"[PIPELINE] Encoding clip {index + 1}/{clip_count} | "
                f"start={start_seconds}s duration={clip_duration}s",
                flush=True,
            )

            clip = await asyncio.to_thread(
                render_clip,
                source,
                destination,
                start_seconds,
                clip_duration,
                progress_callback=emit,
            )
            clips.append(clip)

            job_manager.update(
                job_id,
                stage=JobStage.UPLOADING,
                current_clip=index + 1,
                total_clips=clip_count,
            )

            async def notify(payload: dict[str, Any], clip_index: int = index + 1) -> None:
                if progress_callback is None:
                    return
                result = progress_callback({
                    "job_id": job_id,
                    "clip": clip_index,
                    "total_clips": clip_count,
                    **payload,
                })
                if result is not None:
                    await result

            caption = caption_template.format(index=index + 1, total=clip_count)
            message = await upload_clip(
                client,
                channel,
                clip,
                caption=caption,
                progress_callback=notify,
                retries=retries,
            )
            messages.append(message)

            job_manager.update(
                job_id,
                stage=JobStage.ENCODING if index + 1 < clip_count else JobStage.COMPLETED,
                progress=(index + 1) * 100 / clip_count,
                current_clip=index + 1,
                total_clips=clip_count,
            )

        print(f"[PIPELINE] Encode/upload complete: {len(clips)} clips", flush=True)
        return PipelineResult(clip_paths=clips), messages

    except Exception as exc:
        job_manager.update(job_id, stage=JobStage.FAILED, error=str(exc))
        emit({"stage": JobStage.FAILED.value, "error": str(exc)})
        raise
