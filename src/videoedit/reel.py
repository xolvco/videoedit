"""Reel — concat multiple clips with gaps and chapter markers."""

from __future__ import annotations

import dataclasses
import json
import subprocess
import tempfile
from pathlib import Path


class ReelError(RuntimeError):
    """Raised when reel assembly or rendering fails."""


@dataclasses.dataclass
class ReelClip:
    """One clip in a reel.

    Args:
        input:    Source video file.
        title:    Chapter title — shown in compatible players for navigation.
        start_ms: Trim start offset in milliseconds (0 = from beginning).
        end_ms:   Trim end offset in milliseconds (None = to end of file).
    """

    input: str | Path
    title: str = ""
    start_ms: int = 0
    end_ms: int | None = None

    def __post_init__(self) -> None:
        if self.start_ms < 0:
            raise ValueError(f"start_ms must be >= 0, got {self.start_ms}")
        if self.end_ms is not None and self.end_ms <= self.start_ms:
            raise ValueError(
                f"end_ms ({self.end_ms}) must be > start_ms ({self.start_ms})"
            )


class Reel:
    """Assemble a sequence of video clips into one reel with gaps between them.

    Each clip is separated by a black-frame gap.  Chapter markers are
    embedded in the output so compatible players (including syscplayer) can
    jump ahead — one chapter per clip.

    Example::

        reel = Reel([
            ReelClip("intro.mp4",    title="Introduction"),
            ReelClip("segment1.mp4", title="The Metro"),
            ReelClip("segment2.mp4", title="The Platform"),
            ReelClip("outro.mp4",    title="The Capitol"),
        ], gap_ms=2000)
        reel.render("reel.mp4")

    Or load all ``*.mp4`` files from a folder in sorted order::

        reel = Reel.from_folder("videos/", gap_ms=2000)
        reel.render("reel.mp4")
    """

    def __init__(
        self,
        clips: list[ReelClip],
        *,
        gap_ms: int = 2000,
        canvas_size: tuple[int, int] = (1920, 1080),
        frame_rate: int = 30,
        sample_rate: int = 44100,
    ) -> None:
        if not clips:
            raise ValueError("clips must not be empty")
        if gap_ms < 0:
            raise ValueError(f"gap_ms must be >= 0, got {gap_ms}")
        self.clips = clips
        self.gap_ms = gap_ms
        self.canvas_size = canvas_size
        self.frame_rate = frame_rate
        self.sample_rate = sample_rate

    # ------------------------------------------------------------------
    # Convenience constructor
    # ------------------------------------------------------------------

    @classmethod
    def from_folder(
        cls,
        folder: str | Path,
        *,
        pattern: str = "*.mp4",
        sort: str = "name",
        gap_ms: int = 2000,
        **kw,
    ) -> "Reel":
        """Build a reel from all matching files in *folder*.

        Args:
            folder:  Directory to scan.
            pattern: Glob pattern (default ``"*.mp4"``).
            sort:    ``"name"`` (default) — alphabetical by filename;
                     ``"date"`` — by file modification time, oldest first.
            gap_ms:  Gap duration in milliseconds between clips.
            **kw:    Forwarded to :class:`Reel` (``canvas_size``, etc.).

        Raises:
            FileNotFoundError: If *folder* does not exist.
            ValueError: If no files match *pattern* or *sort* is invalid.
        """
        if sort not in ("name", "date"):
            raise ValueError(f"sort must be 'name' or 'date', got {sort!r}")
        folder = Path(folder)
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder}")
        files = list(folder.glob(pattern))
        if not files:
            raise ValueError(f"No files matching {pattern!r} in {folder}")
        if sort == "date":
            files.sort(key=lambda p: p.stat().st_mtime)
        else:
            files.sort()
        clips = [ReelClip(f, title=f.stem) for f in files]
        return cls(clips, gap_ms=gap_ms, **kw)

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(
        self,
        output: str | Path,
        *,
        crf: int = 18,
        preset: str = "fast",
        timeout: float = 3600.0,
    ) -> Path:
        """Render the reel to *output*.

        1. Probes each clip's duration (or uses ``end_ms - start_ms``).
        2. Writes an ffmetadata file with one ``[CHAPTER]`` per clip.
        3. Runs ffmpeg with a ``filter_complex`` that interleaves clips
           and black-frame/silence gaps, then embeds the chapter metadata.

        Args:
            output:  Destination video file.
            crf:     H.264 quality (lower = better, default 18).
            preset:  ffmpeg encoding preset (default ``"fast"``).
            timeout: ffmpeg timeout in seconds (default 3600).

        Returns:
            Path to the rendered output file.

        Raises:
            FileNotFoundError: If any clip input file does not exist.
            ReelError: If ffmpeg/ffprobe is not on PATH, returns an error,
                or times out.
        """
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)

        for clip in self.clips:
            p = Path(clip.input)
            if not p.exists():
                raise FileNotFoundError(f"Clip input not found: {p}")

        durations = [self._clip_duration_ms(c) for c in self.clips]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as meta_f:
            meta_path = Path(meta_f.name)
            meta_f.write(self._build_ffmetadata(durations))

        try:
            cmd = self._build_command(output, meta_path, crf=crf, preset=preset)
            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=timeout
                )
            except FileNotFoundError:
                raise ReelError(
                    "ffmpeg not found — install ffmpeg and ensure it is on PATH"
                )
            except subprocess.TimeoutExpired:
                raise ReelError(f"ffmpeg timed out after {timeout}s")

            if result.returncode != 0:
                raise ReelError(f"ffmpeg error: {result.stderr[-500:]}")
        finally:
            meta_path.unlink(missing_ok=True)

        return output

    # ------------------------------------------------------------------
    # Duration probe
    # ------------------------------------------------------------------

    def _clip_duration_ms(self, clip: ReelClip) -> int:
        """Return the duration of a clip segment in milliseconds.

        If ``end_ms`` is set, returns ``end_ms - start_ms`` without probing.
        Otherwise shells out to ``ffprobe`` to read the file duration.
        """
        if clip.end_ms is not None:
            return clip.end_ms - clip.start_ms

        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet",
                    "-print_format", "json",
                    "-show_entries", "format=duration",
                    str(Path(clip.input)),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except FileNotFoundError:
            raise ReelError(
                "ffprobe not found — install ffmpeg and ensure it is on PATH"
            )
        except subprocess.TimeoutExpired:
            raise ReelError(f"ffprobe timed out probing {clip.input}")

        if result.returncode != 0:
            raise ReelError(
                f"ffprobe error for {clip.input}: {result.stderr[-200:]}"
            )

        try:
            data = json.loads(result.stdout)
            total_s = float(data["format"]["duration"])
            segment_s = total_s - clip.start_ms / 1000.0
            return round(segment_s * 1000)
        except (KeyError, TypeError, ValueError) as exc:
            raise ReelError(
                f"Could not parse duration for {clip.input}: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Chapter metadata
    # ------------------------------------------------------------------

    def _build_ffmetadata(self, durations: list[int]) -> str:
        """Build an ffmetadata string with one ``[CHAPTER]`` per clip.

        Timestamps use millisecond timebase.  Gap time between chapters
        is included so chapter N+1 starts after the gap following chapter N.
        """
        lines = [";FFMETADATA1"]
        cursor = 0
        for clip, dur in zip(self.clips, durations):
            start = cursor
            end = cursor + dur
            title = clip.title or Path(clip.input).stem
            lines += [
                "",
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={start}",
                f"END={end}",
                f"title={title}",
            ]
            cursor = end + self.gap_ms
        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------
    # Filter complex + command
    # ------------------------------------------------------------------

    def _build_filter_complex(self) -> tuple[str, str, str]:
        """Build the FFmpeg ``filter_complex`` string for the reel.

        Returns:
            ``(filter_complex_str, video_out_label, audio_out_label)``

        Layout (3 clips, 2 gaps)::

            [0:v]scale[v0]; [0:a]anull[a0];
            color=black...[gap_v0]; aevalsrc=0...[gap_a0];
            [1:v]scale[v1]; [1:a]anull[a1];
            color=black...[gap_v1]; aevalsrc=0...[gap_a1];
            [2:v]scale[v2]; [2:a]anull[a2];
            [v0][gap_v0][v1][gap_v1][v2]concat=n=5:v=1:a=0[vout];
            [a0][gap_a0][a1][gap_a1][a2]concat=n=5:v=0:a=1[aout]
        """
        n = len(self.clips)
        w, h = self.canvas_size
        fps = self.frame_rate
        sr = self.sample_rate
        gap_s = self.gap_ms / 1000.0

        parts: list[str] = []
        v_labels: list[str] = []
        a_labels: list[str] = []

        for i, clip in enumerate(self.clips):
            v_in = f"[{i}:v]"
            a_in = f"[{i}:a]"

            if clip.start_ms > 0 or clip.end_ms is not None:
                ss = clip.start_ms / 1000.0
                trim_args = f"start={ss:.3f}"
                if clip.end_ms is not None:
                    trim_args += f":end={clip.end_ms / 1000.0:.3f}"
                parts.append(
                    f"{v_in}trim={trim_args},setpts=PTS-STARTPTS,scale={w}:{h}[v{i}]"
                )
                parts.append(
                    f"{a_in}atrim={trim_args},asetpts=PTS-STARTPTS[a{i}]"
                )
            else:
                parts.append(f"{v_in}scale={w}:{h}[v{i}]")
                parts.append(f"{a_in}anull[a{i}]")

            v_labels.append(f"[v{i}]")
            a_labels.append(f"[a{i}]")

            if i < n - 1:
                parts.append(
                    f"color=black:size={w}x{h}:rate={fps}"
                    f":duration={gap_s:.3f}[gap_v{i}]"
                )
                parts.append(
                    f"aevalsrc=0:channel_layout=stereo"
                    f":sample_rate={sr}:duration={gap_s:.3f}[gap_a{i}]"
                )
                v_labels.append(f"[gap_v{i}]")
                a_labels.append(f"[gap_a{i}]")

        concat_n = n + (n - 1)
        v_inputs = "".join(v_labels)
        a_inputs = "".join(a_labels)
        parts.append(f"{v_inputs}concat=n={concat_n}:v=1:a=0[vout]")
        parts.append(f"{a_inputs}concat=n={concat_n}:v=0:a=1[aout]")

        return ";".join(parts), "[vout]", "[aout]"

    def _build_command(
        self, output: Path, meta_path: Path, *, crf: int, preset: str
    ) -> list[str]:
        """Assemble the full ffmpeg command list."""
        cmd = ["ffmpeg", "-y"]

        for clip in self.clips:
            cmd += ["-i", str(Path(clip.input))]

        # ffmetadata file — for chapter embedding
        cmd += ["-i", str(meta_path)]

        fc, video_out, audio_out = self._build_filter_complex()
        meta_idx = len(self.clips)

        cmd += ["-filter_complex", fc]
        cmd += ["-map", video_out, "-map", audio_out]
        cmd += ["-map_metadata", str(meta_idx)]
        cmd += ["-c:v", "libx264", "-crf", str(crf), "-preset", preset]
        cmd += ["-c:a", "aac", "-b:a", "192k"]
        cmd += [str(output)]

        return cmd

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dict describing this reel."""
        return {
            "type": "reel",
            "version": "1.0",
            "gap_ms": self.gap_ms,
            "canvas_size": list(self.canvas_size),
            "frame_rate": self.frame_rate,
            "sample_rate": self.sample_rate,
            "output": "",
            "clips": [
                {
                    "input": str(c.input),
                    "title": c.title,
                    "start_ms": c.start_ms,
                    "end_ms": c.end_ms,
                }
                for c in self.clips
            ],
        }

    def save(self, path: str | Path) -> Path:
        """Save the reel description to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))
        return path

    @classmethod
    def from_dict(cls, data: dict) -> "Reel":
        """Reconstruct a :class:`Reel` from a plain dict."""
        try:
            clips = [
                ReelClip(
                    input=c["input"],
                    title=c.get("title", ""),
                    start_ms=int(c.get("start_ms", 0)),
                    end_ms=int(c["end_ms"]) if c.get("end_ms") is not None else None,
                )
                for c in data["clips"]
            ]
            return cls(
                clips,
                gap_ms=int(data.get("gap_ms", 2000)),
                canvas_size=tuple(data.get("canvas_size", [1920, 1080])),
                frame_rate=int(data.get("frame_rate", 30)),
                sample_rate=int(data.get("sample_rate", 44100)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ReelError(f"Invalid reel data: {exc}") from exc

    @classmethod
    def load(cls, path: str | Path) -> "Reel":
        """Load a reel from a JSON file saved with :meth:`save`."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Reel file not found: {path}")
        data = json.loads(path.read_text())
        return cls.from_dict(data)
