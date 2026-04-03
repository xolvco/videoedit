# `probe`

## Purpose

Inspect a media file with `ffprobe` and print JSON metadata for use in scripts or other applications.

## Usage

```bash
video-edit probe input.mp4
```

Example:

```bash
video-edit probe input.mp4
```

## Notes

- Returns machine-readable JSON to standard output
- Useful for validating streams, codecs, duration, and container metadata
- Often useful before building trims, concat playlists, or timeline manifests

