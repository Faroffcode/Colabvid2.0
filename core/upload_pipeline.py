"""Run the rendered-clip upload stage with unified progress reporting."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Awaitable, Callable

from core.uploader import upload_clip
from services.jobs import JobManager, JobStage


AsyncProgressCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


async def upload_clips(
    *,
    client: Any,
    channel: Any,
    job_manager: JobManager,
    job_id: str,
    clip_paths: list[str | Path],
    progress_callback: AsyncProgressCallback | None = None,
    caption_template: str = "🎬 Clip {index}/{total}",
    retries: int = 2,
) -> list[Any]:
    """Upload clips sequentially and update the job's upload state."""
    if not clip_paths:
        raise ValueError("clip_paths cannot be empty")

    total = len(clip_paths)
    job_manager.update(
        job_id,
        stage=JobStage.UPLOADING,
        progress=0.0,
        current_clip=0,
        total_clips=total,
    )

    async def notify(payload: dict[str, Any]) -> None:
        if progress_callback:
            result = progress_callback({"job_id": job_id, "total_clips": total, **payload})
            if result is not None:
                await result

    messages: list[Any] = []
    for index, clip_path in enumerate(clip_paths, start=1):
        caption = caption_template.format(index=index, total=total)
        message = await upload_clip(
            client,
            channel,
            clip_path,
            caption=caption,
            retries=retries,
            progress_callback=notify,
        )
        messages.append(message)
        job_manager.update(
            job_id,
            current_clip=index,
            progress=index * 100 / total,
        )
        await notify(
            {
                "stage": JobStage.UPLOADING.value,
                "status": "complete",
                "clip": index,
                "total_clips": total,
                "path": str(clip_path),
            }
        )

    job_manager.update(
        job_id,
        stage=JobStage.COMPLETED,
        progress=100.0,
        current_clip=total,
    )
    await notify(
        {
            "stage": JobStage.COMPLETED.value,
            "status": "complete",
            "clip": total,
            "total_clips": total,
        }
    )
    return messages
