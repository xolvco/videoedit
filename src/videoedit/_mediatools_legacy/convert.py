"""Audio conversion — convert media files to common audio formats."""

from __future__ import annotations

import subprocess
from pathlib import Path

SUPPORTED_FORMATS = ("mp3", "m4a", "wav", "flac", "ogg", "opus")


class ConvertError(RuntimeError):
    """Raised when a conversion fails."""


def convert_to_mp3(
    input: str | Path,
    output: str | Path | None = None,
    *,
    bitrate: str = "320k",
    timeout: float = 120.0,
) -> Path:
    """Convert *input* to MP3.

    Args:
        input:    Source media file (video or audio, any format ffmpeg supports).
        output:   Destination path.  Defaults to *input* with .mp3 extension,
                  in the same folder.
        bitrate:  MP3 bitrate.  Default: "320k" (highest quality).
                  Common values: "128k", "192k", "256k", "320k".
        timeout:  ffmpeg timeout in seconds.

    Returns:
        Path to the output .mp3 file.

    Raises:
        FileNotFoundError: if *input* does not exist
        ConvertError: if ffmpeg is not on PATH or conversion fails
    """
    return convert_audio(input, output, fmt="mp3", bitrate=bitrate, timeout=timeout)


def convert_audio(
    input: str | Path,
    output: str | Path | None = None,
    *,
    fmt: str = "mp3",
    bitrate: str | None = None,
    timeout: float = 120.0,
) -> Path:
    """Convert *input* to an audio format.

    Args:
        input:    Source media file.
        output:   Destination path.  Defaults to *input* with *fmt* extension.
        fmt:      Output format: "mp3", "m4a", "wav", "flac", "ogg", "opus".
        bitrate:  Audio bitrate (e.g. "320k").  Not applicable to lossless formats.
        timeout:  ffmpeg timeout in seconds.

    Returns:
        Path to the output file.

    Raises:
        FileNotFoundError: if *input* does not exist
        ValueError: if *fmt* is not supported
        ConvertError: if ffmpeg is not on PATH or conversion fails
    """
    input = Path(input)
    if not input.exists():
        raise FileNotFoundError(input)

    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(f"unsupported format '{fmt}' — choose from: {', '.join(SUPPORTED_FORMATS)}")

    if output is None:
        output = input.with_suffix(f".{fmt}")
    else:
        output = Path(output)

    output.parent.mkdir(parents=True, exist_ok=True)

    cmd = ["ffmpeg", "-y", "-i", str(input), "-vn"]  # -vn = drop video

    if fmt == "mp3":
        cmd += ["-codec:a", "libmp3lame"]
        if bitrate:
            cmd += ["-b:a", bitrate]
    elif fmt == "m4a":
        cmd += ["-codec:a", "aac"]
        if bitrate:
            cmd += ["-b:a", bitrate]
    elif fmt == "flac":
        cmd += ["-codec:a", "flac"]
    elif fmt == "wav":
        cmd += ["-codec:a", "pcm_s16le"]
    elif fmt == "ogg":
        cmd += ["-codec:a", "libvorbis"]
        if bitrate:
            cmd += ["-b:a", bitrate]
    elif fmt == "opus":
        cmd += ["-codec:a", "libopus"]
        if bitrate:
            cmd += ["-b:a", bitrate]

    cmd.append(str(output))

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise ConvertError("ffmpeg not found — install ffmpeg and ensure it is on PATH")
    except subprocess.TimeoutExpired:
        raise ConvertError(f"ffmpeg timed out after {timeout}s")

    if result.returncode != 0:
        raise ConvertError(f"ffmpeg error: {result.stderr[-500:]}")

    return output

