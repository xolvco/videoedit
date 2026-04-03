# `extract-audio`

## Purpose

Export the audio stream from a media file.

## Usage

```bash
video-edit extract-audio input.mp4 audio.wav
```

Example:

```bash
video-edit extract-audio input.mp4 audio.wav --codec pcm_s16le
```

## Options

- `--codec`: override the audio codec
- `--no-overwrite`: fail if the output file already exists

## Notes

- The command removes video streams from the output
- Use `--codec` when you want a specific output format or encoder

