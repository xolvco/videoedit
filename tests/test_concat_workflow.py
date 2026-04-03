import json
from pathlib import Path

from videoedit.cli import main
from videoedit.commands.concat import _build_json_preview_payload
from videoedit.assembly import build_metadata_text
from videoedit.service import VideoEditingService


def test_concat_workflow_preview_to_playlist_render(tmp_path: Path, monkeypatch, capsys) -> None:
    clip_a = tmp_path / "clip_one.mp4"
    clip_b = tmp_path / "clip_two.mp4"
    clip_a.write_text("a", encoding="utf-8")
    clip_b.write_text("b", encoding="utf-8")

    preview_payload = _build_json_preview_payload(
        input_paths=[str(clip_a), str(clip_b)],
        output="playlist-output.mp4",
        start="00:00:01",
        end=None,
        spacer_seconds=2.0,
        audio_fade_seconds=0.5,
        markers=True,
        full=True,
    )
    preview_payload["items"][0]["marker"] = "Opening"
    preview_payload["items"][1]["duration"] = "3.0"
    preview_payload["items"][1]["audio_fade_out_seconds"] = 0.75

    playlist_path = tmp_path / "playlist.json"
    playlist_path.write_text(json.dumps(preview_payload), encoding="utf-8")
    captured: dict[str, list[str]] = {}
    metadata_text: dict[str, str] = {}

    def fake_probe_media(self, input_path):  # type: ignore[no-untyped-def]
        return {"format": {"duration": "12.0"}}

    def fake_run_ffmpeg(args):  # type: ignore[no-untyped-def]
        captured["args"] = list(args)
        return None

    def fake_write_metadata_file(sections):  # type: ignore[no-untyped-def]
        metadata_path = tmp_path / "chapters.ffmeta"
        metadata_text["value"] = build_metadata_text(sections)
        metadata_path.write_text(metadata_text["value"], encoding="utf-8")
        return metadata_path

    monkeypatch.setattr(VideoEditingService, "probe_media", fake_probe_media)
    monkeypatch.setattr("videoedit.service.run_ffmpeg", fake_run_ffmpeg)
    monkeypatch.setattr("videoedit.service.write_metadata_file", fake_write_metadata_file)

    validate_exit = main(["validate", str(playlist_path)])
    concat_exit = main(["concat", str(tmp_path / "out.mp4"), "--playlist", str(playlist_path)])
    captured_output = capsys.readouterr()
    command_text = " ".join(captured["args"])

    assert validate_exit == 0
    assert concat_exit == 0
    assert "Valid concat-playlist manifest" in captured_output.out
    assert "trim=start=1.000:duration=11.000" in command_text
    assert "trim=start=1.000:duration=3.000" in command_text
    assert "title=Opening" in metadata_text["value"]

