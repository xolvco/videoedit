#!/usr/bin/env bash
set -euo pipefail

playlist_path="${1:-examples/manifests/concat-playlist.v1.json}"
output_path="${2:-playlist-output.mp4}"

python -m video_editing_cli validate "$playlist_path"
python -m video_editing_cli concat "$output_path" --playlist "$playlist_path"
