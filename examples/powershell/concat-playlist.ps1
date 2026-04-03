param(
    [string]$PlaylistPath = "examples/manifests/concat-playlist.v1.json",
    [string]$OutputPath = "playlist-output.mp4"
)

python -m videoedit validate $PlaylistPath
python -m videoedit concat $OutputPath --playlist $PlaylistPath

