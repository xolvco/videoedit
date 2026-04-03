#!/usr/bin/env bash
set -euo pipefail

input_path="${1:?usage: ./probe-video.sh <input-path>}"

python -m video_editing_cli probe "$input_path"
