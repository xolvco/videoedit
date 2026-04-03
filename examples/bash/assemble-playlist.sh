#!/usr/bin/env bash
set -euo pipefail

manifest_path="${1:?usage: ./assemble-playlist.sh <manifest-path> <output-path>}"
output_path="${2:?usage: ./assemble-playlist.sh <manifest-path> <output-path>}"

python -m video_editing_cli validate "$manifest_path"
python -m video_editing_cli plan "$manifest_path" "$output_path"
python -m video_editing_cli assemble "$manifest_path" "$output_path"
