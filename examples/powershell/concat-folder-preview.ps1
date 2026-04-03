param(
    [string]$InputDir = "clips",
    [string]$OutputPath = "playlist-output.mp4"
)

python -m video_editing_cli concat $OutputPath --input-dir $InputDir --json-preview --full-preview
