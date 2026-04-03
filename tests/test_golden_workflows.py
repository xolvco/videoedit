from pathlib import Path

from videoedit.service import VideoEditingService


FIXTURES_DIR = Path(__file__).parent / "fixtures"
MANIFESTS_DIR = FIXTURES_DIR / "manifests"


def _fixture_path(name: str) -> Path:
    return (MANIFESTS_DIR / name).resolve()


def test_golden_timeline_plan_summary_matches_fixture(monkeypatch, tmp_path) -> None:
    manifest_path = _fixture_path("timeline.render.v1.json")

    def fake_probe_media(self, input_path):  # type: ignore[no-untyped-def]
        return {"format": {"duration": "12.0"}}

    monkeypatch.setattr(VideoEditingService, "probe_media", fake_probe_media)

    summary = VideoEditingService().summarize_plan(
        manifest_path=manifest_path,
        output_path=tmp_path / "golden-output.mp4",
    )

    assert summary.manifest_path == manifest_path
    assert summary.output_path == (tmp_path / "golden-output.mp4").resolve()
    assert summary.section_count == 2
    assert [section.title for section in summary.sections] == ["Opening", "Middle"]
    assert [section.duration_seconds for section in summary.sections] == [2.5, 3.0]
    assert [section.gap_after_seconds for section in summary.sections] == [1.0, 1.0]


def test_golden_playlist_plan_summary_matches_fixture() -> None:
    manifest_path = _fixture_path("playlist.render.v1.json")

    summary = VideoEditingService().summarize_plan(manifest_path=manifest_path)

    assert summary == {
        "kind": "playlist",
        "version": 1,
        "item_count": 2,
        "output_path": "playlist-output.mp4",
        "spacer_seconds": 1.5,
    }
