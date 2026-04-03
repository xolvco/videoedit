"""Shared ffmpeg/ffprobe adapter surface for the unified package."""

from .ffmpeg import (
    FFmpegError,
    ensure_ffmpeg_binary,
    run_command,
    run_ffmpeg,
    run_ffprobe,
    validate_existing_file,
)

__all__ = [
    "FFmpegError",
    "ensure_ffmpeg_binary",
    "run_command",
    "run_ffmpeg",
    "run_ffprobe",
    "validate_existing_file",
]
