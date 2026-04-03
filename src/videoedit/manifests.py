from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .assembly import TitleStyle, parse_timecode
from .layout import FinaleClip, Panel
from .mix import AudioMix


@dataclass(frozen=True)
class SourceAsset:
    id: str
    path: Path


@dataclass(frozen=True)
class CutDefinition:
    id: str
    source: str
    start_seconds: float = 0.0
    end_seconds: float | None = None
    duration_seconds: float | None = None
    label: str | None = None
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class TimelineDefaults:
    gap_after_seconds: float = 0.0
    audio_fade_in_seconds: float = 0.0
    audio_fade_out_seconds: float = 0.0


@dataclass(frozen=True)
class TimelineSectionDefinition:
    cut: str
    title: str | None = None
    gap_after_seconds: float | None = None
    audio_fade_in_seconds: float | None = None
    audio_fade_out_seconds: float | None = None


@dataclass(frozen=True)
class OutputDefinition:
    path: Path | None = None


@dataclass(frozen=True)
class ConcatDefaults:
    spacer_mode: str = "black"
    spacer_seconds: float = 0.0
    audio_fade_in_seconds: float = 0.0
    audio_fade_out_seconds: float = 0.0


@dataclass(frozen=True)
class ConcatItemDefinition:
    path: Path
    start: str | None = None
    end: str | None = None
    duration: str | None = None
    marker: str | None = None
    title: str | None = None
    title_start: str | None = None
    title_duration: str | None = None
    title_style: str | None = None
    audio_fade_in_seconds: float | None = None
    audio_fade_out_seconds: float | None = None
    spacer_seconds: float | None = None


@dataclass(frozen=True)
class CutListManifest:
    kind: str
    version: int
    sources: dict[str, SourceAsset]
    cuts: dict[str, CutDefinition]


@dataclass(frozen=True)
class TimelineManifest:
    kind: str
    version: int
    sources: dict[str, SourceAsset]
    cuts: dict[str, CutDefinition]
    sections: list[TimelineSectionDefinition]
    defaults: TimelineDefaults = field(default_factory=TimelineDefaults)
    output: OutputDefinition = field(default_factory=OutputDefinition)


@dataclass(frozen=True)
class ConcatPlaylistManifest:
    kind: str
    version: int
    items: list[ConcatItemDefinition]
    defaults: ConcatDefaults = field(default_factory=ConcatDefaults)
    title_styles: dict[str, TitleStyle] = field(default_factory=dict)
    output: OutputDefinition = field(default_factory=OutputDefinition)


PlaylistManifest = ConcatPlaylistManifest
PlaylistItem = ConcatItemDefinition
TimelineSection = TimelineSectionDefinition


@dataclass(frozen=True)
class CanvasManifest:
    kind: str
    version: int
    panels: list[Panel]
    canvas_size: tuple[int, int] = (4860, 2160)
    audio_mix: AudioMix | None = None
    finale: FinaleClip | None = None
    output: OutputDefinition = field(default_factory=OutputDefinition)


def load_json_document(path: Path | str) -> dict[str, Any]:
    resolved = Path(path).expanduser().resolve()
    with resolved.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Manifest root must be a JSON object")
    return payload


def _require_version(payload: dict[str, Any]) -> int:
    version = payload.get("version")
    if version != 1:
        raise ValueError("Manifest must declare version 1")
    return 1


def infer_manifest_kind(payload: dict[str, Any]) -> str:
    declared_kind = payload.get("kind")
    if isinstance(declared_kind, str) and declared_kind.strip():
        return declared_kind.strip()
    legacy_type = payload.get("type")
    if legacy_type == "reel" or "clips" in payload:
        return "playlist"
    if legacy_type == "canvas_edit" or "panels" in payload:
        return "canvas"
    if "items" in payload:
        return "playlist"
    if "sections" in payload:
        return "timeline"
    if "cuts" in payload and "sources" in payload:
        return "cut_list"
    raise ValueError(
        "Could not determine manifest kind. Expected cut_list, timeline, playlist, or canvas data."
    )


def normalize_manifest_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    kind = infer_manifest_kind(payload)
    normalized["kind"] = kind

    if kind == "playlist" and "items" not in normalized and "clips" in normalized:
        clips = normalized.pop("clips")
        if not isinstance(clips, list):
            raise ValueError("Legacy reel manifest 'clips' must be a list")
        normalized["items"] = [
            {
                "path": clip.get("input"),
                "marker": clip.get("title"),
                "title": clip.get("title"),
                "start": clip.get("start_ms", 0) / 1000.0 if clip.get("start_ms") is not None else None,
                "end": clip.get("end_ms", 0) / 1000.0 if clip.get("end_ms") is not None else None,
            }
            for clip in clips
        ]
        normalized["defaults"] = {
            "spacer_mode": "black",
            "spacer_seconds": float(normalized.get("gap_ms", 2000)) / 1000.0,
            "audio_fade_in_seconds": 0.0,
            "audio_fade_out_seconds": 0.0,
        }
        output_value = normalized.get("output")
        if isinstance(output_value, str):
            normalized["output"] = {"path": output_value}

    if kind == "canvas":
        output_value = normalized.get("output")
        if isinstance(output_value, str):
            normalized["output"] = {"path": output_value}

    return normalized


def _require_list(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        raise ValueError(f"Manifest must contain a non-empty '{key}' list")
    result: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError(f"Every item in '{key}' must be an object")
        result.append(item)
    return result


def _parse_sources(payload: dict[str, Any]) -> dict[str, SourceAsset]:
    sources: dict[str, SourceAsset] = {}
    for item in _require_list(payload, "sources"):
        source_id = item.get("id")
        source_path = item.get("path")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("Each source must define a non-empty string 'id'")
        if not isinstance(source_path, str) or not source_path.strip():
            raise ValueError("Each source must define a non-empty string 'path'")
        if source_id in sources:
            raise ValueError(f"Duplicate source id: {source_id}")
        sources[source_id] = SourceAsset(id=source_id, path=Path(source_path))
    return sources


def _parse_cuts(payload: dict[str, Any], sources: dict[str, SourceAsset]) -> dict[str, CutDefinition]:
    cuts: dict[str, CutDefinition] = {}
    for item in _require_list(payload, "cuts"):
        cut_id = item.get("id")
        source = item.get("source")
        if not isinstance(cut_id, str) or not cut_id.strip():
            raise ValueError("Each cut must define a non-empty string 'id'")
        if not isinstance(source, str) or source not in sources:
            raise ValueError(f"Cut '{cut_id}' references unknown source '{source}'")
        if cut_id in cuts:
            raise ValueError(f"Duplicate cut id: {cut_id}")

        start_seconds = parse_timecode(item.get("start")) or 0.0
        end_seconds = parse_timecode(item.get("end"))
        duration_seconds = parse_timecode(item.get("duration"))
        if end_seconds is not None and duration_seconds is not None:
            raise ValueError(f"Cut '{cut_id}' cannot define both 'end' and 'duration'")

        label = item.get("label")
        if label is not None and not isinstance(label, str):
            raise ValueError(f"Cut '{cut_id}' has a non-string 'label'")

        raw_tags = item.get("tags", [])
        if not isinstance(raw_tags, list) or not all(isinstance(tag, str) for tag in raw_tags):
            raise ValueError(f"Cut '{cut_id}' has invalid 'tags'")

        cuts[cut_id] = CutDefinition(
            id=cut_id,
            source=source,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            duration_seconds=duration_seconds,
            label=label,
            tags=tuple(raw_tags),
        )
    return cuts


def parse_cut_list_manifest(payload: dict[str, Any]) -> CutListManifest:
    normalized = normalize_manifest_payload(payload)
    version = _require_version(normalized)
    sources = _parse_sources(normalized)
    cuts = _parse_cuts(normalized, sources)
    return CutListManifest(kind="cut_list", version=version, sources=sources, cuts=cuts)


def parse_timeline_manifest(payload: dict[str, Any]) -> TimelineManifest:
    normalized = normalize_manifest_payload(payload)
    version = _require_version(normalized)
    sources = _parse_sources(normalized)
    cuts = _parse_cuts(normalized, sources)

    defaults_payload = normalized.get("defaults", {})
    if not isinstance(defaults_payload, dict):
        raise ValueError("'defaults' must be an object when provided")
    defaults = TimelineDefaults(
        gap_after_seconds=float(defaults_payload.get("gap_after_seconds", 0.0)),
        audio_fade_in_seconds=float(defaults_payload.get("audio_fade_in_seconds", 0.0)),
        audio_fade_out_seconds=float(defaults_payload.get("audio_fade_out_seconds", 0.0)),
    )

    sections_payload = _require_list(normalized, "sections")
    sections: list[TimelineSectionDefinition] = []
    for item in sections_payload:
        cut_id = item.get("cut")
        if not isinstance(cut_id, str) or cut_id not in cuts:
            raise ValueError(f"Timeline section references unknown cut '{cut_id}'")
        title = item.get("title")
        if title is not None and not isinstance(title, str):
            raise ValueError(f"Timeline section '{cut_id}' has a non-string 'title'")
        sections.append(
            TimelineSectionDefinition(
                cut=cut_id,
                title=title,
                gap_after_seconds=(
                    float(item["gap_after_seconds"]) if "gap_after_seconds" in item else None
                ),
                audio_fade_in_seconds=(
                    float(item["audio_fade_in_seconds"]) if "audio_fade_in_seconds" in item else None
                ),
                audio_fade_out_seconds=(
                    float(item["audio_fade_out_seconds"]) if "audio_fade_out_seconds" in item else None
                ),
            )
        )

    output_payload = normalized.get("output", {})
    if not isinstance(output_payload, dict):
        raise ValueError("'output' must be an object when provided")
    output_path = output_payload.get("path")
    output = OutputDefinition(path=Path(output_path) if isinstance(output_path, str) else None)

    return TimelineManifest(
        kind="timeline",
        version=version,
        sources=sources,
        cuts=cuts,
        sections=sections,
        defaults=defaults,
        output=output,
    )


def parse_concat_playlist_manifest(payload: dict[str, Any]) -> ConcatPlaylistManifest:
    normalized = normalize_manifest_payload(payload)
    version = _require_version(normalized)

    defaults_payload = normalized.get("defaults", {})
    if not isinstance(defaults_payload, dict):
        raise ValueError("'defaults' must be an object when provided")
    spacer_mode = defaults_payload.get("spacer_mode", "black")
    if not isinstance(spacer_mode, str) or not spacer_mode.strip():
        raise ValueError("'defaults.spacer_mode' must be a non-empty string when provided")
    defaults = ConcatDefaults(
        spacer_mode=spacer_mode,
        spacer_seconds=float(defaults_payload.get("spacer_seconds", 0.0)),
        audio_fade_in_seconds=float(defaults_payload.get("audio_fade_in_seconds", 0.0)),
        audio_fade_out_seconds=float(defaults_payload.get("audio_fade_out_seconds", 0.0)),
    )

    title_styles_payload = normalized.get("title_styles", {})
    if not isinstance(title_styles_payload, dict):
        raise ValueError("'title_styles' must be an object when provided")
    title_styles: dict[str, TitleStyle] = {}
    for style_name, raw_style in title_styles_payload.items():
        if not isinstance(style_name, str) or not style_name.strip():
            raise ValueError("Each title style name must be a non-empty string")
        if not isinstance(raw_style, dict):
            raise ValueError(f"Title style '{style_name}' must be an object")
        anchor = raw_style.get("anchor", "bottom-left")
        if not isinstance(anchor, str) or not anchor.strip():
            raise ValueError(f"Title style '{style_name}' must define a non-empty string 'anchor'")
        font_color = raw_style.get("font_color", "#FFFFFF")
        if not isinstance(font_color, str) or not font_color.strip():
            raise ValueError(f"Title style '{style_name}' must define a non-empty string 'font_color'")
        font_family = raw_style.get("font_family")
        if font_family is not None and not isinstance(font_family, str):
            raise ValueError(f"Title style '{style_name}' has a non-string 'font_family'")
        title_styles[style_name] = TitleStyle(
            anchor=anchor,
            offset_x=int(raw_style.get("offset_x", 80)),
            offset_y=int(raw_style.get("offset_y", 80)),
            font_size=int(raw_style.get("font_size", 42)),
            font_color=font_color,
            opacity=float(raw_style.get("opacity", 0.92)),
            font_family=font_family,
        )

    items_payload = _require_list(normalized, "items")
    items: list[ConcatItemDefinition] = []
    for item in items_payload:
        item_path = item.get("path")
        if not isinstance(item_path, str) or not item_path.strip():
            raise ValueError("Each concat playlist item must define a non-empty string 'path'")
        start = item.get("start")
        end = item.get("end")
        duration = item.get("duration")
        if start is not None:
            parse_timecode(start)
        if end is not None:
            parse_timecode(end)
        if duration is not None:
            parse_timecode(duration)
        if end is not None and duration is not None:
            raise ValueError("Concat playlist item cannot define both 'end' and 'duration'")

        marker = item.get("marker")
        if marker is not None and not isinstance(marker, str):
            raise ValueError("Concat playlist item 'marker' must be a string when provided")
        title = item.get("title")
        if title is not None and not isinstance(title, str):
            raise ValueError("Concat playlist item 'title' must be a string when provided")
        title_start = item.get("title_start")
        if title_start is not None:
            parse_timecode(title_start)
        title_duration = item.get("title_duration")
        if title_duration is not None:
            parse_timecode(title_duration)
        title_style = item.get("title_style")
        if title_style is not None:
            if not isinstance(title_style, str) or not title_style.strip():
                raise ValueError("Concat playlist item 'title_style' must be a non-empty string when provided")
            if title_style not in title_styles:
                raise ValueError(f"Concat playlist item references unknown title style '{title_style}'")

        items.append(
            ConcatItemDefinition(
                path=Path(item_path),
                start=str(start) if start is not None else None,
                end=str(end) if end is not None else None,
                duration=str(duration) if duration is not None else None,
                marker=marker,
                title=title,
                title_start=str(title_start) if title_start is not None else None,
                title_duration=str(title_duration) if title_duration is not None else None,
                title_style=title_style,
                audio_fade_in_seconds=(
                    float(item["audio_fade_in_seconds"]) if "audio_fade_in_seconds" in item else None
                ),
                audio_fade_out_seconds=(
                    float(item["audio_fade_out_seconds"]) if "audio_fade_out_seconds" in item else None
                ),
                spacer_seconds=float(item["spacer_seconds"]) if "spacer_seconds" in item else None,
            )
        )

    output_payload = normalized.get("output", {})
    if not isinstance(output_payload, dict):
        raise ValueError("'output' must be an object when provided")
    output_path = output_payload.get("path")
    output = OutputDefinition(path=Path(output_path) if isinstance(output_path, str) else None)

    return ConcatPlaylistManifest(
        kind="playlist",
        version=version,
        items=items,
        defaults=defaults,
        title_styles=title_styles,
        output=output,
    )


def parse_playlist_manifest(payload: dict[str, Any]) -> PlaylistManifest:
    return parse_concat_playlist_manifest(payload)


def parse_canvas_manifest(payload: dict[str, Any]) -> CanvasManifest:
    normalized = normalize_manifest_payload(payload)
    version = _require_version(normalized)

    raw_panels = normalized.get("panels")
    if not isinstance(raw_panels, list) or not raw_panels:
        raise ValueError("Canvas manifest must contain a non-empty 'panels' list")

    panels: list[Panel] = []
    for item in raw_panels:
        if not isinstance(item, dict):
            raise ValueError("Canvas panel entries must be objects")
        input_path = item.get("input")
        if not isinstance(input_path, str) or not input_path.strip():
            raise ValueError("Canvas panel must define a non-empty string 'input'")
        panels.append(
            Panel(
                input=input_path,
                speed=float(item.get("speed", 1.0)),
                position=str(item.get("position", "outer_left")),
                crop=str(item.get("crop", "full")),
            )
        )

    canvas_size_value = normalized.get("canvas_size", [4860, 2160])
    if not isinstance(canvas_size_value, (list, tuple)) or len(canvas_size_value) != 2:
        raise ValueError("'canvas_size' must be a 2-item list or tuple when provided")
    canvas_size = (int(canvas_size_value[0]), int(canvas_size_value[1]))

    audio_mix: AudioMix | None = None
    raw_audio = normalized.get("audio")
    if raw_audio is not None:
        if not isinstance(raw_audio, dict):
            raise ValueError("'audio' must be an object when provided")
        audio_mix = AudioMix.from_dict(raw_audio)

    finale: FinaleClip | None = None
    raw_finale = normalized.get("finale")
    if raw_finale is not None:
        if not isinstance(raw_finale, dict):
            raise ValueError("'finale' must be an object when provided")
        finale_input = raw_finale.get("input")
        if not isinstance(finale_input, str) or not finale_input.strip():
            raise ValueError("Canvas finale must define a non-empty string 'input'")
        finale = FinaleClip(
            input=finale_input,
            beats=int(raw_finale.get("beats", 8)),
            mode=str(raw_finale.get("mode", "full_width")),
        )

    output_payload = normalized.get("output", {})
    if not isinstance(output_payload, dict):
        raise ValueError("'output' must be an object when provided")
    output_path = output_payload.get("path")
    output = OutputDefinition(path=Path(output_path) if isinstance(output_path, str) else None)

    return CanvasManifest(
        kind="canvas",
        version=version,
        panels=panels,
        canvas_size=canvas_size,
        audio_mix=audio_mix,
        finale=finale,
        output=output,
    )


def load_manifest(path: Path | str) -> CutListManifest | TimelineManifest | PlaylistManifest | CanvasManifest:
    payload = load_json_document(path)
    return parse_manifest(payload)


def parse_manifest(payload: dict[str, Any]) -> CutListManifest | TimelineManifest | PlaylistManifest | CanvasManifest:
    kind = infer_manifest_kind(payload)
    if kind == "cut_list":
        return parse_cut_list_manifest(payload)
    if kind == "timeline":
        return parse_timeline_manifest(payload)
    if kind == "playlist":
        return parse_playlist_manifest(payload)
    if kind == "canvas":
        return parse_canvas_manifest(payload)
    raise ValueError(f"Unsupported manifest kind: {kind}")
