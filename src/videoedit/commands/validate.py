from __future__ import annotations

import argparse
import sys

from ..operations import validate_manifest

COMMAND_NAME = "validate"


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(COMMAND_NAME, help="Validate a cut-list or timeline manifest")
    parser.add_argument("manifest", type=str)
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    try:
        result = validate_manifest(args.manifest)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Invalid manifest: {args.manifest}", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        return 1

    details = [
        f"sources={result.source_count}",
        f"cuts={result.cut_count}",
    ]
    if result.section_count is not None:
        details.append(f"sections={result.section_count}")
    print(f"Valid {result.manifest_type} manifest: {args.manifest} ({', '.join(details)})")
    return 0
