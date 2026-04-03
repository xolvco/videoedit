from pathlib import Path

from videoedit import FFmpegTools, VideoEditingService


def main() -> None:
    service = VideoEditingService(
        tools=FFmpegTools(
            ffmpeg="ffmpeg",
            ffprobe="ffprobe",
        )
    )
    service.extract_audio(
        input_path=Path("input.mp4"),
        output_path=Path("audio.wav"),
    )


if __name__ == "__main__":
    main()

