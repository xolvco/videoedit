import json
from pathlib import Path

from videoedit.layout import MultiPanelCanvas
from videoedit.service import VideoEditingService


FIXTURES_DIR = Path(__file__).parent / "fixtures"
MANIFESTS_DIR = FIXTURES_DIR / "manifests"


def _fixture_path(name: str) -> Path:
    return (MANIFESTS_DIR / name).resolve()


def test_render_timeline_uses_manifest_output_and_renders_plan(monkeypatch) -> None:
    manifest_path = _fixture_path("timeline.render.v1.json")
    captured: dict[str, object] = {}

    def fake_probe_media(self, input_path):  # type: ignore[no-untyped-def]
        return {"format": {"duration": "12.0"}}

    def fake_run_ffmpeg(args):  # type: ignore[no-untyped-def]
        captured["args"] = list(args)
        return None

    monkeypatch.setattr(VideoEditingService, "probe_media", fake_probe_media)
    monkeypatch.setattr("videoedit.service.run_ffmpeg", fake_run_ffmpeg)

    output_path = VideoEditingService().render_timeline(manifest_path)

    assert output_path.name == "timeline-output.mp4"
    command_text = " ".join(captured["args"])
    assert "clip-a.mp4" in command_text
    assert "clip-b.mp4" in command_text
    assert "libx264" in command_text


def test_render_playlist_resolves_relative_media_paths_and_defaults(monkeypatch) -> None:
    manifest_path = _fixture_path("playlist.render.v1.json")
    captured: dict[str, object] = {}

    def fake_probe_media(self, input_path):  # type: ignore[no-untyped-def]
        return {"format": {"duration": "12.0"}}

    def fake_run_ffmpeg(args):  # type: ignore[no-untyped-def]
        captured["args"] = list(args)
        return None

    monkeypatch.setattr(VideoEditingService, "probe_media", fake_probe_media)
    monkeypatch.setattr("videoedit.service.run_ffmpeg", fake_run_ffmpeg)

    output_path = VideoEditingService().render_playlist(manifest_path)

    assert output_path.name == "playlist-output.mp4"
    command_text = " ".join(captured["args"])
    assert "clip-a.mp4" in command_text
    assert "clip-b.mp4" in command_text
    assert "drawtext=" in command_text


def test_render_canvas_uses_manifest_output_and_dispatches_to_canvas_renderer(monkeypatch) -> None:
    manifest_path = _fixture_path("canvas.render.v1.json")
    captured: dict[str, object] = {}

    def fake_render(self, output, **kwargs):  # type: ignore[no-untyped-def]
        captured["output"] = str(output)
        captured["panel_count"] = len(self.panels)
        captured["has_finale"] = self._finale is not None
        return Path(output)

    monkeypatch.setattr(MultiPanelCanvas, "render", fake_render)

    output_path = VideoEditingService().render_canvas(manifest_path)

    assert output_path.name == "canvas-output.mp4"
    assert captured["panel_count"] == 2
    assert captured["has_finale"] is True


def test_plan_render_returns_expected_playlist_summary() -> None:
    manifest_path = _fixture_path("playlist.render.v1.json")

    summary = VideoEditingService().plan_render(manifest_path)

    assert summary == {
        "kind": "playlist",
        "version": 1,
        "item_count": 2,
        "output_path": "playlist-output.mp4",
        "spacer_seconds": 1.5,
    }


def test_plan_render_returns_expected_canvas_summary() -> None:
    manifest_path = _fixture_path("canvas.render.v1.json")

    summary = VideoEditingService().plan_render(manifest_path)

    assert summary == {
        "kind": "canvas",
        "version": 1,
        "panel_count": 2,
        "output_path": "canvas-output.mp4",
        "canvas_size": [1920, 1080],
    }
