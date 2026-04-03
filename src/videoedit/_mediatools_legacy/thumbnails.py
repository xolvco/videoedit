"""Thumbnail generation — extract PNG frames from a video at regular intervals or specific timestamps."""

from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path


def _ms_to_ffmpeg_time(ms: int) -> str:
    """Convert milliseconds to HH:MM:SS.mmm format for ffmpeg -ss."""
    total_s, millis = divmod(ms, 1000)
    h, remainder = divmod(total_s, 3600)
    m, s = divmod(remainder, 60)
    return f"{h:02d}:{m:02d}:{s:02d}.{millis:03d}"


class ThumbnailError(RuntimeError):
    """Raised when thumbnail generation fails."""


def generate_thumbnails_at(
    input: str | Path,
    timestamps: list[int] | str | Path,
    output_dir: str | Path | None = None,
    *,
    timestamp_key: str = "timestamps",
    label_key: str | None = "label",
    zip_output: bool = False,
    timeout: float = 120.0,
) -> list[Path] | Path:
    """Extract PNG thumbnails at specific timestamps.

    Timestamps can be provided as:
    - A list of millisecond integers: ``[0, 15000, 30000]``
    - A path to a JSON file containing a ``timestamps`` key (or custom *timestamp_key*)

    The JSON file may contain other data — only the timestamp key is read.
    Each entry may be a plain integer (ms) or a dict with ``ms`` and optional ``label``:

    .. code-block:: json

        {
          "title": "My Video",
          "timestamps": [
            {"ms": 0,     "label": "intro"},
            {"ms": 30000, "label": "chapter-1"},
            {"ms": 90000, "label": "chapter-2"}
          ]
        }

    Or simply:

    .. code-block:: json

        {"timestamps": [0, 30000, 90000]}

    Args:
        input:          Source video file.
        timestamps:     List of ms values, or path to a JSON file.
        output_dir:     Destination folder.  Defaults to ``thumbnails/`` next to input.
        timestamp_key:  Key to read from the JSON file.  Default: ``"timestamps"``.
        label_key:      Key for a label string within each timestamp dict.
                        Used as the output filename stem.  Default: ``"label"``.
        zip_output:     Zip all thumbnails on completion.
        timeout:        Per-frame ffmpeg timeout in seconds.

    Returns:
        List of Paths to generated PNG files, or Path to the zip file.

    Raises:
        FileNotFoundError: if *input* or a JSON *timestamps* file does not exist
        ValueError: if the JSON file has no *timestamp_key* key
        ThumbnailError: if ffmpeg fails on any frame
    """
    import json

    input = Path(input)
    if not input.exists():
        raise FileNotFoundError(input)

    if output_dir is None:
        output_dir = input.parent / "thumbnails"
    else:
        output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Resolve timestamps
    if isinstance(timestamps, (str, Path)):
        json_path = Path(timestamps)
        if not json_path.exists():
            raise FileNotFoundError(json_path)
        data = json.loads(json_path.read_text(encoding="utf-8"))
        if timestamp_key not in data:
            raise ValueError(
                f"key '{timestamp_key}' not found in {json_path} — "
                f"available keys: {list(data.keys())}"
            )
        timestamps = data[timestamp_key]

    if not timestamps:
        raise ValueError("timestamps list is empty")

    generated: list[Path] = []

    for i, entry in enumerate(timestamps):
        if isinstance(entry, dict):
            ms = int(entry["ms"])
            label = entry.get(label_key) if label_key else None
        else:
            ms = int(entry)
            label = None

        stem = label if label else f"{input.stem}_{i + 1:04d}_at_{ms}ms"
        out_path = output_dir / f"{stem}.png"

        cmd = [
            "ffmpeg", "-y",
            "-ss", _ms_to_ffmpeg_time(ms),
            "-i", str(input),
            "-vframes", "1",
            "-f", "image2",
            str(out_path),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except FileNotFoundError:
            raise ThumbnailError("ffmpeg not found — install ffmpeg and ensure it is on PATH")
        except subprocess.TimeoutExpired:
            raise ThumbnailError(f"ffmpeg timed out at {ms}ms")

        if result.returncode != 0:
            raise ThumbnailError(f"ffmpeg error at {ms}ms: {result.stderr[-300:]}")

        generated.append(out_path)

    if zip_output:
        zip_path = output_dir / f"{input.stem}-thumbnails.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for thumb in generated:
                zf.write(thumb, thumb.name)
        return zip_path

    return generated


def generate_thumbnails(
    input: str | Path,
    output_dir: str | Path | None = None,
    *,
    interval_s: float = 15.0,
    zip_output: bool = False,
    timeout: float = 300.0,
) -> list[Path] | Path:
    """Extract PNG thumbnails from *input* at every *interval_s* seconds.

    Args:
        input:       Source video file.
        output_dir:  Destination folder.  Defaults to a ``thumbnails/`` subfolder
                     next to the input file.
        interval_s:  Seconds between thumbnails.  Default: 15.
        zip_output:  If True, zip all thumbnails into ``<stem>-thumbnails.zip``
                     in *output_dir* and return the zip path instead of the list.
        timeout:     ffmpeg timeout in seconds.

    Returns:
        List of Paths to generated PNG files, or a single Path to the zip file
        if *zip_output* is True.

    Raises:
        FileNotFoundError: if *input* does not exist
        ThumbnailError: if ffmpeg is not on PATH or extraction fails
    """
    input = Path(input)
    if not input.exists():
        raise FileNotFoundError(input)

    if output_dir is None:
        output_dir = input.parent / "thumbnails"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Output pattern: <stem>_0001.png, <stem>_0002.png, ...
    pattern = output_dir / f"{input.stem}_%04d.png"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input),
        "-vf", f"fps=1/{interval_s}",   # one frame every interval_s seconds
        "-f", "image2",
        str(pattern),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise ThumbnailError("ffmpeg not found — install ffmpeg and ensure it is on PATH")
    except subprocess.TimeoutExpired:
        raise ThumbnailError(f"ffmpeg timed out after {timeout}s")

    if result.returncode != 0:
        raise ThumbnailError(f"ffmpeg error: {result.stderr[-500:]}")

    # Collect generated files in order
    thumbs = sorted(output_dir.glob(f"{input.stem}_*.png"))

    if not thumbs:
        raise ThumbnailError(f"no thumbnails generated in {output_dir}")

    if zip_output:
        zip_path = output_dir / f"{input.stem}-thumbnails.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for thumb in thumbs:
                zf.write(thumb, thumb.name)
        return zip_path

    return thumbs

