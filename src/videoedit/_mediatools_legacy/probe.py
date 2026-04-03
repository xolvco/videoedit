"""ffprobe wrapper — extract metadata from any media file."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class StreamInfo:
    codec_type: str       # "video" | "audio"
    codec_name: str
    width: int | None     # video only
    height: int | None    # video only
    sample_rate: int | None   # audio only
    channels: int | None      # audio only
    duration_s: float | None
    fps: float | None = None  # video only — frames per second (from r_frame_rate)


@dataclass
class ProbeResult:
    path: Path
    duration_s: float
    format_name: str
    size_bytes: int
    streams: list[StreamInfo] = field(default_factory=list)

    @property
    def duration_ms(self) -> int:
        return int(self.duration_s * 1000)

    @property
    def has_video(self) -> bool:
        return any(s.codec_type == "video" for s in self.streams)

    @property
    def has_audio(self) -> bool:
        return any(s.codec_type == "audio" for s in self.streams)

    @property
    def video_stream(self) -> StreamInfo | None:
        return next((s for s in self.streams if s.codec_type == "video"), None)

    @property
    def audio_stream(self) -> StreamInfo | None:
        return next((s for s in self.streams if s.codec_type == "audio"), None)


class ProbeError(RuntimeError):
    """Raised when ffprobe fails or is not found."""


def probe(path: str | Path, timeout: float = 10.0) -> ProbeResult:
    """Run ffprobe on *path* and return structured metadata.

    Raises:
        FileNotFoundError: if *path* does not exist
        ProbeError: if ffprobe is not on PATH or returns an error
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise ProbeError("ffprobe not found — install ffmpeg and ensure it is on PATH")
    except subprocess.TimeoutExpired:
        raise ProbeError(f"ffprobe timed out after {timeout}s for {path}")

    if result.returncode != 0:
        raise ProbeError(f"ffprobe error: {result.stderr.strip()}")

    data = json.loads(result.stdout)
    fmt = data.get("format", {})

    streams = []
    for s in data.get("streams", []):
        codec_type = s.get("codec_type", "")
        if codec_type not in ("video", "audio"):
            continue
        dur = s.get("duration")
        fps = None
        if codec_type == "video":
            r = s.get("r_frame_rate", "")
            if "/" in r:
                n, d = r.split("/", 1)
                fps = float(n) / float(d) if float(d) else None
            elif r:
                try:
                    fps = float(r)
                except ValueError:
                    pass
        streams.append(StreamInfo(
            codec_type=codec_type,
            codec_name=s.get("codec_name", ""),
            width=s.get("width"),
            height=s.get("height"),
            sample_rate=int(s["sample_rate"]) if s.get("sample_rate") else None,
            channels=s.get("channels"),
            duration_s=float(dur) if dur else None,
            fps=fps,
        ))

    return ProbeResult(
        path=path,
        duration_s=float(fmt.get("duration", 0)),
        format_name=fmt.get("format_name", ""),
        size_bytes=int(fmt.get("size", 0)),
        streams=streams,
    )

