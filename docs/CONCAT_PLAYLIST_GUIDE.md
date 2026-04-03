# Concat Playlist Guide

This guide shows the more flexible concat workflow using a playlist manifest.

It assumes you already know how to:

- create the virtual environment
- install the package
- run `video-edit`
- make sure FFmpeg is available

If not, start with [Quickstart](QUICKSTART.md).

## Goal

Use a manifest to control:

- the order of clips
- per-clip trim timing
- markers
- simple text titles
- gap timing
- audio fade timing
- output path

The starting point for this guide is:

```text
examples/manifests/concat-playlist.v1.json
```

## Example manifest

```json
{
  "version": 1,
  "defaults": {
    "spacer_mode": "black",
    "spacer_seconds": 2.0,
    "audio_fade_in_seconds": 0.5,
    "audio_fade_out_seconds": 0.5
  },
  "title_styles": {
    "default": {
      "anchor": "bottom-left",
      "offset_x": 80,
      "offset_y": 80,
      "font_size": 42,
      "font_color": "#FFFFFF",
      "opacity": 0.92
    }
  },
  "items": [
    {
      "path": "clips/intro.mp4",
      "start": "00:00:03.000",
      "end": "00:00:12.000",
      "marker": "Intro",
      "title": "Opening",
      "title_start": 0.25,
      "title_duration": 2.5,
      "title_style": "default"
    },
    {
      "path": "clips/topic-a.mp4",
      "start": "00:00:10.000",
      "duration": "8.0",
      "marker": "Topic A",
      "audio_fade_in_seconds": 0.75
    },
    {
      "path": "clips/topic-b.mp4",
      "start": "00:00:05.000",
      "duration": "6.5",
      "marker": "Topic B",
      "spacer_seconds": 1.0
    }
  ],
  "output": {
    "path": "playlist-output.mp4"
  }
}
```

## What each section means

### `version`

The manifest version. Right now it must be `1`.

### `defaults`

Shared behavior for the playlist unless an item overrides it.

Current fields:

- `spacer_mode`
- `spacer_seconds`
- `audio_fade_in_seconds`
- `audio_fade_out_seconds`

### `title_styles`

Reusable title styling for playlist item overlays.

Current fields:

- `anchor`
- `offset_x`
- `offset_y`
- `font_size`
- `font_color`
- `opacity`

### `items`

The ordered clips in the final output.

Each item can currently define:

- `path`
- `start`
- `end`
- `duration`
- `marker`
- `title`
- `title_start`
- `title_duration`
- `title_style`
- `audio_fade_in_seconds`
- `audio_fade_out_seconds`
- `spacer_seconds`

### `output`

The default output path for the rendered file.

## Validate and render the manifest

Validate first:

```powershell
video-edit validate .\examples\manifests\concat-playlist.v1.json
```

Then render:

```powershell
video-edit concat .\playlist-output.mp4 --playlist .\examples\manifests\concat-playlist.v1.json
```

## Build your own manifest from a folder

Start with a scaffold:

```powershell
video-edit concat .\playlist-output.mp4 --input-dir .\clips --json-preview --full-preview
```

Then:

1. paste the JSON into a file such as `.\playlist.json`
2. reorder the items
3. edit the trim values
4. change markers, fades, and gaps
5. run `validate`
6. run `concat --playlist`

## How do I scenarios

### How do I set the gap between videos to `0`?

Set the default:

```json
"defaults": {
  "spacer_seconds": 0.0
}
```

Or set one item:

```json
{
  "path": "clips/topic-b.mp4",
  "spacer_seconds": 0.0
}
```

### How do I make one gap shorter than the others?

Keep the shared default in `defaults`, then override one item:

```json
{
  "path": "clips/topic-b.mp4",
  "spacer_seconds": 1.0
}
```

### How do I set the fade in and fade out timing of the audio?

Set shared defaults:

```json
"defaults": {
  "audio_fade_in_seconds": 0.5,
  "audio_fade_out_seconds": 0.5
}
```

Override one item:

```json
{
  "path": "clips/topic-a.mp4",
  "audio_fade_in_seconds": 0.75,
  "audio_fade_out_seconds": 0.75
}
```

### How do I trim one clip differently from the others?

Use per-item timing:

```json
{
  "path": "clips/topic-a.mp4",
  "start": "00:00:10.000",
  "duration": "8.0"
}
```

Use either:

- `start` + `end`
- `start` + `duration`

Do not use `end` and `duration` together in the same item.

### How do I rename markers so they look nicer than filenames?

Add an explicit `marker` field:

```json
{
  "path": "clips/topic-a.mp4",
  "marker": "Topic A"
}
```

### How do I show a simple title on one clip?

Add `title` fields to the item and point at a manifest title style:

```json
{
  "path": "clips/topic-a.mp4",
  "title": "Opening",
  "title_start": 0.25,
  "title_duration": 2.5,
  "title_style": "default"
}
```

Define the reusable style once:

```json
"title_styles": {
  "default": {
    "anchor": "bottom-left",
    "offset_x": 80,
    "offset_y": 80,
    "font_size": 42,
    "font_color": "#FFFFFF",
    "opacity": 0.92
  }
}
```

### How do I use an image between videos?

That is planned but not implemented yet.

For now, only black spacing is supported through `spacer_seconds`.

## Current boundaries

The current concat playlist is already useful, but it does not yet implement:

- image interstitials
- sampled-frame interstitials
- branding bugs
- intro cards
- credits

The current playlist flow does already support:

- text title overlays
- reusable manifest-level title styles
- per-item title timing

Those are planned in the architecture and can be layered onto this manifest approach later.

