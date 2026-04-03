import json
from pathlib import Path

from video_editing_cli.cli import build_parser
from video_editing_cli.service import VideoEditingService


def test_plan_parser_accepts_manifest_options() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "plan",
            "manifest.json",
            "output.mp4",
            "--gap-seconds",
            "2",
            "--audio-fade-seconds",
            "0.5",
        ]
    )

    assert args.command == "plan"
    assert args.manifest == "manifest.json"
    assert args.output == "output.mp4"
    assert args.gap_seconds == 2.0
    assert args.audio_fade_seconds == 0.5


def test_summarize_assembly_plan_returns_resolved_json_shape(tmp_path, monkeypatch) -> None:
    manifest_path = tmp_path / "manifest.json"
    clip = tmp_path / "clip.mp4"
    clip.write_text("x", encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "version": 1,
                "sources": [{"id": "session", "path": str(clip)}],
                "cuts": [{"id": "intro", "source": "session", "start": "00:00:01", "duration": "2.5"}],
                "defaults": {
                    "gap_after_seconds": 1.0,
                    "audio_fade_in_seconds": 0.25,
                    "audio_fade_out_seconds": 0.25,
                },
                "sections": [{"cut": "intro", "title": "Intro"}],
            }
        ),
        encoding="utf-8",
    )

    def fake_probe_media(self, input_path):  # type: ignore[no-untyped-def]
        return {"format": {"duration": "10.0"}}

    monkeypatch.setattr(VideoEditingService, "probe_media", fake_probe_media)

    summary = VideoEditingService().summarize_assembly_plan(
        manifest_path=manifest_path,
        output_path=tmp_path / "output.mp4",
        gap_seconds=2.0,
        audio_fade_seconds=0.5,
    )

    assert summary.section_count == 1
    assert summary.sections[0].title == "Intro"
    assert summary.sections[0].start_seconds == 1.0
    assert summary.sections[0].duration_seconds == 2.5
    assert summary.sections[0].gap_after_seconds == 2.0
    assert summary.sections[0].audio_fade_in_seconds == 0.5
    assert summary.sections[0].audio_fade_out_seconds == 0.5
    assert summary.output_path == (tmp_path / "output.mp4").resolve()
    assert "libx264" in summary.ffmpeg_args
