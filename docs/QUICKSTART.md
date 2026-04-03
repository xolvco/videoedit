# Quickstart

This guide walks through the fastest path to a usable result with `videoedit`.

It assumes:

- you are new to Python tooling
- you want to work from PowerShell first
- you want to concatenate a folder of videos using the current defaults

If you prefer Git Bash or WSL2 later, see [Bash Integration](BASH.md).

## 1. Get the library

Open PowerShell in the project folder and create a local virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

This installs:

- the `video-edit` command
- the Python package in editable mode
- development tools such as `pytest`

## 2. Make sure FFmpeg is available

This project uses the system `ffmpeg` and `ffprobe` executables.

Check they are available:

```powershell
ffmpeg -version
ffprobe -version
```

If PowerShell says the commands are not found, install FFmpeg and make sure it is on your `PATH` before continuing.

## 3. Choose how you want to run the CLI

After installation, you can usually run either form:

```powershell
video-edit probe .\input.mp4
python -m videoedit probe .\input.mp4
```

For day-to-day use in this repo, `video-edit ...` is the most convenient.

## 4. Concatenate a folder of videos with defaults

Put your source videos in a folder such as `.\clips`.

Then run:

```powershell
video-edit concat .\output.mp4 --input-dir .\clips
```

This will:

- discover supported video files in `.\clips`
- sort them by filename
- concatenate them in that order
- write the result to `.\output.mp4`

## 5. Preview a playlist manifest before rendering

If you want an editable JSON scaffold first, generate one from the same folder:

```powershell
video-edit concat .\output.mp4 --input-dir .\clips --json-preview
```

For a fuller scaffold with defaults and more editable fields:

```powershell
video-edit concat .\output.mp4 --input-dir .\clips --json-preview --full-preview
```

Copy that JSON into a file such as `.\playlist.json`, then edit the order or timing as needed.

## 6. Validate the playlist

Before rendering from a manifest, validate it:

```powershell
video-edit validate .\playlist.json
```

If the manifest is valid, the command prints a short summary and exits with code `0`.

## 7. Render from the playlist

Once the playlist looks right:

```powershell
video-edit concat .\output.mp4 --playlist .\playlist.json
```

## 8. Use the library API directly

If you are integrating `videoedit` into another Python app, the service and manifest helpers are the canonical API:

```python
from pathlib import Path

from videoedit import VideoEditingService, load_manifest, plan_render, summarize_plan

service = VideoEditingService()
manifest = load_manifest(Path("playlist.json"))
plan = plan_render(Path("playlist.json"))
summary = summarize_plan(Path("playlist.json"))
```

Use the higher-level render helpers when you already have a manifest on disk:

```python
from pathlib import Path

from videoedit import render_canvas, render_playlist, render_timeline

render_playlist(Path("playlist.json"))
render_timeline(Path("timeline.json"))
render_canvas(Path("canvas.json"))
```

## Common questions

### How do I set the gap between videos to `0`?

In a concat playlist manifest:

```json
"defaults": {
  "spacer_seconds": 0.0
}
```

For one specific item:

```json
{
  "path": "clips/topic-b.mp4",
  "spacer_seconds": 0.0
}
```

### How do I set the fade in and fade out timing of the audio?

In the playlist defaults:

```json
"defaults": {
  "audio_fade_in_seconds": 0.5,
  "audio_fade_out_seconds": 0.5
}
```

For one specific item:

```json
{
  "path": "clips/topic-a.mp4",
  "audio_fade_in_seconds": 0.75,
  "audio_fade_out_seconds": 0.75
}
```

### How do I use an image between videos?

That is planned in the architecture, but it is not implemented yet.

Today the supported spacer behavior is black spacing controlled by `spacer_seconds`.

## Next step

Once you are comfortable with the quickstart flow, continue to [Concat Playlist Guide](CONCAT_PLAYLIST_GUIDE.md) for a manifest-focused guide that explains the current playlist format in more detail.

