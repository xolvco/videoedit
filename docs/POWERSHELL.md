# PowerShell Integration

This page shows how to call `video-edit` from PowerShell scripts.

## Option 1: call the installed command

After installing the package, you can call the CLI directly:

```powershell
video-edit probe .\input.mp4
video-edit trim .\input.mp4 .\clip.mp4 --start 00:00:10 --duration 20
```

## Option 2: call it through Python during development

If you are working from the repo before installing the command globally:

```powershell
python -m video_editing_cli.cli probe .\input.mp4
```

If needed, set `PYTHONPATH` to include `src` first:

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m video_editing_cli.cli probe .\input.mp4
```

## Capture JSON output

The `probe` command is useful in scripts because it returns JSON:

```powershell
$json = video-edit probe .\input.mp4 | Out-String
$media = $json | ConvertFrom-Json
$media.format.duration
```

## Build a stitched playlist from a manifest

```powershell
video-edit assemble .\examples\manifests\playlist.json .\output.mp4
```

## Fail fast in scripts

Use PowerShell's error handling around CLI calls:

```powershell
$ErrorActionPreference = "Stop"
video-edit trim .\input.mp4 .\clip.mp4 --start 00:00:10 --duration 20
```

## Example scripts

See `examples/powershell/` for runnable starter scripts.
