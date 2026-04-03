import pytest

from videoedit.manifests import (
    parse_concat_playlist_manifest,
    parse_cut_list_manifest,
    parse_timeline_manifest,
)


def test_parse_cut_list_manifest_v1() -> None:
    manifest = parse_cut_list_manifest(
        {
            "version": 1,
            "sources": [{"id": "session", "path": "session.mp4"}],
            "cuts": [
                {
                    "id": "intro-look",
                    "source": "session",
                    "start": "00:00:05.000",
                    "end": "00:00:06.200",
                    "label": "Intro glance",
                    "tags": ["closeup", "beat"],
                }
            ],
        }
    )

    assert manifest.version == 1
    assert manifest.sources["session"].path.as_posix() == "session.mp4"
    assert manifest.cuts["intro-look"].start_seconds == 5.0
    assert manifest.cuts["intro-look"].end_seconds == 6.2
    assert manifest.cuts["intro-look"].tags == ("closeup", "beat")


def test_parse_timeline_manifest_v1() -> None:
    manifest = parse_timeline_manifest(
        {
            "version": 1,
            "sources": [{"id": "session", "path": "session.mp4"}],
            "cuts": [
                {
                    "id": "intro-look",
                    "source": "session",
                    "start": "00:00:05.000",
                    "duration": "1.5",
                }
            ],
            "defaults": {
                "gap_after_seconds": 0.15,
                "audio_fade_in_seconds": 0.04,
                "audio_fade_out_seconds": 0.05,
            },
            "sections": [{"cut": "intro-look", "title": "Intro", "gap_after_seconds": 0.25}],
            "output": {"path": "out.mp4"},
        }
    )

    assert manifest.defaults.gap_after_seconds == 0.15
    assert manifest.sections[0].cut == "intro-look"
    assert manifest.sections[0].gap_after_seconds == 0.25
    assert manifest.output.path.as_posix() == "out.mp4"


def test_parse_manifest_requires_version_1() -> None:
    with pytest.raises(ValueError):
        parse_cut_list_manifest({"version": 2, "sources": [], "cuts": []})


def test_parse_timeline_manifest_rejects_unknown_cut() -> None:
    with pytest.raises(ValueError):
        parse_timeline_manifest(
            {
                "version": 1,
                "sources": [{"id": "session", "path": "session.mp4"}],
                "cuts": [{"id": "intro-look", "source": "session"}],
                "sections": [{"cut": "missing"}],
            }
        )


def test_parse_concat_playlist_manifest_v1() -> None:
    manifest = parse_concat_playlist_manifest(
        {
            "version": 1,
            "defaults": {
                "spacer_mode": "black",
                "spacer_seconds": 2.0,
                "audio_fade_in_seconds": 0.5,
                "audio_fade_out_seconds": 0.5,
            },
            "title_styles": {
                "default": {
                    "anchor": "bottom-left",
                    "offset_x": 72,
                    "offset_y": 64,
                    "font_size": 40,
                    "font_color": "#FFFFFF",
                    "opacity": 0.9,
                }
            },
            "items": [
                {
                    "path": "clips/a.mp4",
                    "start": "00:00:03",
                    "end": "00:00:10",
                    "marker": "Clip A",
                    "title": "Opening",
                    "title_start": 0.5,
                    "title_duration": 2.5,
                    "title_style": "default",
                    "audio_fade_in_seconds": 0.5,
                },
                {
                    "path": "clips/b.mp4",
                    "duration": "3.0",
                    "spacer_seconds": 1.0,
                },
            ],
            "output": {"path": "playlist.mp4"},
        }
    )

    assert manifest.defaults.spacer_mode == "black"
    assert manifest.defaults.spacer_seconds == 2.0
    assert manifest.title_styles["default"].anchor == "bottom-left"
    assert manifest.items[0].path.as_posix() == "clips/a.mp4"
    assert manifest.items[0].start == "00:00:03"
    assert manifest.items[0].marker == "Clip A"
    assert manifest.items[0].title == "Opening"
    assert manifest.items[0].title_style == "default"
    assert manifest.items[1].duration == "3.0"
    assert manifest.items[1].spacer_seconds == 1.0
    assert manifest.output.path.as_posix() == "playlist.mp4"


def test_parse_concat_playlist_manifest_rejects_end_and_duration_together() -> None:
    with pytest.raises(ValueError):
        parse_concat_playlist_manifest(
            {
                "version": 1,
                "items": [
                    {
                        "path": "clips/a.mp4",
                        "end": "00:00:10",
                        "duration": "3.0",
                    },
                    {"path": "clips/b.mp4"},
                ],
            }
        )


def test_parse_concat_playlist_manifest_rejects_unknown_title_style() -> None:
    with pytest.raises(ValueError):
        parse_concat_playlist_manifest(
            {
                "version": 1,
                "title_styles": {
                    "default": {
                        "anchor": "bottom-left",
                    }
                },
                "items": [
                    {
                        "path": "clips/a.mp4",
                        "title": "Opening",
                        "title_style": "missing",
                    },
                    {"path": "clips/b.mp4"},
                ],
            }
        )

