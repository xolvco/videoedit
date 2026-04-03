# videoedit

`videoedit` is a production-oriented Python package for building fast-beating music video workflows on top of FFmpeg. It is designed to work as both:

- a command line tool for scripts and automation
- a Python library that other applications can import and use directly

## Value-add goal

The project is meant to add value on top of FFmpeg, not compete with it. Its main purpose is to make it easier to create energetic, section-driven music videos from reusable cut plans and timeline manifests.

This package is intended to become a reusable backend engine for a future editing UI. The UI will be the public face for selecting footage, deciding what to cut, and choosing how clips should be reassembled. This library should carry the hard production logic underneath that interface.

The reusable layer should focus on:

- stable Python APIs over raw command strings
- reusable command building and validation
- app-friendly workflows for cutting, rearranging, normalizing, and assembling clips against music-driven timing
- consistent docs, tests, and examples for every supported command
- solving editing problems that are awkward or repetitive in mainstream editors

FFmpeg remains the execution engine. This library should provide the ergonomics, guardrails, and integration surface that application code wants.

## Project rule

Every CLI command in this project should include all three of these in the same change:

- the CLI implementation
- a test
- documentation

The command layout is intentionally organized around that rule:

- CLI modules live in `src/videoedit/commands/`
- command docs live in `docs/commands/`
- command tests live in `tests/test_<command>.py`

See `docs/CONTRIBUTING_COMMANDS.md` for the command checklist.

## Project layout

- `src/videoedit/`: package code
- `src/videoedit/commands/`: one module per CLI command
- `tests/`: automated tests
- `BACKLOG.md`: prioritized work list
- `docs/commands/`: command reference pages
- `docs/ARCHITECTURE_SESSION.md`: architecture decisions and domain model
- `docs/MANIFESTS.md`: versioned cut-list and timeline manifest formats
- `docs/TEST_PLAN.md`: testing strategy and release gates
- `docs/USAGE.md`: general CLI usage guide
- `docs/POWERSHELL.md`: how to call the CLI from PowerShell scripts
- `docs/BASH.md`: how to call the CLI from Git Bash or WSL2 bash
- `examples/python/`: example Python integrations
- `examples/powershell/`: example PowerShell scripts
- `examples/bash/`: example bash scripts for Git Bash and WSL2

## Planned direction

This scaffold focuses on a stable foundation for a reusable editing CLI. The initial command set supports the building blocks for music video pipelines:

- `probe`: inspect a media file with `ffprobe`
- `trim`: cut a clip with optional stream copying
- `validate`: validate cut-list, timeline, and concat playlist manifests
- `plan`: resolve an assembly manifest into JSON without rendering
- `concat`: join multiple inputs, folders, or concat playlist manifests
- `extract-audio`: export an audio track from a video file
- `assemble`: build a stitched timeline from a manifest with gaps, audio fades, and chapter markers

The long-term direction is to support workflows like:

- cutting source footage into beat-sized moments
- rearranging those moments with human-readable JSON manifests
- normalizing clips so mismatched footage can be assembled reliably
- inserting black gaps, transitions, and section markers
- combining or preparing audio segments for assembly
- eventually composing multiple videos on screen at once
- preparing clips for later beat-sync or choreography-aware tooling

## Requirements

- Python 3.10+
- `ffmpeg` and `ffprobe` available on your `PATH`

## Installation

### Local development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

On Git Bash or WSL2 bash:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Usage

```bash
video-edit probe input.mp4
video-edit validate examples/manifests/timeline.v1.json
video-edit plan examples/manifests/timeline.v1.json output.mp4
video-edit trim input.mp4 output.mp4 --start 00:00:03 --duration 12
video-edit concat output.mp4 clip1.mp4 clip2.mp4 clip3.mp4
video-edit concat output.mp4 --input-dir clips
video-edit concat output.mp4 --input-dir clips --json-preview
video-edit extract-audio input.mp4 audio.wav
video-edit assemble examples/manifests/timeline.v1.json output.mp4
```

The `assemble` workflow uses versioned, human-readable JSON manifests so you can describe cuts and reassembly with explicit timecodes.
The `concat` workflow now also supports manifest-style preview scaffolding and concat playlist manifests for quick playlist authoring.
The library surface also includes higher-level manifest helpers for application code:

```python
from pathlib import Path

from videoedit import (
    VideoEditingService,
    load_manifest,
    plan_render,
    render_canvas,
    render_playlist,
    render_timeline,
    summarize_plan,
)

manifest = load_manifest(Path("examples/manifests/concat-playlist.v1.json"))
plan = plan_render(Path("examples/manifests/concat-playlist.v1.json"))
summary = summarize_plan(Path("examples/manifests/concat-playlist.v1.json"))
```

You can also run the CLI in a shell-neutral way:

```bash
python -m videoedit probe input.mp4
```

For a broader usage guide, see `docs/USAGE.md`.
For a step-by-step first run, see `docs/QUICKSTART.md`.
For the current concat playlist workflow, see `docs/CONCAT_PLAYLIST_GUIDE.md`.
For manifest formats, see `docs/MANIFESTS.md`.
For the current design direction, see `docs/ARCHITECTURE_SESSION.md` and `BACKLOG.md`.
For the testing strategy, see `docs/TEST_PLAN.md`.

## Library usage

```python
from pathlib import Path

from videoedit import VideoEditingService

service = VideoEditingService()
service.trim_video(
    input_path=Path("input.mp4"),
    output_path=Path("output.mp4"),
    start="00:00:03",
    duration="12",
)
```

More complete integration examples live in `examples/python/`.
That directory now also includes a concat playlist manifest example generator in `examples/python/concat_playlist_workflow.py`.

## PowerShell usage

If you want to call the CLI from PowerShell automation, start with `docs/POWERSHELL.md` and the scripts in `examples/powershell/`.

## Git Bash and WSL2 usage

If you want to call the CLI from Git Bash or WSL2 bash, start with `docs/BASH.md` and the scripts in `examples/bash/`.

## Development

Run tests with:

```bash
.\.venv\Scripts\python -m pytest
```

Each registered command is also checked for matching docs and tests, so missing one of the three pieces will fail the suite.

## Testing ownership

`videoedit` is now the canonical implementation and the primary place for behavioral testing.

- `videoedit` owns manifest, service, command, and workflow behavior tests
- `media-tools` and `video_editing_cli` now run compatibility smoke tests rather than the old full suites
- `media-tools` and `video_editing_cli` should now be treated as deprecated compatibility layers
- `videoflow` compatibility coverage is still partial because analysis/generation features have not fully moved into `videoedit`

This means the current test posture is stronger for the migrated core than it was during the wrapper migration. `videoedit` now includes fixture-backed manifest tests, direct render-path coverage for timeline/playlist/canvas entrypoints, generated-media FFmpeg integration tests for timeline and canvas rendering, and golden workflow tests for timeline and playlist planning. It is still not the fully built-out-from-scratch target described in `docs/TEST_PLAN.md`; the next major gap is expanding those real-media integration scenarios across more playlist, normalization, and mixed-format workflows.

## Notes

This project shells out to FFmpeg rather than re-implementing codec logic in Python. That keeps the package lightweight and makes it easy to embed in larger workflows.

## License

MIT. See [LICENSE](LICENSE).

