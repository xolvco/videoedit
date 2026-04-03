#!/usr/bin/env bash
set -euo pipefail

input_path="${1:?usage: ./trim-video.sh <input-path> <output-path>}"
output_path="${2:?usage: ./trim-video.sh <input-path> <output-path>}"

python -m video_editing_cli trim "$input_path" "$output_path" --start 00:00:05 --duration 15
