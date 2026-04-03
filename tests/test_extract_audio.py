from video_editing_cli.cli import build_parser


def test_extract_audio_parser_accepts_codec() -> None:
    parser = build_parser()
    args = parser.parse_args(["extract-audio", "input.mp4", "audio.wav", "--codec", "mp3"])

    assert args.command == "extract-audio"
    assert args.input == "input.mp4"
    assert args.output == "audio.wav"
    assert args.codec == "mp3"
