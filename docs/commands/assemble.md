# `assemble`

## Purpose

Build a stitched output video from a JSON manifest so other tools can drive repeatable editorial pipelines.

This command is aimed at workflows like:

- adding black gaps between sections
- fading audio in and out for each section
- creating chapter markers at the start of each section
- assigning a title to each section marker

## Usage

```bash
video-edit assemble manifest.json output.mp4
```

Example:

```bash
video-edit assemble examples/manifests/timeline.v1.json output.mp4
```

Override manifest timing values from the CLI if needed:

```bash
video-edit assemble manifest.json output.mp4 --gap-seconds 2 --audio-fade-seconds 0.5
```

## Manifest format

```json
{
  "version": 1,
  "sources": [
    { "id": "session", "path": "session.mp4" },
    { "id": "closing", "path": "closing.mp4" }
  ],
  "cuts": [
    {
      "id": "intro",
      "source": "session",
      "start": "00:00:05.000",
      "end": "00:00:12.500"
    },
    {
      "id": "main-segment",
      "source": "session",
      "start": "00:03:10",
      "duration": "18.0"
    },
    {
      "id": "closing-shot",
      "source": "closing"
    }
  ],
  "defaults": {
    "gap_after_seconds": 2,
    "audio_fade_in_seconds": 0.5,
    "audio_fade_out_seconds": 0.5
  },
  "sections": [
    { "cut": "intro", "title": "Intro" },
    { "cut": "main-segment", "title": "Main Segment" },
    { "cut": "closing-shot", "title": "Closing" }
  ],
  "output": {
    "path": "output.mp4"
  }
}
```

See [Manifest Formats](../MANIFESTS.md) for the full schema.

## Timeline section fields

- `cut`: required reference to a cut id
- `title`: optional chapter title for the assembled output
- `gap_after_seconds`: optional gap override
- `audio_fade_in_seconds`: optional fade-in override
- `audio_fade_out_seconds`: optional fade-out override

## Notes

- Section titles become chapter titles in the rendered output metadata
- Sections can reuse cuts from the same source file multiple times and reassemble them in a new order
- The command currently assumes each input has both video and audio streams
- Because it uses filters for padding and fades, the output is re-encoded
- A common workflow is `validate` -> `plan` -> `assemble`

