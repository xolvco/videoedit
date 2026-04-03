from video_editing_cli.service import FFmpegTools, VideoEditingService


def test_service_uses_provided_tool_paths() -> None:
    service = VideoEditingService(tools=FFmpegTools(ffmpeg="custom-ffmpeg", ffprobe="custom-ffprobe"))

    assert service.tools.ffmpeg == "custom-ffmpeg"
    assert service.tools.ffprobe == "custom-ffprobe"
