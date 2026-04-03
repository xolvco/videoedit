from __future__ import annotations

import argparse

from ..operations import extract_audio

COMMAND_NAME = "extract-audio"


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(COMMAND_NAME, help="Extract audio from a media file")
    parser.add_argument("input", type=str)
    parser.add_argument("output", type=str)
    parser.add_argument("--codec")
    parser.add_argument("--no-overwrite", action="store_true")
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    extract_audio(
        input_path=args.input,
        output_path=args.output,
        codec=args.codec,
        overwrite=not args.no_overwrite,
    )
    print(args.output)
    return 0
