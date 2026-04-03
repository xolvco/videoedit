import json
from pathlib import Path

from videoedit.operations import probe_media


def main() -> None:
    metadata = probe_media(Path("input.mp4"))
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()

