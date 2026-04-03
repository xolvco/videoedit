import json
from pathlib import Path

from video_editing_cli.cli import build_parser
from video_editing_cli.commands import probe


def test_probe_parser_accepts_input() -> None:
    parser = build_parser()
    args = parser.parse_args(["probe", "input.mp4"])

    assert args.command == "probe"
    assert args.input == "input.mp4"


def test_probe_handler_prints_json(monkeypatch, capsys) -> None:
    def fake_probe_media(input_path: str) -> dict:
        return {"input": input_path, "streams": []}

    monkeypatch.setattr(probe, "probe_media", fake_probe_media)

    exit_code = probe.handle(build_parser().parse_args(["probe", "input.mp4"]))

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {"input": "input.mp4", "streams": []}
