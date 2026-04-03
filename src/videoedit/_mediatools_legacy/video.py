"""Video clipping, frame extraction, listing, and concatenation functions."""

from __future__ import annotations

import dataclasses
import json
import subprocess
import tempfile
from pathlib import Path


class VideoError(RuntimeError):
    """Raised when a video operation fails."""


@dataclasses.dataclass
class FrameInfo:
    """Metadata for a single extracted frame."""
    path: Path
    index: int          # 1-based frame index within the extraction run
    timestamp_ms: int   # approximate presentation timestamp in milliseconds


def clip(
    input: str | Path,
    output: str | Path,
    *,
    start_ms: int,
    end_ms: int,
    timeout: float = 120.0,
) -> Path:
    """Clip *input* from *start_ms* to *end_ms* and write to *output*.

    Uses stream copy where possible (no re-encode) for speed.

    Args:
        input:     Source media file.
        output:    Destination path — format inferred from extension.
        start_ms:  Start position in milliseconds.
        end_ms:    End position in milliseconds.
        timeout:   ffmpeg timeout in seconds.

    Returns:
        Path to the output file.

    Raises:
        FileNotFoundError: if *input* does not exist
        ValueError: if start_ms >= end_ms
        VideoError: if ffmpeg is not on PATH or returns an error
    """
    input = Path(input)
    output = Path(output)

    if not input.exists():
        raise FileNotFoundError(input)

    if start_ms >= end_ms:
        raise ValueError(f"start_ms ({start_ms}) must be less than end_ms ({end_ms})")

    output.parent.mkdir(parents=True, exist_ok=True)

    start_s = start_ms / 1000.0
    duration_s = (end_ms - start_ms) / 1000.0

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_s),
        "-i", str(input),
        "-t", str(duration_s),
        "-c", "copy",              # stream copy — fast, no re-encode
        str(output),
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError:
        raise VideoError("ffmpeg not found — install ffmpeg and ensure it is on PATH")
    except subprocess.TimeoutExpired:
        raise VideoError(f"ffmpeg timed out after {timeout}s")

    if result.returncode != 0:
        raise VideoError(f"ffmpeg error: {result.stderr[-500:]}")

    return output


def extract_frames(
    input: str | Path,
    output_dir: str | Path | None = None,
    *,
    fps: float | None = None,
    start_ms: int | None = None,
    end_ms: int | None = None,
    width: int | None = None,
    height: int | None = None,
    fmt: str = "png",
    timeout: float = 600.0,
) -> list[FrameInfo]:
    """Extract frames from a video for analysis or assembly pipelines.

    Suitable for feeding into optical flow, motion detection, keypoint
    tracking, or ML inference.  Output files are named
    ``frame_000001.png``, ``frame_000002.png``, etc.

    Args:
        input:      Source video file.
        output_dir: Destination folder (default: ``frames/`` next to *input*).
        fps:        Frames to extract per second.  ``None`` extracts every
                    native frame (potentially thousands — use with care for
                    long videos).  Set e.g. ``2.0`` for 2 fps analysis.
        start_ms:   Start of the extraction window in milliseconds.
        end_ms:     End of the extraction window in milliseconds.
        width:      Resize output width.  ``-1`` preserves aspect ratio.
        height:     Resize output height.  ``-1`` preserves aspect ratio.
        fmt:        Output format: ``"png"`` (lossless) or ``"jpg"``.
        timeout:    ffmpeg timeout in seconds.

    Returns:
        List of :class:`FrameInfo` objects sorted by frame index, each
        containing the output ``path``, 1-based ``index``, and
        ``timestamp_ms`` (approximate).

    Raises:
        FileNotFoundError: if *input* does not exist.
        ValueError: if *fmt* is unsupported, or start_ms >= end_ms.
        VideoError: if ffmpeg is not on PATH or returns an error.
    """
    input = Path(input)
    if not input.exists():
        raise FileNotFoundError(input)

    if fmt not in ("png", "jpg", "jpeg"):
        raise ValueError(f"fmt must be 'png' or 'jpg', got {fmt!r}")
    ext = "jpg" if fmt == "jpeg" else fmt

    if start_ms is not None and end_ms is not None and start_ms >= end_ms:
        raise ValueError(f"start_ms ({start_ms}) must be less than end_ms ({end_ms})")

    if output_dir is None:
        output_dir = input.parent / "frames"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Resolve effective fps for timestamp computation
    effective_fps: float
    if fps is not None:
        effective_fps = fps
    else:
        from videoedit._mediatools_legacy.probe import probe, ProbeError
        try:
            info = probe(input)
        except ProbeError as e:
            raise VideoError(f"Cannot probe {input}: {e}") from e
        vs = info.video_stream
        if vs is None or vs.fps is None:
            raise VideoError(f"{input} has no video stream with readable frame rate")
        effective_fps = vs.fps

    # Build ffmpeg filter chain
    filters: list[str] = []
    if fps is not None:
        filters.append(f"fps={fps}")
    if width is not None or height is not None:
        w = width if width is not None else -1
        h = height if height is not None else -1
        filters.append(f"scale={w}:{h}")

    cmd = ["ffmpeg", "-y"]
    if start_ms is not None:
        cmd += ["-ss", str(start_ms / 1000.0)]
    cmd += ["-i", str(input)]
    if end_ms is not None and start_ms is not None:
        cmd += ["-t", str((end_ms - start_ms) / 1000.0)]
    elif end_ms is not None:
        cmd += ["-to", str(end_ms / 1000.0)]
    if filters:
        cmd += ["-vf", ",".join(filters)]
    cmd += ["-an"]   # no audio track in frame output
    cmd += [str(output_dir / f"frame_%06d.{ext}")]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError:
        raise VideoError("ffmpeg not found — install ffmpeg and ensure it is on PATH")
    except subprocess.TimeoutExpired:
        raise VideoError(f"ffmpeg timed out after {timeout}s")

    if result.returncode != 0:
        raise VideoError(f"ffmpeg error: {result.stderr[-500:]}")

    base_ms = start_ms or 0
    frames: list[FrameInfo] = []
    for frame_path in sorted(output_dir.glob(f"frame_*.{ext}")):
        # frame_000001.png → index 1
        try:
            idx = int(frame_path.stem.split("_")[1])
        except (IndexError, ValueError):
            continue
        ts_ms = base_ms + round((idx - 1) / effective_fps * 1000)
        frames.append(FrameInfo(path=frame_path, index=idx, timestamp_ms=ts_ms))

    return frames


# ---------------------------------------------------------------------------
# Directory listing
# ---------------------------------------------------------------------------

VIDEO_EXTENSIONS = frozenset({
    ".mp4", ".mkv", ".mov", ".avi", ".wmv", ".flv", ".webm",
    ".m4v", ".ts", ".mts", ".m2ts", ".3gp",
})


@dataclasses.dataclass
class VideoEntry:
    """Metadata for a single video file in a directory listing."""
    path: Path
    duration_ms: int
    size_bytes: int
    width: int | None
    height: int | None
    fps: float | None
    codec: str | None


def list_videos(
    directory: str | Path,
    *,
    recursive: bool = False,
    extensions: set[str] | None = None,
    sort_by: str = "name",  # "name" | "mtime" | "size" | "duration"
) -> list[VideoEntry]:
    """Scan *directory* for video files and return their metadata.

    Args:
        directory:  Folder to scan.
        recursive:  If ``True``, descend into subdirectories.
        extensions: Set of lowercase extensions to include (with dot).
                    Defaults to :data:`VIDEO_EXTENSIONS`.
        sort_by:    Primary sort key — ``"name"`` (alphabetical),
                    ``"mtime"`` (newest last), ``"size"``, or ``"duration"``.

    Returns:
        List of :class:`VideoEntry` objects, each probed for metadata.
        Files that cannot be probed are skipped with a warning to stderr.

    Raises:
        FileNotFoundError: if *directory* does not exist.
        NotADirectoryError: if *directory* is not a directory.
    """
    import sys

    directory = Path(directory)
    if not directory.exists():
        raise FileNotFoundError(directory)
    if not directory.is_dir():
        raise NotADirectoryError(directory)

    exts = extensions if extensions is not None else VIDEO_EXTENSIONS
    glob_fn = directory.rglob if recursive else directory.glob

    paths = sorted(
        p for p in glob_fn("*")
        if p.is_file() and p.suffix.lower() in exts
    )

    from videoedit._mediatools_legacy.probe import probe, ProbeError

    entries: list[VideoEntry] = []
    for p in paths:
        try:
            info = probe(p)
        except ProbeError as e:
            print(f"warning: skipping {p.name} — {e}", file=sys.stderr)
            continue
        vs = info.video_stream
        entries.append(VideoEntry(
            path=p,
            duration_ms=info.duration_ms,
            size_bytes=info.size_bytes,
            width=vs.width if vs else None,
            height=vs.height if vs else None,
            fps=vs.fps if vs else None,
            codec=vs.codec_name if vs else None,
        ))

    key_fns = {
        "name": lambda e: e.path.name.lower(),
        "mtime": lambda e: e.path.stat().st_mtime,
        "size": lambda e: e.size_bytes,
        "duration": lambda e: e.duration_ms,
    }
    if sort_by not in key_fns:
        raise ValueError(f"sort_by must be one of {list(key_fns)}, got {sort_by!r}")

    entries.sort(key=key_fns[sort_by])
    return entries


# ---------------------------------------------------------------------------
# Manifest: human-editable clip order file
# ---------------------------------------------------------------------------

def write_manifest(
    entries: list[VideoEntry] | list[Path],
    manifest_path: str | Path,
    *,
    output_video: str | Path | None = None,
) -> Path:
    """Write a manifest JSON that a human can reorder before concatenation.

    The manifest lists clips in the current order.  Edit the ``"clips"`` array
    to change the order, remove clips, or add a ``"label"`` to each entry.
    Then pass the manifest to :func:`concat_videos`.

    Args:
        entries:       List of :class:`VideoEntry` objects (from :func:`list_videos`)
                       or plain :class:`Path` objects.
        manifest_path: Where to write the ``.json`` file.
        output_video:  Suggested output path written into the manifest
                       (default: ``reel.mp4`` next to the manifest).

    Returns:
        Path to the written manifest file.
    """
    manifest_path = Path(manifest_path)
    if output_video is None:
        output_video = manifest_path.with_name("reel.mp4")

    clips = []
    for e in entries:
        p = e.path if isinstance(e, VideoEntry) else Path(e)
        entry: dict = {"path": str(p)}
        if isinstance(e, VideoEntry):
            entry["duration_ms"] = e.duration_ms
            if e.width and e.height:
                entry["resolution"] = f"{e.width}x{e.height}"
        clips.append(entry)

    manifest = {
        "output": str(output_video),
        "clips": clips,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def read_manifest(manifest_path: str | Path) -> tuple[list[Path], Path]:
    """Read a manifest and return ``(ordered_clip_paths, output_path)``.

    Args:
        manifest_path: Path to a manifest JSON written by :func:`write_manifest`
                       or created manually.

    Returns:
        Tuple of ``(list[Path], output_path)``.

    Raises:
        FileNotFoundError: if the manifest file does not exist.
        ValueError: if the manifest is malformed or any clip path is missing.
    """
    manifest_path = Path(manifest_path)
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if "clips" not in data:
        raise ValueError(f"manifest {manifest_path} is missing 'clips' key")

    output = Path(data.get("output", manifest_path.with_name("reel.mp4")))
    clips: list[Path] = []
    for item in data["clips"]:
        if isinstance(item, str):
            p = Path(item)
        elif isinstance(item, dict):
            if "path" not in item:
                raise ValueError(f"clip entry missing 'path': {item}")
            p = Path(item["path"])
        else:
            raise ValueError(f"unexpected clip entry type: {item!r}")
        clips.append(p)

    return clips, output


# ---------------------------------------------------------------------------
# Concatenation
# ---------------------------------------------------------------------------

def concat_videos(
    inputs: list[str | Path] | str | Path,
    output: str | Path | None = None,
    *,
    re_encode: bool = False,
    timeout: float = 3600.0,
) -> Path:
    """Concatenate multiple video files into a single output.

    Uses the ffmpeg concat demuxer for speed.  With ``re_encode=False``
    (default) all inputs **must share the same codec, resolution, and frame
    rate** — ffmpeg will fail loudly if they do not.  Set ``re_encode=True``
    to force a re-encode to H.264/AAC, which works with heterogeneous sources
    at the cost of extra processing time.

    Accepts a list of file paths **or** a path to a manifest JSON produced by
    :func:`write_manifest`.

    Args:
        inputs:     List of video paths, or path to a ``manifest.json``.
        output:     Destination file.  Required when *inputs* is a list.
                    When *inputs* is a manifest the output defaults to the
                    value stored in the manifest.
        re_encode:  Force H.264 (libx264) + AAC re-encode.  Slower but
                    handles mixed sources.
        timeout:    ffmpeg timeout in seconds.

    Returns:
        Path to the concatenated output file.

    Raises:
        FileNotFoundError: if any input file is missing.
        ValueError: if fewer than 2 inputs are provided.
        VideoError: if ffmpeg is not on PATH or returns an error.
    """
    # Resolve inputs — manifest or list
    if isinstance(inputs, (str, Path)) and Path(inputs).suffix.lower() == ".json":
        clips, manifest_output = read_manifest(inputs)
        if output is None:
            output = manifest_output
    else:
        if isinstance(inputs, (str, Path)):
            inputs = [inputs]
        clips = [Path(p) for p in inputs]

    if output is None:
        raise ValueError("output path is required when inputs is a list (not a manifest)")

    if len(clips) < 2:
        raise ValueError(f"concat requires at least 2 inputs, got {len(clips)}")

    for p in clips:
        if not Path(p).exists():
            raise FileNotFoundError(p)

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    # Write a temporary ffmpeg concat file list
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as fh:
        for p in clips:
            # ffmpeg concat demuxer requires forward slashes and escaped apostrophes
            safe = str(Path(p).resolve()).replace("'", r"'\''")
            fh.write(f"file '{safe}'\n")
        filelist = Path(fh.name)

    try:
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(filelist)]
        if re_encode:
            cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "18",
                    "-c:a", "aac", "-b:a", "192k"]
        else:
            cmd += ["-c", "copy"]
        cmd.append(str(output))

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
        except FileNotFoundError:
            raise VideoError("ffmpeg not found — install ffmpeg and ensure it is on PATH")
        except subprocess.TimeoutExpired:
            raise VideoError(f"ffmpeg timed out after {timeout}s")

        if result.returncode != 0:
            msg = result.stderr[-800:]
            if not re_encode and "Invalid data" in msg:
                msg += (
                    "\n\nHint: sources may have different codecs or resolutions. "
                    "Try concat_videos(..., re_encode=True)."
                )
            raise VideoError(f"ffmpeg error: {msg}")

    finally:
        filelist.unlink(missing_ok=True)

    return output


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

_FIT_MODES = frozenset({"letterbox", "crop", "stretch"})


def normalize_video(
    input: str | Path,
    output: str | Path,
    *,
    width: int = 1920,
    height: int = 1080,
    fps: float = 30.0,
    fit: str = "letterbox",
    pixel_fmt: str = "yuv420p",
    audio_sample_rate: int = 44100,
    audio_channels: int = 2,
    crf: int = 18,
    preset: str = "fast",
    timeout: float = 600.0,
) -> Path:
    """Re-encode *input* to a consistent resolution, frame rate, and format.

    All sources in an assembly reel should be normalized before concatenation
    to guarantee identical codec, resolution, FPS, and pixel format.

    The *fit* parameter controls how the source is scaled to the target frame:

    - ``"letterbox"`` (default) — scale to fit, pad with black bars.
      Preserves all content; adds horizontal or vertical bars as needed.
    - ``"crop"`` — scale to fill, crop the edges.
      Fills the entire frame; the subject stays centred but edges are lost.
    - ``"stretch"`` — force exact dimensions without preserving aspect ratio.
      Distorts the image; rarely desired but occasionally useful.

    Args:
        input:             Source video file.
        output:            Destination path.
        width:             Target width in pixels (default 1920).
        height:            Target height in pixels (default 1080).
        fps:               Target frame rate (default 30.0).
        fit:               Scaling mode — ``"letterbox"``, ``"crop"``, or
                           ``"stretch"`` (default ``"letterbox"``).
        pixel_fmt:         Pixel format (default ``yuv420p``).
        audio_sample_rate: Output audio sample rate in Hz (default 44100).
        audio_channels:    Output audio channels (default 2).
        crf:               H.264 CRF — 18 = visually lossless (default 18).
        preset:            ffmpeg encoding preset (default ``"fast"``).
        timeout:           ffmpeg timeout in seconds (default 600).

    Returns:
        Path to the normalized output file.

    Raises:
        FileNotFoundError: if *input* does not exist.
        ValueError: if *fit* is not a recognised mode.
        VideoError: if ffmpeg is not on PATH or returns an error.
    """
    input = Path(input)
    output = Path(output)

    if fit not in _FIT_MODES:
        raise ValueError(f"fit must be one of {sorted(_FIT_MODES)}, got {fit!r}")

    if not input.exists():
        raise FileNotFoundError(input)

    output.parent.mkdir(parents=True, exist_ok=True)

    # Build the scaling portion of the video filter chain.
    if fit == "letterbox":
        # Scale down to fit within target box, then pad to exact size.
        scale_filters = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
        )
    elif fit == "crop":
        # Scale up to fill target box, then crop the overshoot from centre.
        scale_filters = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height}"
        )
    else:  # stretch
        scale_filters = f"scale={width}:{height}"

    vf = f"{scale_filters},fps={fps},format={pixel_fmt}"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", str(crf),
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", str(audio_sample_rate),
        "-ac", str(audio_channels),
        str(output),
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError:
        raise VideoError("ffmpeg not found — install ffmpeg and ensure it is on PATH")
    except subprocess.TimeoutExpired:
        raise VideoError(f"ffmpeg timed out after {timeout}s")

    if result.returncode != 0:
        raise VideoError(f"ffmpeg error: {result.stderr[-500:]}")

    return output


def normalize_videos(
    inputs: list[str | Path],
    output_dir: str | Path,
    *,
    suffix: str = ".norm",
    width: int = 1920,
    height: int = 1080,
    fps: float = 30.0,
    fit: str = "letterbox",
    pixel_fmt: str = "yuv420p",
    audio_sample_rate: int = 44100,
    audio_channels: int = 2,
    crf: int = 18,
    preset: str = "fast",
    timeout: float = 600.0,
) -> list[Path]:
    """Normalize a list of video files to consistent settings.

    Each output is written to *output_dir* with *suffix* inserted before the
    extension (e.g. ``clip.mp4`` → ``clip.norm.mp4``).  The returned list
    preserves the input order and can be passed directly to
    :func:`concat_videos`.

    Args:
        inputs:     Source video files.
        output_dir: Folder to write normalized files.
        suffix:     Stem suffix for output filenames (default ``".norm"``).
        fit:        Scaling mode — ``"letterbox"``, ``"crop"``, or
                    ``"stretch"`` (default ``"letterbox"``).
        **kwargs:   Forwarded to :func:`normalize_video`.

    Returns:
        List of normalized output paths in input order.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    kwargs = dict(
        width=width, height=height, fps=fps, fit=fit,
        pixel_fmt=pixel_fmt,
        audio_sample_rate=audio_sample_rate,
        audio_channels=audio_channels,
        crf=crf, preset=preset, timeout=timeout,
    )

    outputs: list[Path] = []
    for src in inputs:
        src = Path(src)
        dest = output_dir / f"{src.stem}{suffix}{src.suffix}"
        normalize_video(src, dest, **kwargs)
        outputs.append(dest)

    return outputs


def speed_change(
    input: str | Path,
    output: str | Path,
    speed: float,
    *,
    audio: bool = True,
    crf: int = 18,
    preset: str = "fast",
    timeout: float = 600.0,
) -> Path:
    """Re-encode *input* at *speed* times normal playback rate.

    ``speed > 1.0`` compresses time (fast-forward).
    ``speed < 1.0`` stretches time (slow-motion).

    Video is re-encoded using ``setpts``. Audio is re-sampled using
    ``atempo`` (chained for factors outside 0.5–2.0). Pass ``audio=False``
    to drop the audio track, which avoids ``atempo`` limitations and is
    slightly faster to encode.

    Args:
        input:   Source video file.
        output:  Destination path — format inferred from extension.
        speed:   Playback speed multiplier. Must be > 0.
                 Examples: ``2.0`` = 2× fast-forward, ``0.5`` = half-speed.
        audio:   If ``True`` (default), re-sample audio to match the new speed.
                 If ``False``, drop the audio track.
        crf:     H.264/H.265 quality factor (lower = better, default 18).
        preset:  ffmpeg encoding preset (default ``"fast"``).
        timeout: ffmpeg timeout in seconds (default 600).

    Returns:
        Path to the output file.

    Raises:
        FileNotFoundError: If *input* does not exist.
        ValueError: If *speed* is not positive.
        VideoError: If ffmpeg is not on PATH or returns an error.
    """
    input = Path(input)
    output = Path(output)

    if not input.exists():
        raise FileNotFoundError(input)
    if speed <= 0:
        raise ValueError(f"speed must be positive, got {speed}")

    output.parent.mkdir(parents=True, exist_ok=True)

    # setpts: PTS / speed  →  1/speed * PTS  (inverse because PTS is per-frame time)
    video_filter = f"setpts={1.0 / speed}*PTS"

    if audio:
        # atempo only accepts values in [0.5, 2.0]; chain for factors outside that range
        audio_filters = _build_atempo_chain(speed)
        filter_args = [
            "-filter:v", video_filter,
            "-filter:a", ",".join(audio_filters),
        ]
    else:
        filter_args = ["-filter:v", video_filter, "-an"]

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input),
        *filter_args,
        "-c:v", "libx264",
        "-crf", str(crf),
        "-preset", preset,
        str(output),
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError:
        raise VideoError("ffmpeg not found — install ffmpeg and ensure it is on PATH")
    except subprocess.TimeoutExpired:
        raise VideoError(f"ffmpeg timed out after {timeout}s")

    if result.returncode != 0:
        raise VideoError(f"ffmpeg error: {result.stderr[-500:]}")

    return output


def _build_atempo_chain(speed: float) -> list[str]:
    """Return a list of atempo filter values that together achieve *speed*.

    ``atempo`` only accepts values in [0.5, 2.0], so large or small speed
    factors require chaining. For example, 4× = ``atempo=2.0,atempo=2.0``.
    """
    filters: list[str] = []
    remaining = speed

    if remaining >= 1.0:
        while remaining > 2.0:
            filters.append("atempo=2.0")
            remaining /= 2.0
        filters.append(f"atempo={remaining:.6f}")
    else:
        while remaining < 0.5:
            filters.append("atempo=0.5")
            remaining /= 0.5
        filters.append(f"atempo={remaining:.6f}")

    return filters

