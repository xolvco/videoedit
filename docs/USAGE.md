# CLI Usage

This page is the general usage guide for `video-edit`.

The current workflow is centered on preparing and assembling footage for fast-beating music videos using readable cut lists and timeline manifests.

## Install for local development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

For Git Bash or WSL2:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Basic command pattern

```bash
video-edit <command> [arguments] [options]
```

Portable alternative:

```bash
python -m videoedit <command> [arguments] [options]
```

## Included commands

- `probe`: print media metadata as JSON
- `validate`: check manifests before planning or rendering
- `plan`: resolve an assembly manifest into JSON without rendering
- `trim`: create a clip from a source file
- `concat`: join clips into one output from files, folders, or a concat playlist
- `extract-audio`: write an audio-only output from a media file
- `assemble`: render a manifest-driven timeline with gaps, fades, and chapter markers

## Core library workflows

The CLI covers the current command surface, but the broader editing backend now also exposes a few important library-first workflows:

- normalize mismatched source clips before assembly with `VideoEditingService.normalize_video(...)`
- render playlist manifests directly with `render_playlist(...)`
- render timeline manifests directly with `render_timeline(...)`
- render canvas manifests directly with `render_canvas(...)`
- inspect manifest-driven work without rendering via `plan_render(...)` and `summarize_plan(...)`

## Examples

### Inspect a file

```bash
video-edit probe input.mp4
```

### Trim a clip

```bash
video-edit trim input.mp4 clip.mp4 --start 00:00:05 --duration 15
```

### Validate a manifest

```bash
video-edit validate examples/manifests/timeline.v1.json
```

### Resolve an assembly plan without rendering

```bash
video-edit plan examples/manifests/timeline.v1.json output.mp4
```

### Concatenate clips directly

```bash
video-edit concat merged.mp4 intro.mp4 main.mp4 outro.mp4
```

### Concatenate a folder of videos

```bash
video-edit concat merged.mp4 --input-dir clips
```

### Generate a concat playlist scaffold from a folder

```bash
video-edit concat merged.mp4 --input-dir clips --json-preview
```

Full scaffold with defaults and explicit editable fields:

```bash
video-edit concat merged.mp4 --input-dir clips --json-preview --full-preview
```

### Concatenate from a playlist manifest

```bash
video-edit concat merged.mp4 --playlist playlist.json
```

### Extract audio

```bash
video-edit extract-audio input.mp4 audio.wav
```

### Assemble a timeline from a manifest

```bash
video-edit assemble examples/manifests/timeline.v1.json output.mp4
```

### Normalize a source clip before assembly

Use the Python API when you want to standardize resolution, frame rate, and audio shape before later rendering:

```python
from pathlib import Path

from videoedit import VideoEditingService

service = VideoEditingService()
service.normalize_video(
    input_path=Path("portrait-source.mp4"),
    output_path=Path("portrait-source.norm.mp4"),
    width=160,
    height=90,
    fps=24,
)
```

### Render a canvas manifest

```python
from pathlib import Path

from videoedit import render_canvas

render_canvas(Path("canvas.json"))
```

The manifest can describe cuts from longer source files with versioned `sources`, `cuts`, and `sections`.
For the versioned manifest schema, see [Manifest Formats](MANIFESTS.md).

## Common workflow

For manifest-driven editing, the typical sequence is:

1. `validate` the manifest
2. `plan` the assembly or preview scaffold
3. `assemble` or `concat` the final output

For mixed-source workflows, a practical sequence is often:

1. normalize source clips to a shared size and frame rate
2. validate the playlist, timeline, or canvas manifest
3. summarize or plan the render
4. render the final output

For quick concat work, start with direct files or `--input-dir`, then use `--json-preview` when you want an editable playlist scaffold.

## Guided walkthroughs

- [Quickstart](QUICKSTART.md): novice-first PowerShell walkthrough
- [Concat Playlist Guide](CONCAT_PLAYLIST_GUIDE.md): manifest-focused concat guide
- `README.md`: higher-level Python API examples for normalize, playlist, timeline, and canvas flows

## Command reference

Detailed command pages live in the command reference section below.

- [Probe](commands/probe.md)
- [Validate](commands/validate.md)
- [Plan](commands/plan.md)
- [Trim](commands/trim.md)
- [Concat](commands/concat.md)
- [Extract Audio](commands/extract_audio.md)
- [Assemble](commands/assemble.md)

