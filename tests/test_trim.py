from video_editing_cli.cli import build_parser


def test_trim_parser_accepts_expected_arguments() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "trim",
            "input.mp4",
            "output.mp4",
            "--start",
            "00:00:05",
            "--duration",
            "10",
            "--reencode",
        ]
    )

    assert args.command == "trim"
    assert args.input == "input.mp4"
    assert args.output == "output.mp4"
    assert args.start == "00:00:05"
    assert args.duration == "10"
    assert args.reencode is True
