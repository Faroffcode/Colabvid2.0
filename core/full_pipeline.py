"""End-to-end Colabvid processing and Telegram upload orchestration."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Awaitable, Callable

from core.pipeline import PipelineResult, run_pipeline
from core.upload_pipeline import upload_clips
from services.jobs import JobManager


ProgressCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


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
    """Run synchronous processing in a worker thread, then upload all clips."""
    loop = asyncio.get_running_loop()

    def processing_callback(payload: dict[str, Any]) -> None:
        if progress_callback is None:
            return
        result = progress_callback(payload)
        if result is not None:
            asyncio.run_coroutine_threadsafe(result, loop)

    result = await asyncio.to_thread(
        run_pipeline,
        job_manager=job_manager,
        job_id=job_id,
        source_url=source_url,
        download_path=download_path,
        output_dir=output_dir,
        clip_duration=clip_duration,
        clip_count=clip_count,
        progress_callback=processing_callback,
    )

    uploaded = await upload_clips(
        client=client,
        channel=channel,
        job_manager=job_manager,
        job_id=job_id,
        clip_paths=result.clip_paths,
        progress_callback=progress_callback,
        caption_template=caption_template,
        retries=retries,
    )
    return result, uploaded
