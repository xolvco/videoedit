param(
    [string]$InputDir = "clips",
    [string]$OutputPath = "playlist-output.mp4"
)

python -m videoedit concat $OutputPath --input-dir $InputDir --json-preview --full-preview

