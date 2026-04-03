"""Canonical public model aliases for the unified backend."""

from dataclasses import dataclass

from .assembly import TitleStyle
from .layout import FinaleClip, Panel
from .manifests import (
    CanvasManifest,
    CutDefinition,
    CutListManifest,
    OutputDefinition,
    PlaylistItem,
    PlaylistManifest,
    SourceAsset,
    TimelineManifest,
    TimelineSection,
)
from .mix import AudioMix, AudioTrack, VolumeRamp


CanvasPanel = Panel


@dataclass(frozen=True)
class RenderPreset:
    id: str
    width: int
    height: int
    fps: int = 30
    audio_sample_rate: int = 44100
    audio_channels: int = 2


__all__ = [
    "AudioMix",
    "AudioTrack",
    "CanvasManifest",
    "CanvasPanel",
    "CutDefinition",
    "CutListManifest",
    "FinaleClip",
    "OutputDefinition",
    "PlaylistItem",
    "PlaylistManifest",
    "RenderPreset",
    "SourceAsset",
    "TimelineManifest",
    "TimelineSection",
    "TitleStyle",
    "VolumeRamp",
]
