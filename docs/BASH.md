# Bash Integration

This page shows how to call `videoedit` from Git Bash and WSL2 bash.

## Recommended entrypoint

The most portable way to run the CLI across shells is:

```bash
python -m videoedit <command> [arguments]
```

That works well during development and avoids shell-specific launcher differences.

## Install in a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

After installation, you can usually run either form:

```bash
video-edit probe input.mp4
python -m videoedit probe input.mp4
```

## Git Bash notes

- Prefer `python -m videoedit ...` if the generated `video-edit` launcher is not on your `PATH`
- Use POSIX-style paths when possible, for example `./clips/input.mp4`
- Make sure `ffmpeg` and `ffprobe` are available in the same shell session

## WSL2 notes

- Install FFmpeg inside the WSL distribution, not just on Windows
- Work with files on the Linux filesystem or mounted Windows paths such as `/mnt/c/...`
- Use the Linux Python environment inside WSL for the cleanest behavior

## Examples

### Probe metadata

```bash
python -m videoedit probe ./input.mp4
```

### Trim a clip

```bash
python -m videoedit trim ./input.mp4 ./clip.mp4 --start 00:00:05 --duration 15
```

### Extract audio

```bash
python -m videoedit extract-audio ./input.mp4 ./audio.wav
```

### Assemble a titled playlist

```bash
python -m videoedit assemble ./examples/manifests/playlist.json ./output.mp4
```

## Example scripts

See `examples/bash/` for starter shell scripts.

