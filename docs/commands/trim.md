# `trim`

## Purpose

Create a clipped section of a video file.

## Usage

```bash
video-edit trim input.mp4 output.mp4 --start 00:00:03 --duration 12
```

Examples:

```bash
video-edit trim input.mp4 output.mp4 --start 00:00:03 --duration 12
video-edit trim input.mp4 output.mp4 --start 00:00:03 --end 00:00:15 --reencode
```

## Options

- `--start`: seek position before reading
- `--end`: stop time in the input timeline
- `--duration`: output duration
- `--reencode`: re-encode instead of stream copy
- `--no-overwrite`: fail if the output file already exists

## Notes

- Use either `--end` or `--duration` for the clearest results
- Stream copy is the default when compatible
