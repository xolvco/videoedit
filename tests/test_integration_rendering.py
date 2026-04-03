from __future__ import annotations

from fractions import Fraction

from videoedit.media import normalize_videos
from videoedit.service import VideoEditingService


def _video_stream(probe_result: dict) -> dict:
    for stream in probe_result["streams"]:
        if stream.get("codec_type") == "video":
            return stream
    raise AssertionError("Expected a video stream in probe output")


def _audio_stream(probe_result: dict) -> dict:
    for stream in probe_result["streams"]:
        if stream.get("codec_type") == "audio":
            return stream
    raise AssertionError("Expected an audio stream in probe output")


def _frame_rate_as_float(stream: dict) -> float:
    raw_value = stream.get("avg_frame_rate") or stream.get("r_frame_rate")
    if not raw_value:
        raise AssertionError("Expected frame-rate metadata in probe output")
    return float(Fraction(raw_value))


def test_normalize_video_reencodes_to_target_dimensions_and_fps(
    generated_media_workspace,
) -> None:
    source_path = generated_media_workspace.create_video(
        "portrait-source.mp4",
        duration_seconds=0.8,
        size=(90, 160),
        color="teal",
        tone_hz=510,
        fps=15,
    )
    service = VideoEditingService()
    output_path = generated_media_workspace.root / "normalized.mp4"

    rendered_path = service.normalize_video(
        input_path=source_path,
        output_path=output_path,
        width=160,
        height=90,
        fps=24,
    )

    assert rendered_path == output_path.resolve()
    assert rendered_path.exists()
    assert rendered_path.stat().st_size > 0

    probe_result = service.probe_media(rendered_path)
    video_stream = _video_stream(probe_result)
    audio_stream = _audio_stream(probe_result)

    assert (int(video_stream["width"]), int(video_stream["height"])) == (160, 90)
    assert abs(_frame_rate_as_float(video_stream) - 24.0) < 0.05
    assert audio_stream["codec_name"] == "aac"
    assert float(probe_result["format"]["duration"]) >= 0.7


def test_normalize_videos_batch_handles_mixed_profiles(
    generated_media_workspace,
) -> None:
    source_a = generated_media_workspace.create_video(
        "batch-a.mp4",
        duration_seconds=0.7,
        size=(96, 160),
        color="navy",
        tone_hz=410,
        fps=15,
    )
    source_b = generated_media_workspace.create_video(
        "batch-b.mp4",
        duration_seconds=0.9,
        size=(200, 112),
        color="maroon",
        tone_hz=710,
        fps=30,
    )
    output_dir = generated_media_workspace.root / "normalized-batch"

    normalized_paths = normalize_videos(
        [source_a, source_b],
        output_dir=output_dir,
        width=160,
        height=90,
        fps=24,
    )

    assert len(normalized_paths) == 2
    assert [path.name for path in normalized_paths] == [
        "batch-a.norm.mp4",
        "batch-b.norm.mp4",
    ]

    service = VideoEditingService()
    for normalized_path in normalized_paths:
        assert normalized_path.exists()
        probe_result = service.probe_media(normalized_path)
        video_stream = _video_stream(probe_result)
        audio_stream = _audio_stream(probe_result)

        assert (int(video_stream["width"]), int(video_stream["height"])) == (160, 90)
        assert abs(_frame_rate_as_float(video_stream) - 24.0) < 0.05
        assert audio_stream["codec_name"] == "aac"


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


def test_render_playlist_renders_real_output_from_generated_media(
    generated_media_workspace,
) -> None:
    generated_media_workspace.create_video(
        "clip-a.mp4",
        duration_seconds=0.8,
        size=(160, 90),
        color="red",
        tone_hz=440,
    )
    generated_media_workspace.create_video(
        "clip-b.mp4",
        duration_seconds=0.7,
        size=(160, 90),
        color="yellow",
        tone_hz=620,
    )
    manifest_path = generated_media_workspace.write_manifest(
        "playlist.integration.v1.json",
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
                    "opacity": 0.85,
                }
            },
            "items": [
                {
                    "path": "../media/clip-a.mp4",
                    "start": "0",
                    "duration": "0.5",
                    "marker": "Red Clip",
                    "title": "Opening",
                    "title_start": 0.05,
                    "title_duration": 0.3,
                    "title_style": "default",
                },
                {
                    "path": "../media/clip-b.mp4",
                    "start": "0.1",
                    "duration": "0.4",
                    "marker": "Yellow Clip",
                    "audio_fade_out_seconds": 0.08,
                },
            ],
            "output": {"path": "playlist-output.mp4"},
        },
    )

    service = VideoEditingService()
    output_path = generated_media_workspace.root / "playlist-output.mp4"

    rendered_path = service.render_playlist(manifest_path, output_path=output_path)

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


def test_render_canvas_renders_real_output_with_audio_mix(
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
        "music-bed.mp4",
        duration_seconds=0.9,
        size=(64, 64),
        color="black",
        tone_hz=220,
    )
    generated_media_workspace.create_video(
        "accent.mp4",
        duration_seconds=0.9,
        size=(64, 64),
        color="gray",
        tone_hz=880,
    )
    manifest_path = generated_media_workspace.write_manifest(
        "canvas.audio.integration.v1.json",
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
            "audio": {
                "duration_ms": 900,
                "tracks": [
                    {
                        "input": "../media/music-bed.mp4",
                        "level": 0.6,
                        "fade_in_ms": 80,
                    },
                    {
                        "input": "../media/accent.mp4",
                        "level": 0.35,
                        "fade_out_ms": 100,
                    },
                ],
                "ramps": [
                    {
                        "track": 1,
                        "at_ms": 300,
                        "to_level": 0.0,
                        "over_ms": 200,
                    }
                ],
            },
            "output": {"path": "canvas-audio-output.mp4"},
        },
    )

    service = VideoEditingService()
    output_path = generated_media_workspace.root / "canvas-audio-output.mp4"

    rendered_path = service.render_canvas(manifest_path, output_path=output_path)

    assert rendered_path == output_path
    assert rendered_path.exists()
    assert rendered_path.stat().st_size > 0

    probe_result = service.probe_media(rendered_path)
    video_stream = _video_stream(probe_result)
    audio_stream = _audio_stream(probe_result)

    assert (int(video_stream["width"]), int(video_stream["height"])) == (320, 180)
    assert audio_stream["codec_name"] == "aac"
    assert float(probe_result["format"]["duration"]) >= 0.7


def test_render_canvas_renders_richer_four_panel_layout(
    generated_media_workspace,
) -> None:
    panel_specs = [
        ("outer-left.mp4", "red", 300, (90, 160), "outer_left", "full", 1.0),
        ("inner-left.mp4", "blue", 420, (120, 160), "inner_left", "smart", 1.1),
        ("inner-right.mp4", "green", 540, (160, 120), "inner_right", "smart", 0.9),
        ("outer-right.mp4", "yellow", 660, (90, 160), "outer_right", "full", 1.0),
    ]
    panels: list[dict[str, object]] = []
    for name, color, tone_hz, size, position, crop, speed in panel_specs:
        generated_media_workspace.create_video(
            name,
            duration_seconds=0.8,
            size=size,
            color=color,
            tone_hz=tone_hz,
        )
        panels.append(
            {
                "input": f"../media/{name}",
                "position": position,
                "crop": crop,
                "speed": speed,
            }
        )

    manifest_path = generated_media_workspace.write_manifest(
        "canvas.four-panel.integration.v1.json",
        {
            "kind": "canvas",
            "version": 1,
            "canvas_size": [360, 180],
            "panels": panels,
            "output": {"path": "canvas-four-panel-output.mp4"},
        },
    )

    service = VideoEditingService()
    output_path = generated_media_workspace.root / "canvas-four-panel-output.mp4"

    rendered_path = service.render_canvas(manifest_path, output_path=output_path)

    assert rendered_path == output_path
    assert rendered_path.exists()
    assert rendered_path.stat().st_size > 0

    probe_result = service.probe_media(rendered_path)
    video_stream = _video_stream(probe_result)

    assert (int(video_stream["width"]), int(video_stream["height"])) == (360, 180)
    assert float(probe_result["format"]["duration"]) >= 0.7


def test_render_canvas_handles_four_panel_timing_with_finale_and_audio_mix(
    generated_media_workspace,
) -> None:
    panel_specs = [
        ("outer-left-timing.mp4", "red", 300, (90, 160), "outer_left", "full", 1.2),
        ("inner-left-timing.mp4", "blue", 420, (120, 160), "inner_left", "smart", 0.8),
        ("inner-right-timing.mp4", "green", 540, (160, 120), "inner_right", "smart", 1.0),
        ("outer-right-timing.mp4", "yellow", 660, (90, 160), "outer_right", "full", 1.4),
    ]
    panels: list[dict[str, object]] = []
    for name, color, tone_hz, size, position, crop, speed in panel_specs:
        generated_media_workspace.create_video(
            name,
            duration_seconds=0.9,
            size=size,
            color=color,
            tone_hz=tone_hz,
        )
        panels.append(
            {
                "input": f"../media/{name}",
                "position": position,
                "crop": crop,
                "speed": speed,
            }
        )

    generated_media_workspace.create_video(
        "finale-wide.mp4",
        duration_seconds=0.5,
        size=(360, 180),
        color="white",
        tone_hz=820,
    )
    generated_media_workspace.create_video(
        "music-main.mp4",
        duration_seconds=1.4,
        size=(64, 64),
        color="black",
        tone_hz=220,
    )
    generated_media_workspace.create_video(
        "music-accent.mp4",
        duration_seconds=1.4,
        size=(64, 64),
        color="gray",
        tone_hz=920,
    )

    manifest_path = generated_media_workspace.write_manifest(
        "canvas.timing.finale.integration.v1.json",
        {
            "kind": "canvas",
            "version": 1,
            "canvas_size": [360, 180],
            "panels": panels,
            "finale": {
                "input": "../media/finale-wide.mp4",
                "beats": 4,
                "mode": "full_width",
            },
            "audio": {
                "duration_ms": 1400,
                "tracks": [
                    {
                        "input": "../media/music-main.mp4",
                        "level": 0.55,
                        "fade_in_ms": 100,
                    },
                    {
                        "input": "../media/music-accent.mp4",
                        "level": 0.25,
                        "fade_out_ms": 150,
                    },
                ],
                "ramps": [
                    {
                        "track": 1,
                        "at_ms": 500,
                        "to_level": 0.0,
                        "over_ms": 250,
                    }
                ],
            },
            "output": {"path": "canvas-timing-finale-output.mp4"},
        },
    )

    service = VideoEditingService()
    output_path = generated_media_workspace.root / "canvas-timing-finale-output.mp4"

    rendered_path = service.render_canvas(manifest_path, output_path=output_path)

    assert rendered_path == output_path
    assert rendered_path.exists()
    assert rendered_path.stat().st_size > 0

    probe_result = service.probe_media(rendered_path)
    video_stream = _video_stream(probe_result)
    audio_stream = _audio_stream(probe_result)

    assert (int(video_stream["width"]), int(video_stream["height"])) == (360, 180)
    assert audio_stream["codec_name"] == "aac"
    assert float(probe_result["format"]["duration"]) >= 1.1
