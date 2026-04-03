"""mediatools — reusable media processing utilities."""

from videoedit._mediatools_legacy.convert import convert_audio, convert_to_mp3
from videoedit._mediatools_legacy.download import fetch_info, pull_video
from videoedit._mediatools_legacy.media_file import MediaFile
from videoedit._mediatools_legacy.probe import probe
from videoedit._mediatools_legacy.thumbnails import generate_thumbnails, generate_thumbnails_at
from videoedit._mediatools_legacy.video import (
    FrameInfo, VideoEntry,
    extract_frames, list_videos,
    write_manifest, read_manifest, concat_videos,
    normalize_video, normalize_videos,
)

__all__ = [
    "MediaFile", "probe", "pull_video", "fetch_info",
    "convert_to_mp3", "convert_audio",
    "generate_thumbnails", "generate_thumbnails_at",
    "extract_frames", "FrameInfo",
    "list_videos", "VideoEntry",
    "write_manifest", "read_manifest", "concat_videos",
    "normalize_video", "normalize_videos",
]
__version__ = "0.1.0"

