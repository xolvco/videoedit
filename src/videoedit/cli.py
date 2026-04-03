from __future__ import annotations

import argparse

from .commands import COMMAND_MODULES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="video-edit",
        description="FFmpeg-powered video editing commands for automation and app integration.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for module in COMMAND_MODULES:
        module.register(subparsers)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.error(f"Unknown command: {args.command}")
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
