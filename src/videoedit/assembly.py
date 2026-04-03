from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TitleStyle:
    anchor: str = "bottom-left"
    offset_x: int = 80
    offset_y: int = 80
    font_size: int = 42
    font_color: str = "#FFFFFF"
    opacity: float = 0.92
    font_family: str | None = None


@dataclass(frozen=True)
class SectionTitleOverlay:
    text: str
    start_seconds: float = 0.0
    duration_seconds: float | None = None
    style: TitleStyle = TitleStyle()

@dataclass(frozen=True)
class TimelineSection:
    input_path: Path
    title: str
    duration_seconds: float
    start_seconds: float = 0.0
    gap_after_seconds: float = 0.0
    audio_fade_in_seconds: float = 0.0
    audio_fade_out_seconds: float = 0.0
    overlay_title: SectionTitleOverlay | None = None


@dataclass(frozen=True)
class AssemblyManifest:
    sections: list[TimelineSection]


@dataclass(frozen=True)
class AssemblyPlan:
    ffmpeg_args: list[str]
    metadata_path: Path


@dataclass(frozen=True)
class ResolvedSection:
    input_path: Path
    title: str
    start_seconds: float
    duration_seconds: float
    gap_after_seconds: float
    audio_fade_in_seconds: float
    audio_fade_out_seconds: float


def load_manifest(manifest_path: Path | str) -> dict[str, Any]:
    path = Path(manifest_path).expanduser().resolve()
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_metadata_text(sections: list[TimelineSection]) -> str:
    lines = [";FFMETADATA1", ""]
    elapsed_ms = 0
    for index, section in enumerate(sections):
        duration_ms = int(round(section.duration_seconds * 1000))
        lines.extend(
            [
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={elapsed_ms}",
                f"END={elapsed_ms + duration_ms}",
                f"title={section.title}",
                "",
            ]
        )
        elapsed_ms += duration_ms
        if index < len(sections) - 1:
            elapsed_ms += int(round(section.gap_after_seconds * 1000))
    return "\n".join(lines)


def write_metadata_file(sections: list[TimelineSection]) -> Path:
    metadata_text = build_metadata_text(sections)
    with tempfile.NamedTemporaryFile("w", suffix=".ffmeta", delete=False, encoding="utf-8") as handle:
        handle.write(metadata_text)
        return Path(handle.name)


def build_filter_complex(sections: list[TimelineSection]) -> str:
    video_chains: list[str] = []
    audio_chains: list[str] = []
    concat_inputs: list[str] = []

    for index, section in enumerate(sections):
        video_ops = [
            f"trim=start={section.start_seconds:.3f}:duration={section.duration_seconds:.3f}",
            "setpts=PTS-STARTPTS",
            "format=yuv420p",
        ]
        if section.overlay_title is not None:
            video_ops.append(_build_drawtext_filter(section.overlay_title, section.duration_seconds))
        audio_ops = [
            f"atrim=start={section.start_seconds:.3f}:duration={section.duration_seconds:.3f}",
            "asetpts=PTS-STARTPTS",
        ]

        fade_in_duration = min(section.audio_fade_in_seconds, max(section.duration_seconds, 0.0))
        if fade_in_duration > 0:
            audio_ops.append(f"afade=t=in:st=0:d={fade_in_duration:.3f}")

        fade_out_duration = min(section.audio_fade_out_seconds, max(section.duration_seconds, 0.0))
        if fade_out_duration > 0:
            fade_out_start = max(section.duration_seconds - fade_out_duration, 0.0)
            audio_ops.append(f"afade=t=out:st={fade_out_start:.3f}:d={fade_out_duration:.3f}")

        if section.gap_after_seconds > 0 and index < len(sections) - 1:
            video_ops.append(f"tpad=stop_mode=add:stop_duration={section.gap_after_seconds:.3f}")
            total_audio_duration = section.duration_seconds + section.gap_after_seconds
            audio_ops.append(f"apad=pad_dur={section.gap_after_seconds:.3f}")
            audio_ops.append(f"atrim=duration={total_audio_duration:.3f}")

        video_label = f"v{index}"
        audio_label = f"a{index}"
        video_chains.append(f"[{index}:v]{','.join(video_ops)}[{video_label}]")
        audio_chains.append(f"[{index}:a]{','.join(audio_ops)}[{audio_label}]")
        concat_inputs.append(f"[{video_label}][{audio_label}]")

    return ";".join(
        [
            *video_chains,
            *audio_chains,
            f"{''.join(concat_inputs)}concat=n={len(sections)}:v=1:a=1[outv][outa]",
        ]
    )


def _build_drawtext_filter(overlay: SectionTitleOverlay, section_duration_seconds: float) -> str:
    style = overlay.style
    x_expr, y_expr = _anchor_to_xy(style)
    end_seconds = section_duration_seconds
    if overlay.duration_seconds is not None:
        end_seconds = min(overlay.start_seconds + overlay.duration_seconds, section_duration_seconds)
    enable_expr = f"between(t\\,{overlay.start_seconds:.3f}\\,{end_seconds:.3f})"
    args = [
        f"text='{_escape_drawtext_text(overlay.text)}'",
        f"x={x_expr}",
        f"y={y_expr}",
        f"fontsize={style.font_size}",
        f"fontcolor={style.font_color}@{style.opacity:.2f}",
        f"enable='{enable_expr}'",
    ]
    if style.font_family:
        args.append(f"font='{_escape_drawtext_text(style.font_family)}'")
    return f"drawtext={':'.join(args)}"


def _anchor_to_xy(style: TitleStyle) -> tuple[str, str]:
    anchor = style.anchor.lower()
    horizontal, vertical = anchor.split("-", 1) if "-" in anchor else ("bottom", "left")
    if horizontal in {"top", "center", "bottom"} and vertical in {"left", "center", "right"}:
        row = horizontal
        column = vertical
    elif anchor in {"left", "center", "right"}:
        row = "bottom"
        column = anchor
    else:
        row = "bottom"
        column = "left"

    if column == "left":
        x_expr = str(style.offset_x)
    elif column == "center":
        x_expr = f"(w-text_w)/2+{style.offset_x}"
    else:
        x_expr = f"w-text_w-{style.offset_x}"

    if row == "top":
        y_expr = str(style.offset_y)
    elif row == "center":
        y_expr = f"(h-text_h)/2+{style.offset_y}"
    else:
        y_expr = f"h-text_h-{style.offset_y}"

    return x_expr, y_expr


def _escape_drawtext_text(value: str) -> str:
    escaped = value.replace("\\", "\\\\")
    escaped = escaped.replace(":", "\\:")
    escaped = escaped.replace("'", "\\'")
    escaped = escaped.replace("%", "\\%")
    return escaped


def normalize_title(raw_title: str | None, input_path: Path) -> str:
    if raw_title and raw_title.strip():
        return raw_title.strip()
    return input_path.stem


def parse_duration_from_probe(payload: dict[str, Any]) -> float:
    format_info = payload.get("format", {})
    duration_text = format_info.get("duration")
    if duration_text is None:
        raise ValueError("Could not determine media duration from ffprobe output")
    return float(duration_text)


def parse_timecode(value: str | int | float | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = value.strip()
    if not text:
        return None
    if ":" not in text:
        return float(text)

    parts = text.split(":")
    if len(parts) > 3:
        raise ValueError(f"Invalid timecode: {value}")

    seconds = 0.0
    for part in parts:
        seconds = (seconds * 60) + float(part)
    return seconds


def resolve_section_duration(
    source_duration_seconds: float,
    start_seconds: float,
    end_value: str | int | float | None,
    duration_value: str | int | float | None,
) -> float:
    end_seconds = parse_timecode(end_value)
    duration_seconds = parse_timecode(duration_value)

    if end_seconds is not None and duration_seconds is not None:
        raise ValueError("Section cannot define both 'end' and 'duration'")

    if duration_seconds is not None:
        resolved = duration_seconds
    elif end_seconds is not None:
        resolved = end_seconds - start_seconds
    else:
        resolved = source_duration_seconds - start_seconds

    if resolved <= 0:
        raise ValueError("Section duration must be greater than zero")
    return resolved
