param(
    [string]$PlaylistPath = "examples/manifests/concat-playlist.v1.json",
    [string]$OutputPath = "playlist-output.mp4"
)

python -m video_editing_cli validate $PlaylistPath
python -m video_editing_cli concat $OutputPath --playlist $PlaylistPath
