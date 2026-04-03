from pathlib import Path

from videoedit.media import normalize_videos
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


def test_golden_normalize_then_render_timeline_workflow(
    generated_media_workspace,
) -> None:
    source_a = generated_media_workspace.create_video(
        "workflow-a.mp4",
        duration_seconds=0.8,
        size=(96, 160),
        color="cyan",
        tone_hz=430,
        fps=15,
    )
    source_b = generated_media_workspace.create_video(
        "workflow-b.mp4",
        duration_seconds=0.9,
        size=(200, 112),
        color="magenta",
        tone_hz=730,
        fps=30,
    )
    normalized_paths = normalize_videos(
        [source_a, source_b],
        output_dir=generated_media_workspace.root / "normalized-workflow",
        width=160,
        height=90,
        fps=24,
    )
    manifest_path = generated_media_workspace.write_manifest(
        "timeline.normalized.workflow.v1.json",
        {
            "kind": "timeline",
            "version": 1,
            "sources": [
                {"id": "clip_a", "path": str(normalized_paths[0])},
                {"id": "clip_b", "path": str(normalized_paths[1])},
            ],
            "cuts": [
                {
                    "id": "intro",
                    "source": "clip_a",
                    "start": "0",
                    "duration": "0.4",
                    "label": "Intro",
                },
                {
                    "id": "answer",
                    "source": "clip_b",
                    "start": "0.1",
                    "duration": "0.5",
                    "label": "Answer",
                },
            ],
            "defaults": {
                "gap_after_seconds": 0.1,
                "audio_fade_in_seconds": 0.05,
                "audio_fade_out_seconds": 0.05,
            },
            "sections": [
                {"cut": "intro", "title": "Normalized Intro"},
                {"cut": "answer", "title": "Normalized Answer", "gap_after_seconds": 0.0},
            ],
            "output": {"path": "normalized-workflow-output.mp4"},
        },
    )

    service = VideoEditingService()
    output_path = generated_media_workspace.root / "normalized-workflow-output.mp4"

    summary = service.summarize_plan(manifest_path=manifest_path, output_path=output_path)

    assert summary.manifest_path == manifest_path.resolve()
    assert summary.output_path == output_path.resolve()
    assert summary.section_count == 2
    assert [section.title for section in summary.sections] == [
        "Normalized Intro",
        "Normalized Answer",
    ]
    assert all(section.input_path in normalized_paths for section in summary.sections)

    rendered_path = service.render_timeline(manifest_path=manifest_path, output_path=output_path)

    assert rendered_path == output_path.resolve()
    assert rendered_path.exists()

    probe_result = service.probe_media(rendered_path)
    video_stream = next(
        stream for stream in probe_result["streams"] if stream.get("codec_type") == "video"
    )
    assert (int(video_stream["width"]), int(video_stream["height"])) == (160, 90)
    assert float(probe_result["format"]["duration"]) >= 0.9


def test_golden_service_normalize_batch_then_render_playlist_workflow(
    generated_media_workspace,
) -> None:
    source_a = generated_media_workspace.create_video(
        "playlist-workflow-a.mp4",
        duration_seconds=0.9,
        size=(100, 160),
        color="orange",
        tone_hz=460,
        fps=18,
    )
    source_b = generated_media_workspace.create_video(
        "playlist-workflow-b.mp4",
        duration_seconds=1.0,
        size=(200, 112),
        color="purple",
        tone_hz=760,
        fps=30,
    )

    service = VideoEditingService()
    normalized_dir = generated_media_workspace.root / "service-normalized"
    normalized_dir.mkdir()
    normalized_paths = []
    for source_path in [source_a, source_b]:
        target_path = normalized_dir / f"{source_path.stem}.norm.mp4"
        normalized_paths.append(
            service.normalize_video(
                input_path=source_path,
                output_path=target_path,
                width=160,
                height=90,
                fps=24,
            )
        )

    manifest_path = generated_media_workspace.write_manifest(
        "playlist.normalized.workflow.v1.json",
        {
            "kind": "playlist",
            "version": 1,
            "defaults": {
                "spacer_seconds": 0.1,
                "audio_fade_in_seconds": 0.05,
                "audio_fade_out_seconds": 0.05,
            },
            "title_styles": {
                "default": {
                    "anchor": "bottom-left",
                    "offset_x": 20,
                    "offset_y": 20,
                    "font_size": 18,
                    "font_color": "#FFFFFF",
                    "opacity": 0.9,
                }
            },
            "items": [
                {
                    "path": str(normalized_paths[0]),
                    "start": "0",
                    "duration": "0.4",
                    "marker": "Normalized Orange",
                    "title": "Batch Intro",
                    "title_start": 0.05,
                    "title_duration": 0.25,
                    "title_style": "default",
                },
                {
                    "path": str(normalized_paths[1]),
                    "start": "0.1",
                    "duration": "0.5",
                    "marker": "Normalized Purple",
                    "audio_fade_out_seconds": 0.08,
                },
            ],
            "output": {"path": "service-normalized-playlist-output.mp4"},
        },
    )
    output_path = generated_media_workspace.root / "service-normalized-playlist-output.mp4"

    summary = service.summarize_plan(manifest_path=manifest_path, output_path=output_path)

    assert summary == {
        "kind": "playlist",
        "version": 1,
        "item_count": 2,
        "output_path": str(output_path),
        "spacer_seconds": 0.1,
    }
    assert all(path.exists() for path in normalized_paths)

    rendered_path = service.render_playlist(manifest_path=manifest_path, output_path=output_path)

    assert rendered_path == output_path.resolve()
    assert rendered_path.exists()

    probe_result = service.probe_media(rendered_path)
    video_stream = next(
        stream for stream in probe_result["streams"] if stream.get("codec_type") == "video"
    )
    audio_stream = next(
        stream for stream in probe_result["streams"] if stream.get("codec_type") == "audio"
    )
    assert (int(video_stream["width"]), int(video_stream["height"])) == (160, 90)
    assert audio_stream["codec_name"] == "aac"
    assert float(probe_result["format"]["duration"]) >= 0.9
