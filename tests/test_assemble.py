import json
from pathlib import Path

import pytest

from videoedit.assembly import (
    build_filter_complex,
    build_metadata_text,
    parse_timecode,
    resolve_section_duration,
)
from videoedit.assembly import TimelineSection
from videoedit.cli import build_parser
from videoedit.service import VideoEditingService


def test_assemble_parser_accepts_manifest_options() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "assemble",
            "manifest.json",
            "output.mp4",
            "--gap-seconds",
            "2",
            "--audio-fade-seconds",
            "0.5",
        ]
    )

    assert args.command == "assemble"
    assert args.manifest == "manifest.json"
    assert args.output == "output.mp4"
    assert args.gap_seconds == 2.0
    assert args.audio_fade_seconds == 0.5


def test_build_metadata_text_creates_titled_chapters() -> None:
    text = build_metadata_text(
        [
            TimelineSection(input_path=Path("intro.mp4"), title="Intro", duration_seconds=5.0, gap_after_seconds=2.0),
            TimelineSection(input_path=Path("main.mp4"), title="Main", duration_seconds=10.0),
        ]
    )

    assert "title=Intro" in text
    assert "START=7000" in text
    assert "title=Main" in text


def test_build_filter_complex_adds_gap_and_fades() -> None:
    filter_complex = build_filter_complex(
        [
            TimelineSection(
                input_path=Path("intro.mp4"),
                title="Intro",
                start_seconds=1.0,
                duration_seconds=5.0,
                gap_after_seconds=2.0,
                audio_fade_in_seconds=0.5,
                audio_fade_out_seconds=0.5,
            ),
            TimelineSection(
                input_path=Path("main.mp4"),
                title="Main",
                start_seconds=10.0,
                duration_seconds=10.0,
                audio_fade_in_seconds=0.5,
                audio_fade_out_seconds=0.5,
            ),
        ]
    )

    assert "trim=start=1.000:duration=5.000" in filter_complex
    assert "atrim=start=10.000:duration=10.000" in filter_complex
    assert "tpad=stop_mode=add:stop_duration=2.000" in filter_complex
    assert "afade=t=in:st=0:d=0.500" in filter_complex
    assert "concat=n=2:v=1:a=1[outv][outa]" in filter_complex


def test_parse_timecode_accepts_human_readable_values() -> None:
    assert parse_timecode("75.5") == 75.5
    assert parse_timecode("00:01:15.5") == 75.5
    assert parse_timecode(12) == 12.0


def test_resolve_section_duration_supports_end_or_duration() -> None:
    assert resolve_section_duration(120.0, 5.0, "00:00:12.5", None) == 7.5
    assert resolve_section_duration(120.0, 5.0, None, "7.5") == 7.5
    assert resolve_section_duration(120.0, 5.0, None, None) == 115.0


def test_resolve_section_duration_rejects_conflicting_values() -> None:
    with pytest.raises(ValueError):
        resolve_section_duration(120.0, 5.0, "10", "3")


def test_build_assembly_manifest_uses_titles_and_overrides(tmp_path, monkeypatch) -> None:
    manifest_path = tmp_path / "manifest.json"
    clip_a = tmp_path / "clip-a.mp4"
    clip_b = tmp_path / "clip-b.mp4"
    clip_a.write_text("a", encoding="utf-8")
    clip_b.write_text("b", encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "version": 1,
                "sources": [
                    {"id": "a", "path": str(clip_a)},
                    {"id": "b", "path": str(clip_b)},
                ],
                "cuts": [
                    {"id": "cut-a", "source": "a", "start": "00:00:01", "end": "00:00:03.5", "label": "Clip A"},
                    {"id": "cut-b", "source": "b", "start": 2, "duration": "1.25"},
                ],
                "defaults": {
                    "gap_after_seconds": 1.0,
                    "audio_fade_in_seconds": 0.25,
                    "audio_fade_out_seconds": 0.25,
                },
                "sections": [
                    {"cut": "cut-a", "title": "Clip A"},
                    {"cut": "cut-b", "audio_fade_in_seconds": 0.75},
                ],
                "output": {"path": "out.mp4"},
            }
        ),
        encoding="utf-8",
    )

    def fake_probe_media(self, input_path):  # type: ignore[no-untyped-def]
        return {"format": {"duration": "3.5"}}

    monkeypatch.setattr(VideoEditingService, "probe_media", fake_probe_media)

    manifest = VideoEditingService().build_assembly_manifest(
        manifest_path=manifest_path,
        gap_seconds=2.0,
        audio_fade_seconds=0.5,
    )

    assert manifest.sections[0].title == "Clip A"
    assert manifest.sections[1].title == "clip-b"
    assert manifest.sections[0].start_seconds == 1.0
    assert manifest.sections[0].duration_seconds == 2.5
    assert manifest.sections[0].gap_after_seconds == 2.0
    assert manifest.sections[0].audio_fade_in_seconds == 0.5
    assert manifest.sections[0].audio_fade_out_seconds == 0.5
    assert manifest.sections[1].start_seconds == 2.0
    assert manifest.sections[1].duration_seconds == 1.25
    assert manifest.sections[1].gap_after_seconds == 2.0
    assert manifest.sections[1].audio_fade_in_seconds == 0.5
    assert manifest.sections[1].audio_fade_out_seconds == 0.5

