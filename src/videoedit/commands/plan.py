from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from ..operations import plan_assembly

COMMAND_NAME = "plan"


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(COMMAND_NAME, help="Resolve an assembly manifest into JSON without rendering")
    parser.add_argument("manifest", type=str)
    parser.add_argument("output", type=str)
    parser.add_argument("--gap-seconds", type=float)
    parser.add_argument("--audio-fade-seconds", type=float)
    parser.add_argument("--no-overwrite", action="store_true")
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    try:
        summary = plan_assembly(
            manifest_path=args.manifest,
            output_path=args.output,
            gap_seconds=args.gap_seconds,
            audio_fade_seconds=args.audio_fade_seconds,
            overwrite=not args.no_overwrite,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"Could not build plan: {args.manifest}", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        return 1

    payload = asdict(summary)
    payload["manifest_path"] = str(summary.manifest_path)
    payload["output_path"] = str(summary.output_path)
    payload["sections"] = [
        {
            **section,
            "input_path": str(section["input_path"]),
        }
        for section in payload["sections"]
    ]
    print(json.dumps(payload, indent=2))
    return 0
