"""Low-level media helpers exposed from the unified backend."""

from ._mediatools_legacy import (
    MediaFile,
    VideoEntry,
    concat_videos as legacy_concat_videos,
    convert_audio,
    convert_to_mp3,
    extract_frames,
    fetch_info,
    generate_thumbnails,
    generate_thumbnails_at,
    list_videos,
    normalize_video,
    normalize_videos,
    pull_video,
    read_manifest,
    write_manifest,
)
from ._mediatools_legacy.audio import AudioError, extract_audio as extract_audio_file
from ._mediatools_legacy.download import DownloadError, default_downloads_dir
from ._mediatools_legacy.probe import ProbeError, ProbeResult, StreamInfo, probe
from ._mediatools_legacy.thumbnails import ThumbnailError
from ._mediatools_legacy.video import FrameInfo, VideoError, clip
from .operations import concat_playlist, probe_media, trim_video

concat_videos = legacy_concat_videos

__all__ = [
    "AudioError",
    "DownloadError",
    "FrameInfo",
    "MediaFile",
    "ProbeError",
    "ProbeResult",
    "StreamInfo",
    "ThumbnailError",
    "VideoEntry",
    "VideoError",
    "clip",
    "concat_playlist",
    "concat_videos",
    "convert_audio",
    "convert_to_mp3",
    "default_downloads_dir",
    "extract_audio_file",
    "extract_frames",
    "fetch_info",
    "generate_thumbnails",
    "generate_thumbnails_at",
    "legacy_concat_videos",
    "list_videos",
    "normalize_video",
    "normalize_videos",
    "probe",
    "probe_media",
    "pull_video",
    "read_manifest",
    "trim_video",
    "write_manifest",
]
