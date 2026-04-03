import json
from pathlib import Path

import pytest

from videoedit.cli import build_parser
from videoedit.operations import concat_videos
from videoedit.service import VideoEditingService


def test_concat_parser_collects_multiple_inputs() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "concat",
            "joined.mp4",
            "a.mp4",
            "b.mp4",
            "--start",
            "00:00:03",
            "--end",
            "00:00:10",
            "--spacer-seconds",
            "2",
            "--audio-fade-seconds",
            "0.5",
            "--markers",
        ]
    )

    assert args.command == "concat"
    assert args.output == "joined.mp4"
    assert args.inputs == ["a.mp4", "b.mp4"]
    assert args.start == "00:00:03"
    assert args.end == "00:00:10"
    assert args.spacer_seconds == 2.0
    assert args.audio_fade_seconds == 0.5
    assert args.markers is True


def test_concat_parser_accepts_input_dir() -> None:
    parser = build_parser()
    args = parser.parse_args(["concat", "joined.mp4", "--input-dir", "clips", "--json-preview", "--full-preview"])

    assert args.command == "concat"
    assert args.output == "joined.mp4"
    assert args.inputs == []
    assert args.input_dir == "clips"
    assert args.json_preview is True
    assert args.full_preview is True


def test_concat_parser_accepts_playlist() -> None:
    parser = build_parser()
    args = parser.parse_args(["concat", "joined.mp4", "--playlist", "playlist.json"])

    assert args.command == "concat"
    assert args.output == "joined.mp4"
    assert args.playlist == "playlist.json"


def test_concat_requires_two_inputs(tmp_path: Path) -> None:
    clip = tmp_path / "clip.mp4"
    clip.write_text("placeholder", encoding="utf-8")

    with pytest.raises(ValueError):
        concat_videos([clip], tmp_path / "out.mp4")


def test_concat_input_resolution_rejects_both_inputs_and_directory(tmp_path: Path) -> None:
    from videoedit.commands.concat import _resolve_input_paths

    with pytest.raises(ValueError):
        _resolve_input_paths(["a.mp4", "b.mp4"], str(tmp_path))


def test_concat_source_resolution_requires_exactly_one_source_mode(tmp_path: Path) -> None:
    from videoedit.commands.concat import _resolve_concat_inputs

    with pytest.raises(ValueError):
        _resolve_concat_inputs(
            inputs=["a.mp4", "b.mp4"],
            input_dir=str(tmp_path),
            playlist=None,
            output="out.mp4",
            start=None,
            end=None,
            spacer_seconds=0.0,
            audio_fade_seconds=0.0,
            markers=False,
            full_preview=False,
        )


def test_concat_input_resolution_uses_sorted_directory_files(tmp_path: Path) -> None:
    from videoedit.commands.concat import _resolve_input_paths

    (tmp_path / "b_clip.mp4").write_text("b", encoding="utf-8")
    (tmp_path / "a_clip.mp4").write_text("a", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignore", encoding="utf-8")

    resolved = _resolve_input_paths([], str(tmp_path))

    assert [Path(path).name for path in resolved] == ["a_clip.mp4", "b_clip.mp4"]


def test_concat_json_preview_builds_manifest_style_payload() -> None:
    from videoedit.commands.concat import _build_json_preview_payload

    payload = _build_json_preview_payload(
        input_paths=["clips\\b_clip.mp4", "clips\\a_clip.mp4"],
        output="joined.mp4",
        start="00:00:03",
        end="00:00:10",
        spacer_seconds=2.0,
        audio_fade_seconds=0.5,
        markers=True,
        full=False,
    )

    assert payload["version"] == 1
    assert "defaults" not in payload
    assert payload["items"][0]["start"] == "00:00:03"
    assert payload["items"][0]["end"] == "00:00:10"
    assert payload["items"][0]["marker"] in {"b clip", "clips\\b clip"}
    assert payload["output"]["path"] == "joined.mp4"


def test_concat_json_preview_full_includes_defaults_and_explicit_fields() -> None:
    from videoedit.commands.concat import _build_json_preview_payload

    payload = _build_json_preview_payload(
        input_paths=["clips\\clip.mp4"],
        output="joined.mp4",
        start=None,
        end=None,
        spacer_seconds=2.0,
        audio_fade_seconds=0.5,
        markers=False,
        full=True,
    )

    assert payload["defaults"]["spacer_mode"] == "black"
    assert payload["defaults"]["spacer_seconds"] == 2.0
    assert payload["defaults"]["audio_fade_in_seconds"] == 0.5
    assert payload["title_styles"]["default"]["anchor"] == "bottom-left"
    assert payload["items"][0]["start"] is None
    assert payload["items"][0]["end"] is None
    assert payload["items"][0]["marker"] is None
    assert payload["items"][0]["title"] is None
    assert payload["items"][0]["title_style"] == "default"
    assert payload["items"][0]["audio_fade_in_seconds"] == 0.5


def test_concat_playlist_resolution_uses_manifest_values(tmp_path: Path) -> None:
    from videoedit.commands.concat import _resolve_playlist_inputs

    playlist = tmp_path / "playlist.json"
    playlist.write_text(
        json.dumps(
            {
                "version": 1,
                "defaults": {
                    "spacer_seconds": 2.0,
                    "audio_fade_in_seconds": 0.5,
                    "audio_fade_out_seconds": 0.5,
                },
                "items": [
                    {
                        "path": "clips/a.mp4",
                        "start": "00:00:03",
                        "end": "00:00:10",
                        "marker": "Clip A",
                        "title": "Intro",
                        "title_start": 0.25,
                        "title_duration": 2.0,
                        "title_style": "default",
                    },
                    {
                        "path": "clips/b.mp4",
                        "start": "00:00:03",
                        "end": "00:00:10",
                        "marker": "Clip B",
                    },
                ],
                "title_styles": {
                    "default": {
                        "anchor": "bottom-left",
                        "offset_x": 80,
                        "offset_y": 80,
                        "font_size": 42,
                        "font_color": "#FFFFFF",
                        "opacity": 0.92,
                    }
                },
                "output": {"path": "playlist-output.mp4"},
            }
        ),
        encoding="utf-8",
    )

    resolved = _resolve_playlist_inputs(playlist, "fallback.mp4")

    assert resolved["input_paths"] == ["clips/a.mp4", "clips/b.mp4"]
    assert resolved["playlist_items"][0]["start"] == "00:00:03"
    assert resolved["playlist_items"][1]["end"] == "00:00:10"
    assert resolved["playlist_items"][0]["title"] == "Intro"
    assert resolved["playlist_items"][0]["title_style"] == "default"
    assert resolved["output_path"] == "playlist-output.mp4"
    assert resolved["start"] is None
    assert resolved["end"] is None
    assert resolved["spacer_seconds"] == 2.0
    assert resolved["audio_fade_seconds"] == 0.5
    assert resolved["markers"] is True
    assert "default" in resolved["title_styles"]


def test_concat_playlist_resolution_allows_per_item_start_values(tmp_path: Path) -> None:
    from videoedit.commands.concat import _resolve_playlist_inputs

    playlist = tmp_path / "playlist.json"
    playlist.write_text(
        json.dumps(
            {
                "version": 1,
                "items": [
                    {"path": "clips/a.mp4", "start": "00:00:03"},
                    {"path": "clips/b.mp4", "start": "00:00:04"},
                ],
            }
        ),
        encoding="utf-8",
    )

    resolved = _resolve_playlist_inputs(playlist, "fallback.mp4")

    assert resolved["playlist_items"][0]["start"] == "00:00:03"
    assert resolved["playlist_items"][1]["start"] == "00:00:04"


def test_concat_playlist_mode_builds_filtered_ffmpeg_graph_with_per_item_values(tmp_path: Path, monkeypatch) -> None:
    from videoedit.commands.concat import _resolve_playlist_inputs
    from videoedit.operations import concat_playlist

    clip_a = tmp_path / "clip_one.mp4"
    clip_b = tmp_path / "clip_two.mp4"
    clip_a.write_text("a", encoding="utf-8")
    clip_b.write_text("b", encoding="utf-8")
    captured: dict[str, list[str]] = {}
    playlist = tmp_path / "playlist.json"
    playlist.write_text(
        json.dumps(
            {
                "version": 1,
                "defaults": {
                    "spacer_seconds": 2.0,
                    "audio_fade_in_seconds": 0.25,
                    "audio_fade_out_seconds": 0.25,
                },
                "items": [
                    {
                        "path": str(clip_a),
                        "start": "00:00:01",
                        "end": "00:00:05",
                        "marker": "Clip One",
                        "title": "One",
                        "title_start": 0.25,
                        "title_duration": 1.5,
                        "title_style": "default",
                        "audio_fade_in_seconds": 0.5,
                    },
                    {
                        "path": str(clip_b),
                        "start": "00:00:02",
                        "duration": "3.0",
                        "marker": "Clip Two",
                        "audio_fade_out_seconds": 0.75,
                    },
                ],
                "title_styles": {
                    "default": {
                        "anchor": "bottom-left",
                        "offset_x": 40,
                        "offset_y": 50,
                        "font_size": 30,
                        "font_color": "#FFFFFF",
                        "opacity": 0.8,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    def fake_probe_media(self, input_path):  # type: ignore[no-untyped-def]
        return {"format": {"duration": "12.0"}}

    def fake_run_ffmpeg(args):  # type: ignore[no-untyped-def]
        captured["args"] = list(args)
        return None

    monkeypatch.setattr(VideoEditingService, "probe_media", fake_probe_media)
    monkeypatch.setattr("videoedit.service.run_ffmpeg", fake_run_ffmpeg)

    resolved = _resolve_playlist_inputs(playlist, "fallback.mp4")
    concat_playlist(
        items=resolved["playlist_items"],
        output_path=tmp_path / "out.mp4",
        spacer_seconds=float(resolved["spacer_seconds"]),
        audio_fade_seconds=float(resolved["audio_fade_seconds"]),
        title_styles=resolved["title_styles"],
    )

    command_text = " ".join(captured["args"])
    assert "trim=start=1.000:duration=4.000" in command_text
    assert "trim=start=2.000:duration=3.000" in command_text
    assert "afade=t=in:st=0:d=0.500" in command_text
    assert "afade=t=out:st=2.250:d=0.750" in command_text
    assert "drawtext=" in command_text
    assert "text='One'" in command_text


def test_concat_rejects_end_before_start(tmp_path: Path) -> None:
    clip_a = tmp_path / "clip-a.mp4"
    clip_b = tmp_path / "clip-b.mp4"
    clip_a.write_text("a", encoding="utf-8")
    clip_b.write_text("b", encoding="utf-8")

    with pytest.raises(ValueError):
        concat_videos([clip_a, clip_b], tmp_path / "out.mp4", start="10", end="5")


def test_concat_advanced_mode_builds_filtered_ffmpeg_graph(tmp_path: Path, monkeypatch) -> None:
    clip_a = tmp_path / "clip_one.mp4"
    clip_b = tmp_path / "clip_two.mp4"
    clip_a.write_text("a", encoding="utf-8")
    clip_b.write_text("b", encoding="utf-8")
    captured: dict[str, list[str]] = {}

    def fake_probe_media(self, input_path):  # type: ignore[no-untyped-def]
        return {"format": {"duration": "12.0"}}

    def fake_run_ffmpeg(args):  # type: ignore[no-untyped-def]
        captured["args"] = list(args)
        return None

    monkeypatch.setattr(VideoEditingService, "probe_media", fake_probe_media)
    monkeypatch.setattr("videoedit.service.run_ffmpeg", fake_run_ffmpeg)

    concat_videos(
        [clip_a, clip_b],
        tmp_path / "out.mp4",
        start="00:00:01",
        end="00:00:05",
        spacer_seconds=2.0,
        audio_fade_seconds=0.5,
        markers=True,
    )

    command = captured["args"]
    command_text = " ".join(command)

    assert "-filter_complex" in command
    assert "trim=start=1.000:duration=4.000" in command_text
    assert "tpad=stop_mode=add:stop_duration=2.000" in command_text
    assert "afade=t=in:st=0:d=0.500" in command_text
    assert "use_metadata_tags" in command
    assert "libx264" in command

