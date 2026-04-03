from pathlib import Path

from videoedit import FFmpegTools, VideoEditingService


def main() -> None:
    service = VideoEditingService(
        tools=FFmpegTools(
            ffmpeg="ffmpeg",
            ffprobe="ffprobe",
        )
    )

    # Normalize mismatched footage before later assembly or playlist rendering.
    normalized_path = service.normalize_video(
        input_path=Path("input.mp4"),
        output_path=Path("input.norm.mp4"),
        width=160,
        height=90,
        fps=24,
    )

    # Render a playlist manifest once the media and edit description are ready.
    rendered_path = service.render_playlist(
        manifest_path=Path("examples/manifests/concat-playlist.v1.json"),
        output_path=Path("playlist-output.mp4"),
    )

    print(f"Normalized clip: {normalized_path}")
    print(f"Rendered playlist: {rendered_path}")


if __name__ == "__main__":
    main()

