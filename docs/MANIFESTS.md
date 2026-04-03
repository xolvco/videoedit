# Manifests

`video-editing-cli` uses versioned JSON manifests as its main data interface.

## Why manifests

They are:

- readable by humans
- easy to generate from other tools
- easy to diff in git
- easier to validate than ad hoc command strings

## Manifest types

Version `1` currently defines two manifest shapes:

- cut list manifests
- timeline manifests
- concat playlist manifests

## Cut list manifest v1

Use this to define reusable moments cut from source footage.

```json
{
  "version": 1,
  "sources": [
    { "id": "session", "path": "session.mp4" }
  ],
  "cuts": [
    {
      "id": "intro-look",
      "source": "session",
      "start": "00:00:05.000",
      "end": "00:00:06.200",
      "label": "Intro glance",
      "tags": ["closeup", "beat"]
    }
  ]
}
```

## Timeline manifest v1

Use this to assemble a final output from reusable cuts.

```json
{
  "version": 1,
  "sources": [
    { "id": "session", "path": "session.mp4" },
    { "id": "closing", "path": "closing.mp4" }
  ],
  "cuts": [
    {
      "id": "intro-look",
      "source": "session",
      "start": "00:00:05.000",
      "end": "00:00:06.200"
    },
    {
      "id": "main-hit",
      "source": "session",
      "start": "00:03:10",
      "duration": "00:00:18.000"
    },
    {
      "id": "closing-shot",
      "source": "closing"
    }
  ],
  "defaults": {
    "gap_after_seconds": 2.0,
    "audio_fade_in_seconds": 0.5,
    "audio_fade_out_seconds": 0.5
  },
  "sections": [
    { "cut": "intro-look", "title": "Intro" },
    { "cut": "main-hit", "title": "Main Segment" },
    { "cut": "closing-shot", "title": "Closing" }
  ],
  "output": {
    "path": "output.mp4"
  }
}
```

## Notes

- `version` is required and currently must be `1`
- time values may be numeric seconds or `HH:MM:SS(.sss)` strings
- cuts should use either `end` or `duration`, not both
- timeline sections reference cuts by id

## Concat playlist manifest v1

Use this to define a linear playlist-style concat job with ordered input items.

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
      "path": "clips/a.mp4",
      "start": "00:00:03",
      "end": "00:00:10",
      "marker": "Clip A",
      "title": "Opening",
      "title_start": 0.25,
      "title_duration": 2.5,
      "title_style": "default"
    },
    {
      "path": "clips/b.mp4",
      "duration": "3.0",
      "audio_fade_out_seconds": 0.75
    }
  ],
  "output": {
    "path": "playlist.mp4"
  }
}
```

Concat playlist notes:

- `items` must contain at least two objects
- each item must define a `path`
- each item may define either `end` or `duration`, not both
- item timing values are relative to that source video
- defaults may supply shared spacer and audio fade values
- `title_styles` may define reusable concat title styles
- items may define `title`, `title_start`, `title_duration`, and `title_style`
- `title_style` must reference a style defined in `title_styles`
