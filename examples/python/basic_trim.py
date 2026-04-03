from pathlib import Path

from videoedit.operations import trim_video


def main() -> None:
    trim_video(
        input_path=Path("input.mp4"),
        output_path=Path("output.mp4"),
        start="00:00:03",
        duration="10",
        reencode=False,
    )


if __name__ == "__main__":
    main()

