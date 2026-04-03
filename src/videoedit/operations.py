from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .assembly import TitleStyle
from .service import DEFAULT_SERVICE, ManifestValidationResult


def probe_media(input_path: Path) -> dict:
    return DEFAULT_SERVICE.probe_media(input_path)


def validate_manifest(manifest_path: Path) -> ManifestValidationResult:
    return DEFAULT_SERVICE.validate_manifest(manifest_path)


def load_manifest(manifest_path: Path) -> object:
    return DEFAULT_SERVICE.load_manifest(manifest_path)


def plan_assembly(
    manifest_path: Path,
    output_path: Path,
    gap_seconds: float | None = None,
    audio_fade_seconds: float | None = None,
    overwrite: bool = True,
) -> object:
    return DEFAULT_SERVICE.summarize_assembly_plan(
        manifest_path=manifest_path,
        output_path=output_path,
        gap_seconds=gap_seconds,
        audio_fade_seconds=audio_fade_seconds,
        overwrite=overwrite,
    )


def trim_video(
    input_path: Path,
    output_path: Path,
    start: str | None = None,
    end: str | None = None,
    duration: str | None = None,
    reencode: bool = False,
    overwrite: bool = True,
) -> Path:
    return DEFAULT_SERVICE.trim_video(
        input_path=input_path,
        output_path=output_path,
        start=start,
        end=end,
        duration=duration,
        reencode=reencode,
        overwrite=overwrite,
    )


def concat_videos(
    input_paths: Iterable[Path],
    output_path: Path,
    start: str | None = None,
    end: str | None = None,
    spacer_seconds: float = 0.0,
    audio_fade_seconds: float = 0.0,
    markers: bool = False,
    reencode: bool = False,
    overwrite: bool = True,
) -> Path:
    return DEFAULT_SERVICE.concat_videos(
        input_paths=input_paths,
        output_path=output_path,
        start=start,
        end=end,
        spacer_seconds=spacer_seconds,
        audio_fade_seconds=audio_fade_seconds,
        markers=markers,
        reencode=reencode,
        overwrite=overwrite,
    )


def concat_playlist(
    items: list[dict[str, object]],
    output_path: Path,
    spacer_seconds: float = 0.0,
    audio_fade_seconds: float = 0.0,
    title_styles: dict[str, TitleStyle] | None = None,
    overwrite: bool = True,
) -> Path:
    return DEFAULT_SERVICE.concat_playlist(
        items=items,
        output_path=output_path,
        spacer_seconds=spacer_seconds,
        audio_fade_seconds=audio_fade_seconds,
        title_styles=title_styles,
        overwrite=overwrite,
    )


def render_playlist(
    manifest_path: Path,
    output_path: Path | None = None,
    overwrite: bool = True,
) -> Path:
    return DEFAULT_SERVICE.render_playlist(
        manifest_path=manifest_path,
        output_path=output_path,
        overwrite=overwrite,
    )


def extract_audio(
    input_path: Path,
    output_path: Path,
    codec: str | None = None,
    overwrite: bool = True,
) -> Path:
    return DEFAULT_SERVICE.extract_audio(
        input_path=input_path,
        output_path=output_path,
        codec=codec,
        overwrite=overwrite,
    )


def normalize_video(
    input_path: Path,
    output_path: Path,
    width: int | None = None,
    height: int | None = None,
    fps: float | None = None,
) -> Path:
    return DEFAULT_SERVICE.normalize_video(
        input_path=input_path,
        output_path=output_path,
        width=width,
        height=height,
        fps=fps,
    )


def assemble_from_manifest(
    manifest_path: Path,
    output_path: Path,
    gap_seconds: float | None = None,
    audio_fade_seconds: float | None = None,
    overwrite: bool = True,
) -> Path:
    return DEFAULT_SERVICE.assemble_from_manifest(
        manifest_path=manifest_path,
        output_path=output_path,
        gap_seconds=gap_seconds,
        audio_fade_seconds=audio_fade_seconds,
        overwrite=overwrite,
    )


def render_timeline(
    manifest_path: Path,
    output_path: Path | None = None,
    overwrite: bool = True,
) -> Path:
    return DEFAULT_SERVICE.render_timeline(
        manifest_path=manifest_path,
        output_path=output_path,
        overwrite=overwrite,
    )


def render_canvas(
    manifest_path: Path,
    output_path: Path | None = None,
) -> Path:
    return DEFAULT_SERVICE.render_canvas(
        manifest_path=manifest_path,
        output_path=output_path,
    )


def plan_render(
    manifest_path: Path,
    output_path: Path | None = None,
    overwrite: bool = True,
) -> object:
    return DEFAULT_SERVICE.plan_render(
        manifest_path=manifest_path,
        output_path=output_path,
        overwrite=overwrite,
    )


def summarize_plan(
    manifest_path: Path,
    output_path: Path | None = None,
    overwrite: bool = True,
) -> object:
    return DEFAULT_SERVICE.summarize_plan(
        manifest_path=manifest_path,
        output_path=output_path,
        overwrite=overwrite,
    )
