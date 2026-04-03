"""Audio extraction and processing functions."""

from __future__ import annotations

import subprocess
from pathlib import Path


class AudioError(RuntimeError):
    """Raised when an audio operation fails."""


def extract_audio(
    input: str | Path,
    output: str | Path,
    *,
    sample_rate: int = 44100,
    channels: int = 2,
    timeout: float = 120.0,
) -> Path:
    """Extract the audio stream from *input* and write to *output*.

    Args:
        input:        Source media file (video or audio).
        output:       Destination path — format inferred from extension (.wav, .mp3, .m4a, etc.)
        sample_rate:  Output sample rate in Hz.  Default: 44100.
        channels:     Number of output channels.  Default: 2 (stereo).
        timeout:      ffmpeg timeout in seconds.

    Returns:
        Path to the output file.

    Raises:
        FileNotFoundError: if *input* does not exist
        AudioError: if ffmpeg is not on PATH or returns an error
    """
    input = Path(input)
    output = Path(output)

    if not input.exists():
        raise FileNotFoundError(input)

    output.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input),
        "-vn",                        # drop video
        "-ar", str(sample_rate),
        "-ac", str(channels),
        str(output),
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError:
        raise AudioError("ffmpeg not found — install ffmpeg and ensure it is on PATH")
    except subprocess.TimeoutExpired:
        raise AudioError(f"ffmpeg timed out after {timeout}s")

    if result.returncode != 0:
        raise AudioError(f"ffmpeg error: {result.stderr[-500:]}")

    return output

