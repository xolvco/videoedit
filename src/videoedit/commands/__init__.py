"""Command registry for the video-edit CLI."""

from . import assemble, concat, extract_audio, plan, probe, trim, validate

COMMAND_MODULES = [probe, trim, concat, extract_audio, assemble, validate, plan]

__all__ = ["COMMAND_MODULES"]
