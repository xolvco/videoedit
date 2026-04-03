"""Audio mixing — levels, fades, and volume ramps for multi-source video."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path


class MixError(RuntimeError):
    """Raised when audio mix configuration is invalid."""


@dataclasses.dataclass
class AudioTrack:
    """One audio source in a mix.

    The source can be a standalone audio file (.mp3, .wav, .m4a, …) or a
    video file — FFmpeg extracts the audio stream automatically.

    Args:
        input:       Path to the audio or video file.
        level:       Base volume level, 0.0–1.0 (default 1.0 = full volume).
        fade_in_ms:  Duration of fade-in from silence at the track start.
        fade_out_ms: Duration of fade-out to silence at the track end.
                     Requires ``AudioMix.duration_ms`` to be set so the
                     renderer can place the fade correctly.
    """

    input: str | Path
    level: float = 1.0
    fade_in_ms: int = 0
    fade_out_ms: int = 0

    def __post_init__(self) -> None:
        if not (0.0 <= self.level <= 1.0):
            raise ValueError(f"level must be 0.0–1.0, got {self.level}")
        if self.fade_in_ms < 0:
            raise ValueError(f"fade_in_ms must be >= 0, got {self.fade_in_ms}")
        if self.fade_out_ms < 0:
            raise ValueError(f"fade_out_ms must be >= 0, got {self.fade_out_ms}")


@dataclasses.dataclass
class VolumeRamp:
    """A volume change on one track at a specific time.

    The level transitions linearly from the track's current level to
    ``to_level`` over ``over_ms`` milliseconds starting at ``at_ms``.

    Example — Capitol reveal at 45 s:

    .. code-block:: python

        VolumeRamp(track=0, at_ms=45_000, to_level=1.0, over_ms=2_000)
        VolumeRamp(track=1, at_ms=45_000, to_level=0.0, over_ms=1_000)

    The music (track 0) swells to full while the ambient Metro sound
    (track 1) fades out — both triggered by the same beat.

    Args:
        track:    Index into ``AudioMix.tracks``.
        at_ms:    When the ramp begins (milliseconds from video start).
        to_level: Target level at the end of the ramp (0.0–1.0).
        over_ms:  How long the transition takes (default 500 ms).
    """

    track: int
    at_ms: int
    to_level: float
    over_ms: int = 500

    def __post_init__(self) -> None:
        if not (0.0 <= self.to_level <= 1.0):
            raise ValueError(f"to_level must be 0.0–1.0, got {self.to_level}")
        if self.over_ms <= 0:
            raise ValueError(f"over_ms must be > 0, got {self.over_ms}")


@dataclasses.dataclass
class AudioMix:
    """Complete audio mix description for a canvas render.

    Combines multiple audio sources — backing music, panel ambient audio,
    voice-over — at specified levels with fade and ramp automation.

    The ``ramps`` list defines volume changes at specific moments.
    Use this to swell the music at the reveal, fade out ambient sound
    before the finale, or duck the backing track under a voice-over.

    Args:
        tracks:      Audio sources and their base levels.
        duration_ms: Total output duration in milliseconds.  Required if any
                     track has ``fade_out_ms > 0``.
        ramps:       Volume changes at specific times.
    """

    tracks: list[AudioTrack]
    duration_ms: int | None = None
    ramps: list[VolumeRamp] = dataclasses.field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.tracks:
            raise ValueError("AudioMix must have at least one track")
        for ramp in self.ramps:
            if ramp.track >= len(self.tracks):
                raise ValueError(
                    f"ramp references track {ramp.track} but only "
                    f"{len(self.tracks)} track(s) defined"
                )

    # ------------------------------------------------------------------
    # FFmpeg filter construction
    # ------------------------------------------------------------------

    def build_filter_chains(
        self, first_audio_input_idx: int
    ) -> tuple[list[str], str]:
        """Build per-track FFmpeg filter chains and a final mix label.

        Args:
            first_audio_input_idx: The FFmpeg ``-i`` index of the first
                audio track input.  Panel video inputs come first; audio
                inputs are appended after them.

        Returns:
            ``(filter_parts, output_label)`` where *filter_parts* is a list
            of filter strings to include in ``filter_complex`` and
            *output_label* is the label to ``-map`` for the audio output
            (e.g. ``"[aout]"``).
        """
        parts: list[str] = []
        processed_labels: list[str] = []

        for i, track in enumerate(self.tracks):
            src = f"[{first_audio_input_idx + i}:a]"
            label = f"a{i}"
            chain = self._track_filter(src, label, i, track)
            parts.append(chain)
            processed_labels.append(f"[{label}]")

        if len(self.tracks) == 1:
            # Single track — no amix needed, just rename the output label
            # by adding a copy (anull) filter
            last_label = processed_labels[0].strip("[]")
            parts.append(f"[{last_label}]anull[aout]")
        else:
            n = len(self.tracks)
            inputs = "".join(processed_labels)
            parts.append(
                f"{inputs}amix=inputs={n}:duration=first:normalize=0[aout]"
            )

        return parts, "[aout]"

    def _track_filter(
        self, src: str, out_label: str, track_idx: int, track: AudioTrack
    ) -> str:
        """Build the complete filter chain for one track."""
        filters: list[str] = []

        # Base level
        filters.append(f"volume={track.level:.6f}")

        # Fade in
        if track.fade_in_ms > 0:
            d = track.fade_in_ms / 1000.0
            filters.append(f"afade=t=in:st=0:d={d:.3f}")

        # Fade out — needs duration to place correctly
        if track.fade_out_ms > 0 and self.duration_ms is not None:
            d = track.fade_out_ms / 1000.0
            st = max(0.0, (self.duration_ms - track.fade_out_ms) / 1000.0)
            filters.append(f"afade=t=out:st={st:.3f}:d={d:.3f}")

        # Volume ramps for this track
        track_ramps = sorted(
            [r for r in self.ramps if r.track == track_idx],
            key=lambda r: r.at_ms,
        )
        for ramp in track_ramps:
            expr = self._ramp_volume_expr(ramp)
            filters.append(f"volume='{expr}':eval=frame")

        chain_str = ",".join(filters)
        return f"{src}{chain_str}[{out_label}]"

    @staticmethod
    def _ramp_volume_expr(ramp: VolumeRamp) -> str:
        """Build an FFmpeg ``volume`` filter expression for a linear ramp.

        The expression linearly interpolates from 1.0 (current normalised
        level) to ``to_level`` between ``at_ms`` and ``at_ms + over_ms``.
        Before the ramp the multiplier is 1.0; after it is ``to_level``.

        The ``volume`` filter applied here multiplies the track's already-
        levelled signal — so ``to_level=0.0`` silences it regardless of the
        base level.
        """
        t0 = ramp.at_ms / 1000.0
        t1 = (ramp.at_ms + ramp.over_ms) / 1000.0
        target = ramp.to_level

        # FFmpeg if(cond, then, else) — nested for three time regions
        return (
            f"if(lt(t,{t0:.3f}),"
            f"1,"
            f"if(lt(t,{t1:.3f}),"
            f"1+({target:.6f}-1)*(t-{t0:.3f})/{(t1-t0):.3f},"
            f"{target:.6f}))"
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dict."""
        d: dict = {
            "tracks": [
                {
                    "input": str(t.input),
                    "level": t.level,
                    "fade_in_ms": t.fade_in_ms,
                    "fade_out_ms": t.fade_out_ms,
                }
                for t in self.tracks
            ],
        }
        if self.duration_ms is not None:
            d["duration_ms"] = self.duration_ms
        if self.ramps:
            d["ramps"] = [
                {
                    "track": r.track,
                    "at_ms": r.at_ms,
                    "to_level": r.to_level,
                    "over_ms": r.over_ms,
                }
                for r in self.ramps
            ]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "AudioMix":
        """Reconstruct from a plain dict (as produced by :meth:`to_dict`)."""
        try:
            tracks = [
                AudioTrack(
                    input=t["input"],
                    level=float(t.get("level", 1.0)),
                    fade_in_ms=int(t.get("fade_in_ms", 0)),
                    fade_out_ms=int(t.get("fade_out_ms", 0)),
                )
                for t in data["tracks"]
            ]
            ramps = [
                VolumeRamp(
                    track=int(r["track"]),
                    at_ms=int(r["at_ms"]),
                    to_level=float(r["to_level"]),
                    over_ms=int(r.get("over_ms", 500)),
                )
                for r in data.get("ramps", [])
            ]
            return cls(
                tracks=tracks,
                duration_ms=data.get("duration_ms"),
                ramps=ramps,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MixError(f"Invalid audio mix data: {exc}") from exc
