from __future__ import annotations

from videoedit.service import VideoEditingService


def _video_stream(probe_result: dict) -> dict:
    for stream in probe_result["streams"]:
        if stream.get("codec_type") == "video":
            return stream
    raise AssertionError("Expected a video stream in probe output")


def test_render_timeline_renders_real_output_from_generated_media(
    generated_media_workspace,
) -> None:
    generated_media_workspace.create_video(
        "clip-a.mp4",
        duration_seconds=1.1,
        size=(160, 90),
        color="blue",
        tone_hz=440,
    )
    generated_media_workspace.create_video(
        "clip-b.mp4",
        duration_seconds=1.0,
        size=(160, 90),
        color="green",
        tone_hz=660,
    )
    manifest_path = generated_media_workspace.write_manifest(
        "timeline.integration.v1.json",
        {
            "kind": "timeline",
            "version": 1,
            "sources": [
                {"id": "clip_a", "path": "../media/clip-a.mp4"},
                {"id": "clip_b", "path": "../media/clip-b.mp4"},
            ],
            "cuts": [
                {
                    "id": "intro",
                    "source": "clip_a",
                    "start": "0",
                    "duration": "0.6",
                    "label": "Intro",
                },
                {
                    "id": "closing",
                    "source": "clip_b",
                    "start": "0.1",
                    "duration": "0.5",
                    "label": "Closing",
                },
            ],
            "defaults": {
                "gap_after_seconds": 0.1,
                "audio_fade_in_seconds": 0.05,
                "audio_fade_out_seconds": 0.05,
            },
            "sections": [
                {"cut": "intro", "title": "Blue Intro"},
                {"cut": "closing", "title": "Green Closing", "gap_after_seconds": 0.0},
            ],
            "output": {"path": "timeline-output.mp4"},
        },
    )

    service = VideoEditingService()
    output_path = generated_media_workspace.root / "timeline-output.mp4"

    rendered_path = service.render_timeline(manifest_path, output_path=output_path)

    assert rendered_path == output_path.resolve()
    assert rendered_path.exists()
    assert rendered_path.stat().st_size > 0

    probe_result = service.probe_media(rendered_path)
    stream = _video_stream(probe_result)

    assert (int(stream["width"]), int(stream["height"])) == (160, 90)
    assert float(probe_result["format"]["duration"]) >= 1.0


def test_render_canvas_renders_real_output_from_generated_media(
    generated_media_workspace,
) -> None:
    generated_media_workspace.create_video(
        "panel-left.mp4",
        duration_seconds=0.8,
        size=(160, 180),
        color="purple",
        tone_hz=330,
    )
    generated_media_workspace.create_video(
        "panel-right.mp4",
        duration_seconds=0.8,
        size=(160, 180),
        color="orange",
        tone_hz=550,
    )
    generated_media_workspace.create_video(
        "finale.mp4",
        duration_seconds=0.4,
        size=(320, 180),
        color="white",
        tone_hz=770,
    )
    manifest_path = generated_media_workspace.write_manifest(
        "canvas.integration.v1.json",
        {
            "kind": "canvas",
            "version": 1,
            "canvas_size": [320, 180],
            "panels": [
                {
                    "input": "../media/panel-left.mp4",
                    "position": "outer_left",
                    "crop": "full",
                    "speed": 1.0,
                },
                {
                    "input": "../media/panel-right.mp4",
                    "position": "inner_left",
                    "crop": "smart",
                    "speed": 1.0,
                },
            ],
            "finale": {
                "input": "../media/finale.mp4",
                "beats": 4,
                "mode": "full_width",
            },
            "output": {"path": "canvas-output.mp4"},
        },
    )

    service = VideoEditingService()
    output_path = generated_media_workspace.root / "canvas-output.mp4"

    rendered_path = service.render_canvas(manifest_path, output_path=output_path)

    assert rendered_path == output_path
    assert rendered_path.exists()
    assert rendered_path.stat().st_size > 0

    probe_result = service.probe_media(rendered_path)
    stream = _video_stream(probe_result)

    assert (int(stream["width"]), int(stream["height"])) == (320, 180)
    assert float(probe_result["format"]["duration"]) >= 1.0
