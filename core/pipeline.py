"""Coordinate downloading and sequential clip rendering."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from core.downloader import download_file
from core.renderer import render_clip
from services.jobs import JobManager, JobStage


ProgressCallback = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class PipelineResult:
    """Files produced by a completed processing pipeline."""

    source_path: Path
    clip_paths: list[Path]


class PipelineError(RuntimeError):
    """Raised when a pipeline stage fails."""


def run_pipeline(
    *,
    job_manager: JobManager,
    job_id: str,
    source_url: str,
    download_path: str | Path,
    output_dir: str | Path,
    clip_duration: float,
    clip_count: int,
    progress_callback: ProgressCallback | None = None,
) -> PipelineResult:
    """Download a source video and render a sequence of vertical clips."""
    if clip_duration <= 0:
        raise ValueError("clip_duration must be greater than zero")
    if clip_count <= 0:
        raise ValueError("clip_count must be greater than zero")

    job = job_manager.get(job_id)
    output_directory = Path(output_dir)
    output_directory.mkdir(parents=True, exist_ok=True)

    def notify(payload: dict[str, Any]) -> None:
        if progress_callback:
            progress_callback({"job_id": job_id, **payload})

    try:
        job_manager.update(job_id, stage=JobStage.DOWNLOADING, progress=0.0)
        source_path = download_file(
            source_url,
            download_path,
            progress_callback=lambda downloaded, total: notify(
                {
                    "stage": JobStage.DOWNLOADING.value,
                    "downloaded_bytes": downloaded,
                    "total_bytes": total,
                }
            ),
        )

        job_manager.update(
            job_id,
            stage=JobStage.ENCODING,
            progress=0.0,
            total_clips=clip_count,
            current_clip=0,
        )

        clip_paths: list[Path] = []
        for index in range(clip_count):
            start_seconds = index * clip_duration
            output_path = output_directory / f"clip_{index + 1:03d}.mp4"

            render_clip(
                source_path,
                output_path,
                start_seconds,
                clip_duration,
                progress_callback=lambda event, clip=index + 1: notify(
                    {
                        **event,
                        "clip": clip,
                        "total_clips": clip_count,
                    }
                ),
            )
            clip_paths.append(output_path)
            job_manager.update(
                job_id,
                current_clip=index + 1,
                progress=((index + 1) / clip_count) * 100,
            )

        job_manager.update(
            job_id,
            stage=JobStage.COMPLETED,
            progress=100.0,
            current_clip=clip_count,
        )
        notify({"stage": JobStage.COMPLETED.value, "clip_paths": clip_paths})
        return PipelineResult(source_path=source_path, clip_paths=clip_paths)

    except Exception as exc:
        job_manager.update(
            job_id,
            stage=JobStage.FAILED,
            error=str(exc),
        )
        notify({"stage": JobStage.FAILED.value, "error": str(exc)})
        raise PipelineError(f"Pipeline failed for job {job_id}: {exc}") from exc
