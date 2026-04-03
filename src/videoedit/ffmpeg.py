from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Iterable


class FFmpegError(RuntimeError):
    """Raised when an FFmpeg command fails."""


def ensure_ffmpeg_binary(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise FileNotFoundError(
            f"Required executable '{name}' was not found on PATH. Install FFmpeg and try again."
        )
    return path


def run_command(args: Iterable[str]) -> subprocess.CompletedProcess[str]:
    command = list(args)
    return subprocess.run(command, capture_output=True, text=True, check=False)


def run_ffmpeg(args: Iterable[str]) -> subprocess.CompletedProcess[str]:
    ensure_ffmpeg_binary("ffmpeg")
    result = run_command(args)
    if result.returncode != 0:
        raise FFmpegError(result.stderr.strip() or "FFmpeg command failed.")
    return result


def run_ffprobe(args: Iterable[str]) -> subprocess.CompletedProcess[str]:
    ensure_ffmpeg_binary("ffprobe")
    result = run_command(args)
    if result.returncode != 0:
        raise FFmpegError(result.stderr.strip() or "ffprobe command failed.")
    return result


def validate_existing_file(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.exists() or not resolved.is_file():
        raise FileNotFoundError(f"Input file does not exist: {path}")
    return resolved
