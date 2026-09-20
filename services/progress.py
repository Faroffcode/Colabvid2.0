"""Build one compact status message for the complete pipeline."""

from dataclasses import dataclass


@dataclass(slots=True)
class PipelineProgress:
    file_name: str = "Unknown"
    download_percent: int = 0
    download_size: str = "0 B / ?"
    download_speed: str = "-"
    encoding_clip: str = "-"
    encoding_range: str = "-"
    encoding_percent: int = 0
    uploading_clip: str = "-"
    upload_percent: int = 0
    upload_speed: str = "-"
    waiting: int = 0
    completed: int = 0
    total: int = 0
    retries: int = 0
    error: str = ""


def format_pipeline_status(progress: PipelineProgress) -> str:
    """Return the single Telegram status message used by the pipeline."""
    error_text = f"\n\n❌ **Error:** `{progress.error}`" if progress.error else ""
    return (
        "🎬 **COLABVID PIPELINE**\n\n"
        f"📁 File: `{progress.file_name}`\n\n"
        "⬇️ **DOWNLOAD**\n"
        f"✅ Complete: {progress.download_percent}%\n"
        f"📦 {progress.download_size}\n"
        f"⚡ Speed: {progress.download_speed}\n\n"
        "🎬 **ENCODING**\n"
        f"🎞️ Clip: {progress.encoding_clip}\n"
        f"📍 {progress.encoding_range}\n"
        f"📊 Progress: {progress.encoding_percent}%\n\n"
        "📤 **UPLOADING**\n"
        f"🎞️ Clip: {progress.uploading_clip}\n"
        f"📊 Progress: {progress.upload_percent}%\n"
        f"⚡ Speed: {progress.upload_speed}\n\n"
        "📦 **QUEUE**\n"
        f"⏳ Waiting: {progress.waiting}\n"
        f"✅ Completed: {progress.completed}/{progress.total}\n\n"
        f"🔁 Retries: {progress.retries}"
        f"{error_text}"
    )
