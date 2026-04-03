# `plan`

## Purpose

Resolve an assembly manifest into JSON without rendering media.

This is useful when you want to inspect:

- the resolved sections and titles
- the effective gaps and audio fade values
- the final output path
- the FFmpeg command arguments that would be used for rendering

## Usage

```bash
video-edit plan manifest.json output.mp4
```

Example:

```bash
video-edit plan examples/manifests/timeline.v1.json output.mp4
```

Override manifest timing values from the CLI if needed:

```bash
video-edit plan manifest.json output.mp4 --gap-seconds 2 --audio-fade-seconds 0.5
```

## Output

The command prints JSON describing the resolved plan.

Example fields include:

- `manifest_path`
- `output_path`
- `section_count`
- `sections`
- `ffmpeg_args`

## Notes

- `plan` does not render media
- `plan` currently targets the same timeline manifests used by `assemble`
- referenced source files must exist so the plan can be resolved
- Use `plan` after `validate` when you want to inspect the resolved output before rendering
- See [Manifest Formats](../MANIFESTS.md) for the timeline manifest structure

