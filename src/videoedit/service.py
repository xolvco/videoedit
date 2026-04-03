from __future__ import annotations

import json
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .assembly import (
    AssemblyManifest,
    AssemblyPlan,
    ResolvedSection,
    SectionTitleOverlay,
    TimelineSection,
    TitleStyle,
    build_filter_complex,
    normalize_title,
    parse_duration_from_probe,
    parse_timecode,
    resolve_section_duration,
    write_metadata_file,
)
from .ffmpeg import run_ffmpeg, run_ffprobe, validate_existing_file
from .layout import MultiPanelCanvas
from .manifests import (
    CanvasManifest,
    ConcatPlaylistManifest,
    CutListManifest,
    TimelineManifest,
    infer_manifest_kind,
    load_manifest as load_manifest_document,
    load_json_document,
    parse_manifest,
    parse_concat_playlist_manifest,
    parse_cut_list_manifest,
    parse_timeline_manifest,
)
from ._mediatools_legacy.video import normalize_video as legacy_normalize_video


@dataclass(frozen=True)
class FFmpegTools:
    ffmpeg: str = "ffmpeg"
    ffprobe: str = "ffprobe"


@dataclass(frozen=True)
class ManifestValidationResult:
    manifest_type: str
    manifest_path: Path
    source_count: int
    cut_count: int
    section_count: int | None = None


@dataclass(frozen=True)
class AssemblyPlanSummary:
    manifest_path: Path
    output_path: Path
    section_count: int
    sections: list[ResolvedSection]
    ffmpeg_args: list[str]


class VideoEditingService:
    """Reusable high-level interface for FFmpeg-backed workflows."""

    def __init__(self, tools: FFmpegTools | None = None) -> None:
        self.tools = tools or FFmpegTools()

    def validate_manifest(self, manifest_path: Path | str) -> ManifestValidationResult:
        resolved_manifest_path = Path(manifest_path).expanduser().resolve()
        payload = load_json_document(resolved_manifest_path)
        manifest = parse_manifest(payload)
        manifest_type = infer_manifest_kind(payload).replace("_", "-")
        section_count = None

        base_dir = resolved_manifest_path.parent
        if isinstance(manifest, ConcatPlaylistManifest):
            for item in manifest.items:
                source_path = item.path if item.path.is_absolute() else base_dir / item.path
                validate_existing_file(source_path)
            source_count = len(manifest.items)
            cut_count = len(manifest.items)
            section_count = len(manifest.items)
        elif isinstance(manifest, CanvasManifest):
            for panel in manifest.panels:
                panel_path = Path(panel.input)
                source_path = panel_path if panel_path.is_absolute() else base_dir / panel_path
                validate_existing_file(source_path)
            if manifest.finale is not None:
                finale_path = Path(manifest.finale.input)
                source_path = finale_path if finale_path.is_absolute() else base_dir / finale_path
                validate_existing_file(source_path)
            source_count = len(manifest.panels) + (1 if manifest.finale is not None else 0)
            cut_count = len(manifest.panels)
            section_count = len(manifest.panels)
        else:
            for source in manifest.sources.values():
                source_path = source.path if source.path.is_absolute() else base_dir / source.path
                validate_existing_file(source_path)
            source_count = len(manifest.sources)
            cut_count = len(manifest.cuts)
            if isinstance(manifest, TimelineManifest):
                section_count = len(manifest.sections)

        return ManifestValidationResult(
            manifest_type=manifest_type,
            manifest_path=resolved_manifest_path,
            source_count=source_count,
            cut_count=cut_count,
            section_count=section_count,
        )

    def load_manifest(
        self,
        manifest_path: Path | str,
    ) -> CutListManifest | TimelineManifest | ConcatPlaylistManifest | CanvasManifest:
        return load_manifest_document(manifest_path)

    def probe_media(self, input_path: Path | str) -> dict:
        source = validate_existing_file(Path(input_path))
        result = run_ffprobe(
            [
                self.tools.ffprobe,
                "-v",
                "error",
                "-show_format",
                "-show_streams",
                "-of",
                "json",
                str(source),
            ]
        )
        return json.loads(result.stdout)

    def trim_video(
        self,
        input_path: Path | str,
        output_path: Path | str,
        start: str | None = None,
        end: str | None = None,
        duration: str | None = None,
        reencode: bool = False,
        overwrite: bool = True,
    ) -> Path:
        source = validate_existing_file(Path(input_path))
        target = Path(output_path).expanduser().resolve()

        args = [self.tools.ffmpeg, "-hide_banner"]
        args.append("-y" if overwrite else "-n")
        if start:
            args.extend(["-ss", start])
        args.extend(["-i", str(source)])
        if end:
            args.extend(["-to", end])
        if duration:
            args.extend(["-t", duration])
        if reencode:
            args.extend(["-c:v", "libx264", "-c:a", "aac"])
        else:
            args.extend(["-c", "copy"])
        args.append(str(target))

        run_ffmpeg(args)
        return target

    def normalize_video(
        self,
        input_path: Path | str,
        output_path: Path | str,
        width: int | None = None,
        height: int | None = None,
        fps: float | None = None,
        video_codec: str = "libx264",
        audio_codec: str = "aac",
    ) -> Path:
        return legacy_normalize_video(
            input=input_path,
            output=output_path,
            width=width,
            height=height,
            fps=fps,
            video_codec=video_codec,
            audio_codec=audio_codec,
        )

    def concat_videos(
        self,
        input_paths: Iterable[Path | str],
        output_path: Path | str,
        start: str | None = None,
        end: str | None = None,
        spacer_seconds: float = 0.0,
        audio_fade_seconds: float = 0.0,
        markers: bool = False,
        reencode: bool = False,
        overwrite: bool = True,
    ) -> Path:
        sources = [validate_existing_file(Path(path)) for path in input_paths]
        if len(sources) < 2:
            raise ValueError("concat requires at least two input files")

        target = Path(output_path).expanduser().resolve()
        start_seconds = parse_timecode(start) or 0.0
        end_seconds = parse_timecode(end)
        advanced_concat = (
            start is not None
            or end is not None
            or spacer_seconds > 0
            or audio_fade_seconds > 0
            or markers
        )

        if end_seconds is not None and end_seconds <= start_seconds:
            raise ValueError("concat end time must be greater than start time")

        if advanced_concat:
            sections: list[TimelineSection] = []
            for source in sources:
                source_duration_seconds = parse_duration_from_probe(self.probe_media(source))
                duration_seconds = resolve_section_duration(
                    source_duration_seconds=source_duration_seconds,
                    start_seconds=start_seconds,
                    end_value=end_seconds,
                    duration_value=None,
                )
                sections.append(
                    TimelineSection(
                        input_path=source,
                        title=_normalize_marker_text(source.stem),
                        duration_seconds=duration_seconds,
                        start_seconds=start_seconds,
                        gap_after_seconds=spacer_seconds,
                        audio_fade_in_seconds=audio_fade_seconds,
                        audio_fade_out_seconds=audio_fade_seconds,
                    )
                )

            return self._render_concat_sections(
                sections=sections,
                output_path=target,
                markers=markers,
                overwrite=overwrite,
            )

        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as handle:
            for source in sources:
                normalized = source.as_posix().replace("'", "'\\''")
                handle.write(f"file '{normalized}'\n")
            list_path = Path(handle.name)

        try:
            args = [
                self.tools.ffmpeg,
                "-hide_banner",
                "-y" if overwrite else "-n",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_path),
            ]
            if reencode:
                args.extend(["-c:v", "libx264", "-c:a", "aac"])
            else:
                args.extend(["-c", "copy"])
            args.append(str(target))
            run_ffmpeg(args)
            return target
        finally:
            list_path.unlink(missing_ok=True)

    def concat_playlist(
        self,
        items: Iterable[dict[str, object]],
        output_path: Path | str,
        spacer_seconds: float = 0.0,
        audio_fade_seconds: float = 0.0,
        title_styles: dict[str, TitleStyle] | None = None,
        overwrite: bool = True,
    ) -> Path:
        raw_items = list(items)
        if len(raw_items) < 2:
            raise ValueError("concat playlist requires at least two items")

        sections: list[TimelineSection] = []
        markers = False
        resolved_title_styles = title_styles or {}
        for item in raw_items:
            source = validate_existing_file(Path(str(item["path"])))
            marker_text = item.get("marker")
            if marker_text is not None:
                if not isinstance(marker_text, str):
                    raise ValueError("Playlist item marker must be a string when provided")
                title = marker_text.strip() or _normalize_marker_text(source.stem)
                markers = True
            else:
                title = _normalize_marker_text(source.stem)

            start_seconds = parse_timecode(item.get("start")) or 0.0
            end_value = item.get("end")
            duration_value = item.get("duration")
            source_duration_seconds = parse_duration_from_probe(self.probe_media(source))
            duration_seconds = resolve_section_duration(
                source_duration_seconds=source_duration_seconds,
                start_seconds=start_seconds,
                end_value=end_value,
                duration_value=duration_value,
            )
            section_spacer_seconds = float(item.get("spacer_seconds", spacer_seconds))
            fade_in_seconds = float(item.get("audio_fade_in_seconds", audio_fade_seconds))
            fade_out_seconds = float(item.get("audio_fade_out_seconds", audio_fade_seconds))
            overlay_title = self._build_overlay_title(
                item=item,
                resolved_title_styles=resolved_title_styles,
                section_duration_seconds=duration_seconds,
            )
            sections.append(
                TimelineSection(
                    input_path=source,
                    title=title,
                    duration_seconds=duration_seconds,
                    start_seconds=start_seconds,
                    gap_after_seconds=section_spacer_seconds,
                    audio_fade_in_seconds=fade_in_seconds,
                    audio_fade_out_seconds=fade_out_seconds,
                    overlay_title=overlay_title,
                )
            )

        return self._render_concat_sections(
            sections=sections,
            output_path=output_path,
            markers=markers,
            overwrite=overwrite,
        )

    def _render_concat_sections(
        self,
        sections: list[TimelineSection],
        output_path: Path | str,
        markers: bool,
        overwrite: bool,
    ) -> Path:
        target = Path(output_path).expanduser().resolve()
        metadata_path: Path | None = write_metadata_file(sections) if markers else None
        ffmpeg_args = [self.tools.ffmpeg, "-hide_banner", "-y" if overwrite else "-n"]
        for section in sections:
            ffmpeg_args.extend(["-i", str(section.input_path)])
        if metadata_path is not None:
            ffmpeg_args.extend(["-i", str(metadata_path)])
        ffmpeg_args.extend(
            [
                "-filter_complex",
                build_filter_complex(sections),
                "-map",
                "[outv]",
                "-map",
                "[outa]",
            ]
        )
        if metadata_path is not None:
            ffmpeg_args.extend(
                [
                    "-map_metadata",
                    str(len(sections)),
                    "-movflags",
                    "use_metadata_tags",
                ]
            )
        ffmpeg_args.extend(["-c:v", "libx264", "-c:a", "aac", str(target)])

        try:
            run_ffmpeg(ffmpeg_args)
            return target
        finally:
            if metadata_path is not None:
                metadata_path.unlink(missing_ok=True)

    def extract_audio(
        self,
        input_path: Path | str,
        output_path: Path | str,
        codec: str | None = None,
        overwrite: bool = True,
    ) -> Path:
        source = validate_existing_file(Path(input_path))
        target = Path(output_path).expanduser().resolve()

        args = [
            self.tools.ffmpeg,
            "-hide_banner",
            "-y" if overwrite else "-n",
            "-i",
            str(source),
            "-vn",
        ]
        if codec:
            args.extend(["-c:a", codec])
        args.append(str(target))

        run_ffmpeg(args)
        return target

    def build_assembly_manifest(
        self,
        manifest_path: Path | str,
        gap_seconds: float | None = None,
        audio_fade_seconds: float | None = None,
    ) -> AssemblyManifest:
        payload = load_json_document(manifest_path)
        timeline_manifest = parse_timeline_manifest(payload)
        sections: list[TimelineSection] = []
        for item in timeline_manifest.sections:
            cut = timeline_manifest.cuts[item.cut]
            source_asset = timeline_manifest.sources[cut.source]
            input_path = validate_existing_file(source_asset.path)
            title = normalize_title(item.title or cut.label, input_path)
            source_duration_seconds = parse_duration_from_probe(self.probe_media(input_path))
            duration_seconds = resolve_section_duration(
                source_duration_seconds=source_duration_seconds,
                start_seconds=cut.start_seconds,
                end_value=cut.end_seconds,
                duration_value=cut.duration_seconds,
            )
            resolved_gap = timeline_manifest.defaults.gap_after_seconds
            if item.gap_after_seconds is not None:
                resolved_gap = item.gap_after_seconds
            resolved_fade_in = timeline_manifest.defaults.audio_fade_in_seconds
            if item.audio_fade_in_seconds is not None:
                resolved_fade_in = item.audio_fade_in_seconds
            resolved_fade_out = timeline_manifest.defaults.audio_fade_out_seconds
            if item.audio_fade_out_seconds is not None:
                resolved_fade_out = item.audio_fade_out_seconds
            sections.append(
                TimelineSection(
                    input_path=input_path,
                    title=title,
                    duration_seconds=duration_seconds,
                    start_seconds=cut.start_seconds,
                    gap_after_seconds=resolved_gap,
                    audio_fade_in_seconds=resolved_fade_in,
                    audio_fade_out_seconds=resolved_fade_out,
                )
            )
        if gap_seconds is not None or audio_fade_seconds is not None:
            override_gap = gap_seconds if gap_seconds is not None else None
            override_fade = audio_fade_seconds if audio_fade_seconds is not None else None
            sections = [
                TimelineSection(
                    input_path=section.input_path,
                    title=section.title,
                    duration_seconds=section.duration_seconds,
                    start_seconds=section.start_seconds,
                    gap_after_seconds=section.gap_after_seconds if override_gap is None else override_gap,
                    audio_fade_in_seconds=(
                        section.audio_fade_in_seconds if override_fade is None else override_fade
                    ),
                    audio_fade_out_seconds=(
                        section.audio_fade_out_seconds if override_fade is None else override_fade
                    ),
                )
                for section in sections
            ]
        return AssemblyManifest(sections=sections)

    def build_assembly_plan(
        self,
        manifest_path: Path | str,
        output_path: Path | str,
        gap_seconds: float | None = None,
        audio_fade_seconds: float | None = None,
        overwrite: bool = True,
        ) -> AssemblyPlan:
        manifest = self.build_assembly_manifest(
            manifest_path=manifest_path,
            gap_seconds=gap_seconds,
            audio_fade_seconds=audio_fade_seconds,
        )
        target = Path(output_path).expanduser().resolve()
        metadata_path = write_metadata_file(manifest.sections)
        ffmpeg_args = [self.tools.ffmpeg, "-hide_banner", "-y" if overwrite else "-n"]

        for section in manifest.sections:
            ffmpeg_args.extend(["-i", str(section.input_path)])

        ffmpeg_args.extend(["-i", str(metadata_path)])
        ffmpeg_args.extend(
            [
                "-filter_complex",
                build_filter_complex(manifest.sections),
                "-map",
                "[outv]",
                "-map",
                "[outa]",
                "-map_metadata",
                str(len(manifest.sections)),
                "-movflags",
                "use_metadata_tags",
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                str(target),
            ]
        )
        return AssemblyPlan(ffmpeg_args=ffmpeg_args, metadata_path=metadata_path)

    def summarize_assembly_plan(
        self,
        manifest_path: Path | str,
        output_path: Path | str,
        gap_seconds: float | None = None,
        audio_fade_seconds: float | None = None,
        overwrite: bool = True,
    ) -> AssemblyPlanSummary:
        resolved_manifest_path = Path(manifest_path).expanduser().resolve()
        target = Path(output_path).expanduser().resolve()
        manifest = self.build_assembly_manifest(
            manifest_path=resolved_manifest_path,
            gap_seconds=gap_seconds,
            audio_fade_seconds=audio_fade_seconds,
        )
        plan = self.build_assembly_plan(
            manifest_path=resolved_manifest_path,
            output_path=target,
            gap_seconds=gap_seconds,
            audio_fade_seconds=audio_fade_seconds,
            overwrite=overwrite,
        )
        try:
            sections = [
                ResolvedSection(
                    input_path=section.input_path,
                    title=section.title,
                    start_seconds=section.start_seconds,
                    duration_seconds=section.duration_seconds,
                    gap_after_seconds=section.gap_after_seconds,
                    audio_fade_in_seconds=section.audio_fade_in_seconds,
                    audio_fade_out_seconds=section.audio_fade_out_seconds,
                )
                for section in manifest.sections
            ]
            return AssemblyPlanSummary(
                manifest_path=resolved_manifest_path,
                output_path=target,
                section_count=len(sections),
                sections=sections,
                ffmpeg_args=plan.ffmpeg_args,
            )
        finally:
            plan.metadata_path.unlink(missing_ok=True)

    def _build_overlay_title(
        self,
        item: dict[str, object],
        resolved_title_styles: dict[str, TitleStyle],
        section_duration_seconds: float,
    ) -> SectionTitleOverlay | None:
        raw_title = item.get("title")
        if raw_title is None:
            return None
        if not isinstance(raw_title, str):
            raise ValueError("Playlist item title must be a string when provided")
        title_text = raw_title.strip()
        if not title_text:
            return None

        style_name = item.get("title_style")
        style = TitleStyle()
        if style_name is not None:
            if not isinstance(style_name, str):
                raise ValueError("Playlist item title_style must be a string when provided")
            if style_name not in resolved_title_styles:
                raise ValueError(f"Playlist item references unknown title style '{style_name}'")
            style = resolved_title_styles[style_name]
        elif "default" in resolved_title_styles:
            style = resolved_title_styles["default"]

        title_start_seconds = parse_timecode(item.get("title_start")) or 0.0
        title_duration_value = item.get("title_duration")
        title_duration_seconds = parse_timecode(title_duration_value) if title_duration_value is not None else None

        if title_start_seconds < 0:
            raise ValueError("Playlist item title_start must be zero or greater")
        if title_duration_seconds is not None and title_duration_seconds <= 0:
            raise ValueError("Playlist item title_duration must be greater than zero")
        if title_start_seconds >= section_duration_seconds:
            return None

        return SectionTitleOverlay(
            text=title_text,
            start_seconds=title_start_seconds,
            duration_seconds=title_duration_seconds,
            style=style,
        )

    def assemble_from_manifest(
        self,
        manifest_path: Path | str,
        output_path: Path | str,
        gap_seconds: float | None = None,
        audio_fade_seconds: float | None = None,
        overwrite: bool = True,
    ) -> Path:
        plan = self.build_assembly_plan(
            manifest_path=manifest_path,
            output_path=output_path,
            gap_seconds=gap_seconds,
            audio_fade_seconds=audio_fade_seconds,
            overwrite=overwrite,
        )
        try:
            run_ffmpeg(plan.ffmpeg_args)
            return Path(output_path).expanduser().resolve()
        finally:
            plan.metadata_path.unlink(missing_ok=True)

    def render_timeline(
        self,
        manifest_path: Path | str,
        output_path: Path | str | None = None,
        gap_seconds: float | None = None,
        audio_fade_seconds: float | None = None,
        overwrite: bool = True,
    ) -> Path:
        target_output = output_path
        if target_output is None:
            manifest = parse_timeline_manifest(load_json_document(manifest_path))
            if manifest.output.path is None:
                raise ValueError("Timeline manifest does not define output.path and no output path was provided")
            target_output = manifest.output.path
        return self.assemble_from_manifest(
            manifest_path=manifest_path,
            output_path=target_output,
            gap_seconds=gap_seconds,
            audio_fade_seconds=audio_fade_seconds,
            overwrite=overwrite,
        )

    def render_playlist(
        self,
        manifest_path: Path | str,
        output_path: Path | str | None = None,
        overwrite: bool = True,
    ) -> Path:
        resolved_manifest_path = Path(manifest_path).expanduser().resolve()
        manifest = parse_concat_playlist_manifest(load_json_document(resolved_manifest_path))
        resolved_items: list[dict[str, object]] = []
        for item in manifest.items:
            item_path = item.path if item.path.is_absolute() else resolved_manifest_path.parent / item.path
            resolved_item: dict[str, object] = {"path": str(item_path)}
            for field_name in (
                "marker",
                "title",
                "title_start",
                "title_duration",
                "title_style",
                "start",
                "end",
                "duration",
            ):
                value = getattr(item, field_name)
                if value is not None:
                    resolved_item[field_name] = value
            if item.audio_fade_in_seconds is not None:
                resolved_item["audio_fade_in_seconds"] = item.audio_fade_in_seconds
            if item.audio_fade_out_seconds is not None:
                resolved_item["audio_fade_out_seconds"] = item.audio_fade_out_seconds
            if item.spacer_seconds is not None:
                resolved_item["spacer_seconds"] = item.spacer_seconds
            resolved_items.append(resolved_item)

        target_output = output_path or manifest.output.path
        if target_output is None:
            raise ValueError("Playlist manifest does not define output.path and no output path was provided")
        return self.concat_playlist(
            items=resolved_items,
            output_path=target_output,
            spacer_seconds=manifest.defaults.spacer_seconds,
            audio_fade_seconds=manifest.defaults.audio_fade_in_seconds,
            title_styles=manifest.title_styles,
            overwrite=overwrite,
        )

    def render_canvas(
        self,
        manifest_path: Path | str,
        output_path: Path | str | None = None,
    ) -> Path:
        resolved_manifest_path = Path(manifest_path).expanduser().resolve()
        payload = load_json_document(resolved_manifest_path)
        manifest = parse_manifest(payload)
        if not isinstance(manifest, CanvasManifest):
            raise ValueError("render_canvas requires a canvas manifest")

        normalized_payload = dict(payload)
        if "type" not in normalized_payload:
            normalized_payload["type"] = "canvas_edit"
        if "version" not in normalized_payload:
            normalized_payload["version"] = "1.0"
        canvas = MultiPanelCanvas.from_dict(normalized_payload)
        target_output = output_path or manifest.output.path
        if target_output is None:
            raise ValueError("Canvas manifest does not define output.path and no output path was provided")
        return canvas.render(target_output)

    def plan_render(
        self,
        manifest_path: Path | str,
        output_path: Path | str | None = None,
        overwrite: bool = True,
    ) -> object:
        payload = load_json_document(manifest_path)
        kind = infer_manifest_kind(payload)
        if kind == "timeline":
            manifest = parse_timeline_manifest(payload)
            target_output = output_path or manifest.output.path
            if target_output is None:
                raise ValueError("Timeline manifest does not define output.path and no output path was provided")
            return self.summarize_assembly_plan(manifest_path=manifest_path, output_path=target_output, overwrite=overwrite)
        if kind == "playlist":
            manifest = parse_concat_playlist_manifest(payload)
            return {
                "kind": "playlist",
                "version": manifest.version,
                "item_count": len(manifest.items),
                "output_path": str(output_path or manifest.output.path or ""),
                "spacer_seconds": manifest.defaults.spacer_seconds,
            }
        if kind == "canvas":
            manifest = parse_manifest(payload)
            assert isinstance(manifest, CanvasManifest)
            return {
                "kind": "canvas",
                "version": manifest.version,
                "panel_count": len(manifest.panels),
                "output_path": str(output_path or manifest.output.path or ""),
                "canvas_size": list(manifest.canvas_size),
            }
        return self.validate_manifest(manifest_path)

    def summarize_plan(
        self,
        manifest_path: Path | str,
        output_path: Path | str | None = None,
        overwrite: bool = True,
    ) -> object:
        return self.plan_render(manifest_path=manifest_path, output_path=output_path, overwrite=overwrite)


DEFAULT_SERVICE = VideoEditingService()


def _normalize_marker_text(raw_text: str) -> str:
    collapsed = re.sub(r"[_-]+", " ", raw_text)
    collapsed = re.sub(r"\s+", " ", collapsed)
    return collapsed.strip()
