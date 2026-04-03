from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest


@dataclass
class GeneratedMediaWorkspace:
    root: Path
    media_dir: Path
    manifests_dir: Path

    def create_video(
        self,
        name: str,
        *,
        duration_seconds: float = 1.0,
        size: tuple[int, int] = (160, 90),
        color: str = "navy",
        tone_hz: int = 440,
        fps: int = 24,
    ) -> Path:
        path = self.media_dir / name
        width, height = size
        _run_process(
            [
                "ffmpeg",
                "-hide_banner",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c={color}:s={width}x{height}:d={duration_seconds}:r={fps}",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency={tone_hz}:duration={duration_seconds}:sample_rate=44100",
                "-shortest",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "96k",
                str(path),
            ]
        )
        return path

    def write_manifest(self, name: str, payload: dict[str, object]) -> Path:
        path = self.manifests_dir / name
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path


def _run_process(args: list[str]) -> None:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "Command failed:\n"
            f"{' '.join(args)}\n\n"
            f"stdout:\n{result.stdout}\n\n"
            f"stderr:\n{result.stderr}"
        )


@pytest.fixture
def generated_media_workspace(tmp_path: Path) -> GeneratedMediaWorkspace:
    media_dir = tmp_path / "media"
    manifests_dir = tmp_path / "manifests"
    media_dir.mkdir()
    manifests_dir.mkdir()
    return GeneratedMediaWorkspace(
        root=tmp_path,
        media_dir=media_dir,
        manifests_dir=manifests_dir,
    )
