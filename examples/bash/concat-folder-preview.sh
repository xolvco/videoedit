#!/usr/bin/env bash
set -euo pipefail

input_dir="${1:-clips}"
output_path="${2:-playlist-output.mp4}"

python -m videoedit concat "$output_path" --input-dir "$input_dir" --json-preview --full-preview

