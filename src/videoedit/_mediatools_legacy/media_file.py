"""MediaFile — primary interface for working with a media file."""

from __future__ import annotations

from pathlib import Path

from videoedit._mediatools_legacy.probe import ProbeResult, probe


class MediaFile:
    """Wraps a media file path and provides lazy-cached metadata and operations.

    Usage::

        mf = MediaFile("video.mp4")
        print(mf.duration_ms)      # 183400
        print(mf.has_video)        # True
        print(mf.has_audio)        # True
        mf.extract_audio("out.wav")
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(self.path)
        self._probe: ProbeResult | None = None

    # ------------------------------------------------------------------
    # Metadata (lazy probe)
    # ------------------------------------------------------------------

    @property
    def info(self) -> ProbeResult:
        if self._probe is None:
            self._probe = probe(self.path)
        return self._probe

    @property
    def duration_ms(self) -> int:
        return self.info.duration_ms

    @property
    def duration_s(self) -> float:
        return self.info.duration_s

    @property
    def has_video(self) -> bool:
        return self.info.has_video

    @property
    def has_audio(self) -> bool:
        return self.info.has_audio

    @property
    def size_bytes(self) -> int:
        return self.info.size_bytes

    # ------------------------------------------------------------------
    # Operations (delegate to audio.py / video.py as they are added)
    # ------------------------------------------------------------------

    def extract_audio(self, output: str | Path, **kwargs) -> Path:
        """Extract the audio stream to *output*.  See :func:`mediatools.audio.extract_audio`."""
        from videoedit._mediatools_legacy.audio import extract_audio
        return extract_audio(self.path, output, **kwargs)

    def convert_to_mp3(self, output: str | Path | None = None, **kwargs) -> Path:
        """Convert to MP3.  See :func:`mediatools.convert.convert_to_mp3`."""
        from videoedit._mediatools_legacy.convert import convert_to_mp3
        return convert_to_mp3(self.path, output, **kwargs)

    def convert_audio(self, output: str | Path | None = None, fmt: str = "mp3", **kwargs) -> Path:
        """Convert to an audio format.  See :func:`mediatools.convert.convert_audio`."""
        from videoedit._mediatools_legacy.convert import convert_audio
        return convert_audio(self.path, output, fmt=fmt, **kwargs)

    def clip(self, output: str | Path, start_ms: int, end_ms: int, **kwargs) -> Path:
        """Clip the file from *start_ms* to *end_ms*.  See :func:`mediatools.video.clip`."""
        from videoedit._mediatools_legacy.video import clip
        return clip(self.path, output, start_ms=start_ms, end_ms=end_ms, **kwargs)

    def extract_frames(
        self,
        output_dir: str | Path | None = None,
        *,
        fps: float | None = None,
        start_ms: int | None = None,
        end_ms: int | None = None,
        width: int | None = None,
        height: int | None = None,
        fmt: str = "png",
        **kwargs,
    ) -> list:
        """Extract frames for analysis or assembly.  See :func:`mediatools.video.extract_frames`."""
        from videoedit._mediatools_legacy.video import extract_frames
        return extract_frames(
            self.path, output_dir,
            fps=fps, start_ms=start_ms, end_ms=end_ms,
            width=width, height=height, fmt=fmt, **kwargs,
        )

    def generate_thumbnails_at(
        self,
        timestamps: list[int] | str | Path,
        output_dir: str | Path | None = None,
        **kwargs,
    ) -> list[Path] | Path:
        """Generate thumbnails at specific timestamps (ms list or JSON file).
        See :func:`mediatools.thumbnails.generate_thumbnails_at`."""
        from videoedit._mediatools_legacy.thumbnails import generate_thumbnails_at
        return generate_thumbnails_at(self.path, timestamps, output_dir, **kwargs)

    def generate_thumbnails(
        self,
        output_dir: str | Path | None = None,
        *,
        interval_s: float = 15.0,
        zip_output: bool = False,
    ) -> list[Path] | Path:
        """Generate PNG thumbnails at *interval_s* second intervals.
        See :func:`mediatools.thumbnails.generate_thumbnails`."""
        from videoedit._mediatools_legacy.thumbnails import generate_thumbnails
        return generate_thumbnails(
            self.path, output_dir, interval_s=interval_s, zip_output=zip_output
        )

    def normalize(
        self,
        output: str | Path,
        *,
        width: int = 1920,
        height: int = 1080,
        fps: float = 30.0,
        fit: str = "letterbox",
        **kwargs,
    ) -> Path:
        """Normalize to consistent resolution, FPS, and format.
        See :func:`mediatools.video.normalize_video`."""
        from videoedit._mediatools_legacy.video import normalize_video
        return normalize_video(self.path, output, width=width, height=height,
                               fps=fps, fit=fit, **kwargs)

    def __repr__(self) -> str:
        return f"MediaFile({self.path!r})"

