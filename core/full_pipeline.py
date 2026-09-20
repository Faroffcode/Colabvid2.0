"""End-to-end Colabvid processing with parallel encoding and uploading."""

from __future__ import annotations

import asyncio
import os
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
    """Download once, then encode and upload clips concurrently with limits."""
    loop = asyncio.get_running_loop()
    source = Path(download_path)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    encode_workers = max(1, int(os.getenv("COLABVID_ENCODE_WORKERS", "2")))
    upload_workers = max(1, int(os.getenv("COLABVID_UPLOAD_WORKERS", "2")))
    encode_semaphore = asyncio.Semaphore(encode_workers)
    upload_semaphore = asyncio.Semaphore(upload_workers)

    def emit(payload: dict[str, Any]) -> None:
        if progress_callback is None:
            return
        result = progress_callback({"job_id": job_id, **payload})
        if result is not None:
            asyncio.run_coroutine_threadsafe(result, loop)

    def download_progress(downloaded: int, total: int | None) -> None:
        percent = round((downloaded * 100 / total), 1) if total else 0.0
        emit({
            "stage": "downloading",
            "status": "progress",
            "downloaded_bytes": downloaded,
            "total_bytes": total,
            "percent": percent,
        })

    async def process_clip(index: int) -> tuple[Path, Any]:
        start_seconds = index * clip_duration
        destination = output_root / f"clip_{index + 1:03d}.mp4"

        async with encode_semaphore:
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

        job_manager.update(
            job_id,
            stage=JobStage.UPLOADING,
            current_clip=index + 1,
            total_clips=clip_count,
        )

        async def notify(payload: dict[str, Any]) -> None:
            if progress_callback is None:
                return
            result = progress_callback({
                "job_id": job_id,
                "clip": index + 1,
                "total_clips": clip_count,
                **payload,
            })
            if result is not None:
                await result

        caption = caption_template.format(index=index + 1, total=clip_count)
        async with upload_semaphore:
            print(f"[PIPELINE] Uploading clip {index + 1}/{clip_count}", flush=True)
            message = await upload_clip(
                client,
                channel,
                clip,
                caption=caption,
                progress_callback=notify,
                retries=retries,
            )

        job_manager.update(
            job_id,
            stage=JobStage.COMPLETED,
            progress=(index + 1) * 100 / clip_count,
            current_clip=index + 1,
            total_clips=clip_count,
        )
        return clip, message

    try:
        print("[PIPELINE] Downloading source", flush=True)
        await asyncio.to_thread(
            download_file,
            source_url,
            source,
            progress_callback=download_progress,
        )
        print(f"[PIPELINE] Download complete: {source}", flush=True)

        job_manager.update(
            job_id,
            stage=JobStage.ENCODING,
            progress=0.0,
            current_clip=0,
            total_clips=clip_count,
        )

        results = await asyncio.gather(
            *(process_clip(index) for index in range(clip_count))
        )
        clips = [clip for clip, _ in sorted(results, key=lambda item: item[0].name)]
        messages = [message for _, message in sorted(results, key=lambda item: item[0].name)]

        print(f"[PIPELINE] Parallel encode/upload complete: {len(clips)} clips", flush=True)
        return PipelineResult(clip_paths=clips), messages

    except Exception as exc:
        job_manager.update(job_id, stage=JobStage.FAILED, error=str(exc))
        emit({"stage": JobStage.FAILED.value, "error": str(exc)})
        raise
