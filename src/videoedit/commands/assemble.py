from __future__ import annotations

import argparse

from ..operations import assemble_from_manifest

COMMAND_NAME = "assemble"


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        COMMAND_NAME,
        help="Build a stitched timeline from a manifest with optional gaps, audio fades, and chapter markers",
    )
    parser.add_argument("manifest", type=str)
    parser.add_argument("output", type=str)
    parser.add_argument("--gap-seconds", type=float)
    parser.add_argument("--audio-fade-seconds", type=float)
    parser.add_argument("--no-overwrite", action="store_true")
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    assemble_from_manifest(
        manifest_path=args.manifest,
        output_path=args.output,
        gap_seconds=args.gap_seconds,
        audio_fade_seconds=args.audio_fade_seconds,
        overwrite=not args.no_overwrite,
    )
    print(args.output)
    return 0
