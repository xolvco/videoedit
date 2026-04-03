import json
from pathlib import Path


def main() -> None:
    clips = [
        Path("clips/intro.mp4"),
        Path("clips/topic-a.mp4"),
        Path("clips/topic-b.mp4"),
    ]

    playlist = {
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
                "offset_x": 80,
                "offset_y": 80,
                "font_size": 42,
                "font_color": "#FFFFFF",
                "opacity": 0.92,
            }
        },
        "items": [
            {
                "path": str(clips[0]),
                "start": "00:00:03.000",
                "end": "00:00:12.000",
                "marker": "Intro",
                "title": "Opening",
                "title_start": 0.25,
                "title_duration": 2.5,
                "title_style": "default",
            },
            {
                "path": str(clips[1]),
                "start": "00:00:10.000",
                "duration": "8.0",
                "marker": "Topic A",
                "audio_fade_in_seconds": 0.75,
            },
            {
                "path": str(clips[2]),
                "start": "00:00:05.000",
                "duration": "6.5",
                "marker": "Topic B",
                "spacer_seconds": 1.0,
            },
        ],
        "output": {
            "path": "playlist-output.mp4",
        },
    }

    playlist_path = Path("playlist.json")
    playlist_path.write_text(json.dumps(playlist, indent=2), encoding="utf-8")
    print(f"Wrote {playlist_path}")


if __name__ == "__main__":
    main()

