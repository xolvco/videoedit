from __future__ import annotations

import argparse

from ..operations import trim_video

COMMAND_NAME = "trim"


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(COMMAND_NAME, help="Trim a video file")
    parser.add_argument("input", type=str)
    parser.add_argument("output", type=str)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--duration")
    parser.add_argument("--reencode", action="store_true")
    parser.add_argument("--no-overwrite", action="store_true")
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    trim_video(
        input_path=args.input,
        output_path=args.output,
        start=args.start,
        end=args.end,
        duration=args.duration,
        reencode=args.reencode,
        overwrite=not args.no_overwrite,
    )
    print(args.output)
    return 0
