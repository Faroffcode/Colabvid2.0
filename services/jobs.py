"""Job state and lifecycle management for the Colabvid pipeline."""

from dataclasses import dataclass, field
from enum import StrEnum
from time import time
from typing import Any


class JobStage(StrEnum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    ENCODING = "encoding"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class JobState:
    """Mutable state for one processing job."""

    job_id: str
    source_url: str
    filename: str | None = None
    stage: JobStage = JobStage.QUEUED
    progress: float = 0.0
    current_clip: int = 0
    total_clips: int = 0
    retries: int = 0
    error: str | None = None
    created_at: float = field(default_factory=time)
    updated_at: float = field(default_factory=time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def update(self, **changes: Any) -> None:
        """Apply validated state changes and refresh the update timestamp."""
        for key, value in changes.items():
            if not hasattr(self, key):
                raise AttributeError(f"Unknown job state field: {key}")
            setattr(self, key, value)
        self.updated_at = time()


class JobManager:
    """In-memory manager for active and completed jobs."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobState] = {}

    def create(self, job_id: str, source_url: str, **metadata: Any) -> JobState:
        if job_id in self._jobs:
            raise ValueError(f"Job already exists: {job_id}")

        job = JobState(job_id=job_id, source_url=source_url, metadata=metadata)
        self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> JobState:
        try:
            return self._jobs[job_id]
        except KeyError as exc:
            raise KeyError(f"Unknown job: {job_id}") from exc

    def update(self, job_id: str, **changes: Any) -> JobState:
        job = self.get(job_id)
        job.update(**changes)
        return job

    def remove(self, job_id: str) -> JobState:
        try:
            return self._jobs.pop(job_id)
        except KeyError as exc:
            raise KeyError(f"Unknown job: {job_id}") from exc

    def all(self) -> list[JobState]:
        return list(self._jobs.values())

    def active(self) -> list[JobState]:
        return [
            job
            for job in self._jobs.values()
            if job.stage not in {JobStage.COMPLETED, JobStage.FAILED}
        ]
