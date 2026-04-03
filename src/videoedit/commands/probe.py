from __future__ import annotations

import argparse
import json

from ..operations import probe_media

COMMAND_NAME = "probe"


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(COMMAND_NAME, help="Inspect a media file with ffprobe")
    parser.add_argument("input", type=str)
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    payload = probe_media(args.input)
    print(json.dumps(payload, indent=2))
    return 0
