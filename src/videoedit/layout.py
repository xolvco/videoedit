"""Multi-panel canvas layout — compose multiple video streams onto one wide canvas."""

from __future__ import annotations

import dataclasses
import json
import subprocess
from pathlib import Path

from videoedit.audio import AudioBeatMap, BeatError
from videoedit.mix import AudioMix, MixError


class LayoutError(RuntimeError):
    """Raised when canvas layout or rendering fails."""


_POSITIONS = ("outer_left", "inner_left", "inner_right", "outer_right")
_CROPS = ("full", "smart")


@dataclasses.dataclass
class Panel:
    """One panel in a multi-panel canvas.

    Args:
        input:    Source video file.
        speed:    Playback speed multiplier (2.0 = fast-forward, 0.5 = slow-mo).
        position: Panel position — ``"outer_left"``, ``"inner_left"``,
                  ``"inner_right"``, or ``"outer_right"``.
        crop:     ``"full"`` scales the source to fill the panel.
                  ``"smart"`` center-crops to 60% before scaling, giving a
                  zoomed-in view of the most active region (V1: centre;
                  V2: energy-histogram guided).
    """

    input: str | Path
    speed: float = 1.0
    position: str = "outer_left"
    crop: str = "full"

    def __post_init__(self) -> None:
        if self.position not in _POSITIONS:
            raise ValueError(
                f"position must be one of {list(_POSITIONS)!r}, got {self.position!r}"
            )
        if self.crop not in _CROPS:
            raise ValueError(
                f"crop must be one of {list(_CROPS)!r}, got {self.crop!r}"
            )
        if self.speed <= 0:
            raise ValueError(f"speed must be positive, got {self.speed}")


@dataclasses.dataclass
class FinaleClip:
    """A full-width clip pinned to the end of the canvas render."""

    input: str | Path
    beats: int = 8
    """Number of beats to hold the finale (requires beat_map to be set)."""

    mode: str = "full_width"
    """``"full_width"`` scales the clip to the entire canvas width."""


class MultiPanelCanvas:
    """Compose multiple video streams onto a single wide canvas.

    Standard layout: four panels side by side on a 4860×2160 canvas
    (four 9:16 portrait streams — wider than 4K).

    The two outer panels show the full frame at their respective speeds.
    The two inner panels show a zoomed crop of the adjacent outer source
    (``crop="smart"``), giving the eye detail while the outer panels
    provide context.

    The panel sizes are the edit language — ``crop="smart"`` on the inner
    panels creates a visual tension between the wide view and the close-up
    that plays on the beat.

    Example (DC Metro)::

        canvas = MultiPanelCanvas(
            panels=[
                Panel("tunnel.mp4",   speed=2.0, position="outer_left",  crop="full"),
                Panel("tunnel.mp4",   speed=2.0, position="inner_left",  crop="smart"),
                Panel("platform.mp4", speed=0.5, position="inner_right", crop="smart"),
                Panel("platform.mp4", speed=0.5, position="outer_right", crop="full"),
            ],
            canvas_size=(4860, 2160),
        )
        canvas.set_finale("capitol.mp4", beats=8)
        canvas.render("dc_metro.mp4")
    """

    def __init__(
        self,
        panels: list[Panel],
        *,
        canvas_size: tuple[int, int] = (4860, 2160),
        beat_map: AudioBeatMap | None = None,
        audio_mix: AudioMix | None = None,
    ) -> None:
        if not panels:
            raise ValueError("panels must not be empty")
        self.panels = panels
        self.canvas_size = canvas_size
        self.beat_map = beat_map  # reserved — used in V2 for beat-sync transitions
        self.audio_mix = audio_mix
        self._finale: FinaleClip | None = None

    def set_finale(
        self,
        clip: str | Path,
        *,
        beats: int = 8,
        mode: str = "full_width",
    ) -> None:
        """Pin a full-width clip to the end of the render.

        The clip expands across the entire canvas — all four panel positions
        become one image. This is the reveal moment: the Capitol, the product,
        the CTA. Everything before it was panels; this is the payoff.

        Args:
            clip:  Path to the finale video file.
            beats: Number of beats to hold (requires ``beat_map`` to be set).
            mode:  Currently only ``"full_width"`` is supported.
        """
        if mode != "full_width":
            raise ValueError(f"mode must be 'full_width', got {mode!r}")
        self._finale = FinaleClip(input=Path(clip), beats=beats, mode=mode)

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
        """Render the multi-panel canvas to *output*.

        Builds an FFmpeg ``filter_complex`` that:

        1. Applies per-panel speed (``setpts``) and crop.
        2. Scales each panel to its column width × canvas height.
        3. Stacks all panels horizontally (``hstack``).
        4. If a finale is set, appends it full-width via ``concat``.

        Args:
            output:  Destination video file.
            crf:     H.264 quality (lower = better, default 18).
            preset:  ffmpeg encoding preset (default ``"fast"``).
            timeout: ffmpeg timeout in seconds (default 3600).

        Returns:
            Path to the rendered output file.

        Raises:
            FileNotFoundError: If any panel input file does not exist.
            LayoutError: If ffmpeg is not on PATH, returns an error, or times out.
        """
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)

        for panel in self.panels:
            p = Path(panel.input)
            if not p.exists():
                raise FileNotFoundError(f"Panel input not found: {p}")

        if self._finale is not None:
            fp = Path(self._finale.input)
            if not fp.exists():
                raise FileNotFoundError(f"Finale input not found: {fp}")

        cmd = self._build_command(output, crf=crf, preset=preset)

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
        except FileNotFoundError:
            raise LayoutError(
                "ffmpeg not found — install ffmpeg and ensure it is on PATH"
            )
        except subprocess.TimeoutExpired:
            raise LayoutError(f"ffmpeg timed out after {timeout}s")

        if result.returncode != 0:
            raise LayoutError(f"ffmpeg error: {result.stderr[-500:]}")

        return output

    # ------------------------------------------------------------------
    # Internal — command and filter_complex construction
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Serialisation — JSON is the edit description
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dict describing this canvas edit.

        The returned dict can be saved to ``canvas.json`` and later
        restored with :meth:`from_dict`.  The UI fills this structure;
        the renderer reads it.  Humans can inspect and edit it directly.
        """
        d: dict = {
            "type": "canvas_edit",
            "version": "1.0",
            "canvas_size": list(self.canvas_size),
            "output": "",
            "panels": [
                {
                    "input": str(p.input),
                    "speed": p.speed,
                    "position": p.position,
                    "crop": p.crop,
                }
                for p in self.panels
            ],
        }
        if self.audio_mix is not None:
            d["audio"] = self.audio_mix.to_dict()
        if self._finale is not None:
            d["finale"] = {
                "input": str(self._finale.input),
                "beats": self._finale.beats,
                "mode": self._finale.mode,
            }
        return d

    def save(self, path: str | Path) -> Path:
        """Save the canvas edit description to a JSON file.

        Args:
            path: Destination ``.json`` file (e.g. ``dc_metro_canvas.json``).

        Returns:
            Path to the written file.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))
        return path

    @classmethod
    def from_dict(cls, data: dict) -> "MultiPanelCanvas":
        """Reconstruct a :class:`MultiPanelCanvas` from a plain dict.

        Args:
            data: Dict as produced by :meth:`to_dict`.

        Returns:
            Reconstructed :class:`MultiPanelCanvas`.

        Raises:
            LayoutError: If required fields are missing or invalid.
        """
        try:
            panels = [
                Panel(
                    input=p["input"],
                    speed=float(p.get("speed", 1.0)),
                    position=p.get("position", "outer_left"),
                    crop=p.get("crop", "full"),
                )
                for p in data["panels"]
            ]
            canvas_size = tuple(data.get("canvas_size", [4860, 2160]))
            canvas = cls(panels, canvas_size=canvas_size)  # type: ignore[arg-type]

            if "audio" in data:
                try:
                    canvas.audio_mix = AudioMix.from_dict(data["audio"])
                except MixError as exc:
                    raise LayoutError(str(exc)) from exc
            if "finale" in data:
                f = data["finale"]
                canvas.set_finale(
                    f["input"],
                    beats=int(f.get("beats", 8)),
                    mode=f.get("mode", "full_width"),
                )
        except (KeyError, TypeError, ValueError) as exc:
            raise LayoutError(f"Invalid canvas edit data: {exc}") from exc
        return canvas

    @classmethod
    def load(cls, path: str | Path) -> "MultiPanelCanvas":
        """Load a canvas edit from a JSON file saved with :meth:`save`.

        Args:
            path: Path to the ``.json`` file.

        Returns:
            Reconstructed :class:`MultiPanelCanvas`.

        Raises:
            FileNotFoundError: If *path* does not exist.
            LayoutError: If the file is missing required fields.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Canvas edit file not found: {path}")
        data = json.loads(path.read_text())
        return cls.from_dict(data)

    def _panel_width(self) -> int:
        """Width of each panel column in pixels."""
        return self.canvas_size[0] // len(self.panels)

    def _panel_filter(self, stream_idx: int, panel: Panel) -> tuple[str, str]:
        """Return ``(filter_chain, out_label)`` for one panel stream.

        The filter chain:
        - ``setpts`` to apply speed
        - optional center crop to 60% for ``smart`` mode
        - ``scale`` to panel_w × canvas_height
        """
        w = self._panel_width()
        h = self.canvas_size[1]
        pts = f"setpts={1.0 / panel.speed:.6f}*PTS"

        if panel.crop == "smart":
            # Center crop to 60% of the frame before scaling — zoomed-in view.
            # V2: replace with energy-histogram guided crop position.
            crop = "crop=iw*6/10:ih*6/10,"
        else:
            crop = ""

        label = f"p{stream_idx}"
        chain = f"[{stream_idx}:v]{pts},{crop}scale={w}:{h},setsar=1[{label}]"
        return chain, label

    def _build_filter_complex(self) -> str:
        """Build the full FFmpeg filter_complex string."""
        parts: list[str] = []
        panel_labels: list[str] = []

        for i, panel in enumerate(self.panels):
            chain, label = self._panel_filter(i, panel)
            parts.append(chain)
            panel_labels.append(f"[{label}]")

        n = len(self.panels)
        hstack_inputs = "".join(panel_labels)

        # Finale input index (after panel inputs)
        finale_idx = n
        # Audio inputs start after panel inputs (and after finale if present)
        audio_start_idx = n + (1 if self._finale is not None else 0)

        if self._finale is not None:
            w, h = self.canvas_size
            parts.append(f"{hstack_inputs}hstack=inputs={n}[panels]")
            parts.append(f"[{finale_idx}:v]scale={w}:{h},setsar=1[fin]")
            parts.append("[panels][fin]concat=n=2:v=1:a=0[vout]")
            video_out = "[vout]"
        else:
            parts.append(f"{hstack_inputs}hstack=inputs={n}[vout]")
            video_out = "[vout]"

        # Audio mix
        if self.audio_mix is not None:
            audio_parts, audio_out = self.audio_mix.build_filter_chains(
                audio_start_idx
            )
            parts.extend(audio_parts)
        else:
            audio_out = None

        return ";".join(parts), video_out, audio_out

    def _build_command(
        self, output: Path, *, crf: int, preset: str
    ) -> list[str]:
        """Assemble the full ffmpeg command list."""
        cmd = ["ffmpeg", "-y"]

        # One -i per panel (files may repeat — FFmpeg handles this fine)
        for panel in self.panels:
            cmd += ["-i", str(Path(panel.input))]

        # Finale input (if set)
        if self._finale is not None:
            cmd += ["-i", str(Path(self._finale.input))]

        # Audio track inputs (if mix is set)
        if self.audio_mix is not None:
            for track in self.audio_mix.tracks:
                cmd += ["-i", str(Path(track.input))]

        fc, video_out, audio_out = self._build_filter_complex()

        cmd += ["-filter_complex", fc, "-map", video_out]

        if audio_out:
            cmd += ["-map", audio_out, "-c:a", "aac", "-b:a", "192k"]
        else:
            cmd += ["-an"]

        cmd += [
            "-c:v", "libx264",
            "-crf", str(crf),
            "-preset", preset,
            str(output),
        ]

        return cmd

