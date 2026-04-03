import json
from pathlib import Path

import pytest

from videoedit.cli import build_parser
from videoedit.commands import validate
from videoedit.service import VideoEditingService


def test_validate_parser_accepts_manifest_path() -> None:
    parser = build_parser()
    args = parser.parse_args(["validate", "manifest.json"])

    assert args.command == "validate"
    assert args.manifest == "manifest.json"


def test_validate_manifest_accepts_cut_list_manifest(tmp_path: Path) -> None:
    clip = tmp_path / "clip.mp4"
    manifest_path = tmp_path / "cut-list.json"
    clip.write_text("placeholder", encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "version": 1,
                "sources": [{"id": "session", "path": "clip.mp4"}],
                "cuts": [{"id": "intro", "source": "session", "start": "00:00:01", "duration": "2.0"}],
            }
        ),
        encoding="utf-8",
    )

    result = VideoEditingService().validate_manifest(manifest_path)

    assert result.manifest_type == "cut-list"
    assert result.source_count == 1
    assert result.cut_count == 1
    assert result.section_count is None


def test_validate_manifest_accepts_timeline_manifest(tmp_path: Path) -> None:
    clip = tmp_path / "clip.mp4"
    manifest_path = tmp_path / "timeline.json"
    clip.write_text("placeholder", encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "version": 1,
                "sources": [{"id": "session", "path": "clip.mp4"}],
                "cuts": [{"id": "intro", "source": "session", "start": "00:00:01", "duration": "2.0"}],
                "sections": [{"cut": "intro", "title": "Intro"}],
            }
        ),
        encoding="utf-8",
    )

    result = VideoEditingService().validate_manifest(manifest_path)

    assert result.manifest_type == "timeline"
    assert result.source_count == 1
    assert result.cut_count == 1
    assert result.section_count == 1


def test_validate_manifest_accepts_concat_playlist_manifest(tmp_path: Path) -> None:
    clip_a = tmp_path / "clip-a.mp4"
    clip_b = tmp_path / "clip-b.mp4"
    manifest_path = tmp_path / "playlist.json"
    clip_a.write_text("a", encoding="utf-8")
    clip_b.write_text("b", encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "version": 1,
                "defaults": {"spacer_seconds": 2.0},
                "items": [
                    {"path": "clip-a.mp4", "start": "00:00:03", "marker": "Clip A"},
                    {"path": "clip-b.mp4", "duration": "3.0"},
                ],
            }
        ),
        encoding="utf-8",
    )

    result = VideoEditingService().validate_manifest(manifest_path)

    assert result.manifest_type == "concat-playlist"
    assert result.source_count == 2
    assert result.cut_count == 2
    assert result.section_count == 2


def test_validate_manifest_rejects_missing_source_file(tmp_path: Path) -> None:
    manifest_path = tmp_path / "timeline.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": 1,
                "sources": [{"id": "session", "path": "missing.mp4"}],
                "cuts": [{"id": "intro", "source": "session"}],
                "sections": [{"cut": "intro"}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError):
        VideoEditingService().validate_manifest(manifest_path)


def test_validate_command_returns_1_for_invalid_manifest(capsys, tmp_path: Path) -> None:
    manifest_path = tmp_path / "timeline.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": 1,
                "sources": [{"id": "session", "path": "missing.mp4"}],
                "cuts": [{"id": "intro", "source": "session"}],
                "sections": [{"cut": "intro"}],
            }
        ),
        encoding="utf-8",
    )

    exit_code = validate.handle(build_parser().parse_args(["validate", str(manifest_path)]))
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Invalid manifest:" in captured.err
    assert "missing.mp4" in captured.err

