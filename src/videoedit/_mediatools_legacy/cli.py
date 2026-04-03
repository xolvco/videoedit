"""mediatools CLI — thin wrapper over the library API.

Output format: JSON by default (machine-readable, agentic-friendly).
Use --human for human-readable text output.

Error output always goes to stderr.  Exit code 0 = success, 1 = error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# ── output helpers ────────────────────────────────────────────────────────────

def _out(data: dict, human: bool) -> None:
    """Print *data* as JSON (default) or human-readable text."""
    if human:
        for k, v in data.items():
            print(f"{k}: {v}")
    else:
        print(json.dumps(data, indent=2, default=str))


def _err(message: str, human: bool) -> None:
    """Print an error — always to stderr, always as the right format."""
    if human:
        print(f"error: {message}", file=sys.stderr)
    else:
        print(json.dumps({"error": message}), file=sys.stderr)


# ── commands ──────────────────────────────────────────────────────────────────

def cmd_probe(args: argparse.Namespace) -> int:
    from videoedit._mediatools_legacy.probe import probe, ProbeError
    try:
        info = probe(args.path)
    except (FileNotFoundError, ProbeError) as e:
        _err(str(e), args.human)
        return 1

    streams = []
    for s in info.streams:
        entry = {"codec_type": s.codec_type, "codec_name": s.codec_name}
        if s.codec_type == "video":
            entry.update({"width": s.width, "height": s.height})
        elif s.codec_type == "audio":
            entry.update({"sample_rate": s.sample_rate, "channels": s.channels})
        streams.append(entry)

    data = {
        "path": str(info.path),
        "duration_ms": info.duration_ms,
        "duration_s": round(info.duration_s, 3),
        "format": info.format_name,
        "size_bytes": info.size_bytes,
        "streams": streams,
    }

    if args.human:
        print(f"path:     {info.path}")
        print(f"duration: {info.duration_ms} ms ({info.duration_s:.2f}s)")
        print(f"format:   {info.format_name}")
        print(f"size:     {info.size_bytes:,} bytes")
        for s in info.streams:
            if s.codec_type == "video":
                print(f"video:    {s.codec_name} {s.width}x{s.height}")
            elif s.codec_type == "audio":
                print(f"audio:    {s.codec_name} {s.sample_rate}Hz {s.channels}ch")
    else:
        print(json.dumps(data, indent=2))
    return 0


def cmd_extract_audio(args: argparse.Namespace) -> int:
    from videoedit._mediatools_legacy.audio import extract_audio, AudioError
    try:
        out = extract_audio(args.input, args.output,
                            sample_rate=args.sample_rate,
                            channels=args.channels)
    except (FileNotFoundError, AudioError) as e:
        _err(str(e), args.human)
        return 1

    _out({"path": str(out), "sample_rate": args.sample_rate, "channels": args.channels},
         args.human)
    return 0


def cmd_clip(args: argparse.Namespace) -> int:
    from videoedit._mediatools_legacy.video import clip, VideoError
    try:
        out = clip(args.input, args.output,
                   start_ms=args.start_ms, end_ms=args.end_ms)
    except (FileNotFoundError, ValueError, VideoError) as e:
        _err(str(e), args.human)
        return 1

    _out({"path": str(out), "start_ms": args.start_ms, "end_ms": args.end_ms},
         args.human)
    return 0


def cmd_normalize(args: argparse.Namespace) -> int:
    from videoedit._mediatools_legacy.video import normalize_video, normalize_videos, VideoError
    from pathlib import Path as _Path

    inputs = args.inputs
    try:
        if len(inputs) == 1:
            output = args.output or _Path(inputs[0]).with_stem(
                _Path(inputs[0]).stem + ".norm"
            )
            out = normalize_video(
                inputs[0], output,
                width=args.width, height=args.height,
                fps=args.fps, fit=args.fit, crf=args.crf, preset=args.preset,
            )
            _out({"path": str(out), "width": args.width, "height": args.height,
                  "fps": args.fps, "fit": args.fit}, args.human)
        else:
            output_dir = args.output or _Path(inputs[0]).parent / "normalized"
            outs = normalize_videos(
                inputs, output_dir,
                width=args.width, height=args.height,
                fps=args.fps, fit=args.fit, crf=args.crf, preset=args.preset,
            )
            _out({"count": len(outs), "output_dir": str(output_dir),
                  "paths": [str(p) for p in outs]}, args.human)
    except (FileNotFoundError, VideoError) as e:
        _err(str(e), args.human)
        return 1
    return 0


def cmd_list_videos(args: argparse.Namespace) -> int:
    from videoedit._mediatools_legacy.video import list_videos, VideoError
    try:
        entries = list_videos(args.directory, recursive=args.recursive, sort_by=args.sort_by)
    except (FileNotFoundError, NotADirectoryError, ValueError, VideoError) as e:
        _err(str(e), args.human)
        return 1

    clips = [
        {
            "path": str(e.path),
            "duration_ms": e.duration_ms,
            "size_bytes": e.size_bytes,
            "resolution": f"{e.width}x{e.height}" if e.width and e.height else None,
            "fps": e.fps,
            "codec": e.codec,
        }
        for e in entries
    ]
    _out({"count": len(clips), "directory": str(args.directory), "clips": clips}, args.human)
    return 0


def cmd_init_manifest(args: argparse.Namespace) -> int:
    from videoedit._mediatools_legacy.video import list_videos, write_manifest, VideoError
    try:
        entries = list_videos(args.directory, recursive=args.recursive, sort_by=args.sort_by)
    except (FileNotFoundError, NotADirectoryError, ValueError, VideoError) as e:
        _err(str(e), args.human)
        return 1

    if not entries:
        _err(f"no video files found in {args.directory}", args.human)
        return 1

    manifest_path = args.manifest or (Path(args.directory) / "manifest.json")
    output_video = args.output or (Path(args.directory) / "reel.mp4")
    try:
        written = write_manifest(entries, manifest_path, output_video=output_video)
    except Exception as e:
        _err(str(e), args.human)
        return 1

    _out({"manifest": str(written), "count": len(entries)}, args.human)
    return 0


def cmd_concat(args: argparse.Namespace) -> int:
    from videoedit._mediatools_legacy.video import concat_videos, VideoError
    # Accept either: multiple file paths, or a single manifest.json
    if len(args.inputs) == 1 and args.inputs[0].suffix.lower() == ".json":
        inputs = args.inputs[0]   # manifest path
        output = args.output      # may be None — manifest supplies it
    else:
        inputs = args.inputs
        if args.output is None:
            _err("--output is required when passing file paths directly", args.human)
            return 1
        output = args.output

    try:
        out = concat_videos(inputs, output, re_encode=args.re_encode)
    except (FileNotFoundError, ValueError, VideoError) as e:
        _err(str(e), args.human)
        return 1

    _out({"path": str(out)}, args.human)
    return 0


def cmd_extract_frames(args: argparse.Namespace) -> int:
    from videoedit._mediatools_legacy.video import extract_frames, VideoError
    try:
        frames = extract_frames(
            args.input,
            args.output_dir,
            fps=args.fps,
            start_ms=args.start_ms,
            end_ms=args.end_ms,
            width=args.width,
            height=args.height,
            fmt=args.fmt,
        )
    except (FileNotFoundError, ValueError, VideoError) as e:
        _err(str(e), args.human)
        return 1

    _out({
        "count": len(frames),
        "fps": args.fps,
        "frames": [{"index": f.index, "timestamp_ms": f.timestamp_ms, "path": str(f.path)}
                   for f in frames],
    }, args.human)
    return 0


def cmd_thumbnails_at(args: argparse.Namespace) -> int:
    from videoedit._mediatools_legacy.thumbnails import generate_thumbnails_at, ThumbnailError
    try:
        result = generate_thumbnails_at(
            args.input,
            args.timestamps,
            args.output_dir,
            timestamp_key=args.timestamp_key,
            zip_output=args.zip,
        )
    except (FileNotFoundError, ValueError, ThumbnailError) as e:
        _err(str(e), args.human)
        return 1

    if args.zip:
        _out({"zip": str(result)}, args.human)
    else:
        _out({"count": len(result), "paths": [str(p) for p in result]}, args.human)
    return 0


def cmd_thumbnails(args: argparse.Namespace) -> int:
    from videoedit._mediatools_legacy.thumbnails import generate_thumbnails, ThumbnailError
    try:
        result = generate_thumbnails(
            args.input,
            args.output_dir,
            interval_s=args.interval,
            zip_output=args.zip,
        )
    except (FileNotFoundError, ThumbnailError) as e:
        _err(str(e), args.human)
        return 1

    if args.zip:
        _out({"zip": str(result)}, args.human)
    else:
        _out({"count": len(result), "paths": [str(p) for p in result]}, args.human)
    return 0


def cmd_fetch_info(args: argparse.Namespace) -> int:
    from videoedit._mediatools_legacy.download import fetch_info, DownloadError
    try:
        info = fetch_info(args.url)
    except DownloadError as e:
        _err(str(e), args.human)
        return 1

    if args.human:
        print(f"title:    {info.get('title')}")
        print(f"creator:  {info.get('creator', {}).get('uploader')}")
        print(f"duration: {info.get('duration_s')}s")
        print(f"uploaded: {info.get('upload_date')}")
        print(f"views:    {info.get('view_count')}")
        print(f"formats:  {len(info.get('formats', []))}")
    else:
        print(json.dumps(info, indent=2, default=str))
    return 0


def cmd_convert(args: argparse.Namespace) -> int:
    from videoedit._mediatools_legacy.convert import convert_audio, ConvertError
    try:
        out = convert_audio(
            args.input,
            args.output,
            fmt=args.format,
            bitrate=args.bitrate,
        )
    except (FileNotFoundError, ValueError, ConvertError) as e:
        _err(str(e), args.human)
        return 1

    _out({"path": str(out), "format": args.format, "bitrate": args.bitrate}, args.human)
    return 0


def cmd_pull_video(args: argparse.Namespace) -> int:
    from videoedit._mediatools_legacy.download import pull_video, DownloadError, default_downloads_dir
    import json as _json
    dest = args.output_dir or default_downloads_dir()
    if args.human:
        print(f"downloading to {dest} ...", file=sys.stderr)
    try:
        out = pull_video(
            args.url,
            output_dir=dest,
            filename=args.filename,
            quality=args.quality,
            cookies=args.cookies,
            cookies_from_browser=args.cookies_from_browser,
        )
    except DownloadError as e:
        _err(str(e), args.human)
        return 1

    # Load credits sidecar if present
    credits_path = out.with_name(out.stem + ".credits.json")
    credits = {}
    if credits_path.exists():
        try:
            credits = _json.loads(credits_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    data = {"path": str(out), "credits": credits}
    _out(data, args.human)
    return 0


# ── parser ────────────────────────────────────────────────────────────────────

def _add_human(p: argparse.ArgumentParser) -> None:
    p.add_argument("--human", action="store_true",
                   help="Human-readable text output instead of JSON")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mediatools",
        description="Media processing utilities — JSON output by default",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # probe
    p = sub.add_parser("probe", help="Show metadata for a media file")
    p.add_argument("path", type=Path)
    _add_human(p)
    p.set_defaults(func=cmd_probe)

    # extract-audio
    p = sub.add_parser("extract-audio", help="Extract audio stream from a media file")
    p.add_argument("input", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--sample-rate", type=int, default=44100)
    p.add_argument("--channels", type=int, default=2)
    _add_human(p)
    p.set_defaults(func=cmd_extract_audio)

    # clip
    p = sub.add_parser("clip", help="Clip a media file to a time range")
    p.add_argument("input", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--start-ms", type=int, required=True)
    p.add_argument("--end-ms", type=int, required=True)
    _add_human(p)
    p.set_defaults(func=cmd_clip)

    # normalize
    p = sub.add_parser("normalize",
                       help="Re-encode to consistent resolution, FPS, and format")
    p.add_argument("inputs", type=Path, nargs="+",
                   help="One or more video files to normalize")
    p.add_argument("--output", "-o", type=Path, default=None,
                   help="Output file (single input) or output folder (multiple inputs)")
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--fps", type=float, default=30.0)
    p.add_argument("--fit", default="letterbox",
                   choices=["letterbox", "crop", "stretch"],
                   help="Scaling mode: letterbox (default), crop, or stretch")
    p.add_argument("--crf", type=int, default=18,
                   help="H.264 CRF quality (18=visually lossless, higher=smaller)")
    p.add_argument("--preset", default="fast",
                   choices=["ultrafast", "superfast", "veryfast", "faster",
                             "fast", "medium", "slow", "veryslow"],
                   help="ffmpeg encoding preset (default: fast)")
    _add_human(p)
    p.set_defaults(func=cmd_normalize)

    # list-videos
    p = sub.add_parser("list-videos", help="List video files in a directory with metadata")
    p.add_argument("directory", type=Path)
    p.add_argument("--recursive", "-r", action="store_true",
                   help="Descend into subdirectories")
    p.add_argument("--sort-by", default="name",
                   choices=["name", "mtime", "size", "duration"],
                   help="Sort order (default: name)")
    _add_human(p)
    p.set_defaults(func=cmd_list_videos)

    # init-manifest
    p = sub.add_parser("init-manifest",
                       help="Scan a directory and write a manifest.json for manual reordering")
    p.add_argument("directory", type=Path)
    p.add_argument("--manifest", type=Path, default=None,
                   help="Manifest output path (default: <directory>/manifest.json)")
    p.add_argument("--output", type=Path, default=None,
                   help="Output video path stored in manifest (default: <directory>/reel.mp4)")
    p.add_argument("--recursive", "-r", action="store_true")
    p.add_argument("--sort-by", default="name",
                   choices=["name", "mtime", "size", "duration"])
    _add_human(p)
    p.set_defaults(func=cmd_init_manifest)

    # concat
    p = sub.add_parser("concat",
                       help="Concatenate videos in order — accepts file list or manifest.json")
    p.add_argument("inputs", type=Path, nargs="+",
                   help="Video files to concatenate, or a single manifest.json")
    p.add_argument("--output", "-o", type=Path, default=None,
                   help="Output file (required for file list; manifest supplies default)")
    p.add_argument("--re-encode", action="store_true",
                   help="Re-encode to H.264/AAC (required for mixed-format sources)")
    _add_human(p)
    p.set_defaults(func=cmd_concat)

    # extract-frames
    p = sub.add_parser("extract-frames",
                       help="Extract frames for analysis or assembly pipelines")
    p.add_argument("input", type=Path)
    p.add_argument("--output-dir", type=Path, default=None,
                   help="Destination folder (default: frames/ next to input)")
    p.add_argument("--fps", type=float, default=None,
                   help="Frames per second to extract (default: native fps)")
    p.add_argument("--start-ms", type=int, default=None)
    p.add_argument("--end-ms", type=int, default=None)
    p.add_argument("--width", type=int, default=None,
                   help="Output width (-1 = preserve aspect)")
    p.add_argument("--height", type=int, default=None,
                   help="Output height (-1 = preserve aspect)")
    p.add_argument("--fmt", default="png", choices=["png", "jpg"],
                   help="Output image format (default: png)")
    _add_human(p)
    p.set_defaults(func=cmd_extract_frames)

    # thumbnails-at
    p = sub.add_parser("thumbnails-at",
                       help="Extract PNG thumbnails at specific timestamps from a JSON file")
    p.add_argument("input", type=Path)
    p.add_argument("timestamps", type=Path,
                   help="JSON file containing a 'timestamps' key (ms values or {ms, label} dicts)")
    p.add_argument("--output-dir", type=Path, default=None)
    p.add_argument("--timestamp-key", default="timestamps",
                   help="Key to read from the JSON file (default: timestamps)")
    p.add_argument("--zip", action="store_true", help="Zip all thumbnails on completion")
    _add_human(p)
    p.set_defaults(func=cmd_thumbnails_at)

    # thumbnails
    p = sub.add_parser("thumbnails", help="Extract PNG thumbnails at regular intervals")
    p.add_argument("input", type=Path)
    p.add_argument("--output-dir", type=Path, default=None,
                   help="Output folder (default: thumbnails/ next to input file)")
    p.add_argument("--interval", type=float, default=15.0,
                   help="Seconds between thumbnails (default: 15)")
    p.add_argument("--zip", action="store_true",
                   help="Zip all thumbnails on completion")
    _add_human(p)
    p.set_defaults(func=cmd_thumbnails)

    # fetch-info
    p = sub.add_parser("fetch-info", help="Fetch video metadata without downloading")
    p.add_argument("url")
    _add_human(p)
    p.set_defaults(func=cmd_fetch_info)

    # convert
    p = sub.add_parser("convert", help="Convert media to an audio format (default: mp3)")
    p.add_argument("input", type=Path)
    p.add_argument("output", type=Path, nargs="?", default=None,
                   help="Output path (default: input filename with new extension)")
    p.add_argument("--format", default="mp3",
                   choices=["mp3", "m4a", "wav", "flac", "ogg", "opus"],
                   help="Output format (default: mp3)")
    p.add_argument("--bitrate", default="320k",
                   help="Audio bitrate (default: 320k)")
    _add_human(p)
    p.set_defaults(func=cmd_convert)

    # pull-video
    p = sub.add_parser("pull-video", help="Download a video from a URL")
    p.add_argument("url")
    p.add_argument("--output-dir", type=Path, default=None,
                   help="Destination folder (default: platform Downloads)")
    p.add_argument("--filename", default=None,
                   help="Output filename without extension (default: video title)")
    p.add_argument("--quality", default="bestvideo+bestaudio/best",
                   help="yt-dlp format selector (default: best)")
    p.add_argument("--cookies", type=Path, default=None,
                   help="Path to Netscape-format cookies.txt file")
    p.add_argument("--cookies-from-browser", default=None,
                   metavar="BROWSER",
                   help="Extract cookies from browser: chrome, firefox, edge, safari")
    _add_human(p)
    p.set_defaults(func=cmd_pull_video)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()

