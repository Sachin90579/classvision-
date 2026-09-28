"""Shared types."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ClassVisionError(Exception):
    """Base error whose message is safe to show to a teacher."""


class CaptureError(ClassVisionError):
    pass


class Status(str, Enum):
    READY = "Ready"
    LISTENING = "Listening"
    GENERATING = "Generating"
    ERROR = "Error"


@dataclass
class VisualizationContext:
    image: bytes | None            # JPEG bytes of the screenshot (None if screen capture is off)
    screen_size: tuple[int, int]
    cursor_xy: tuple[int, int] | None
    cursor_rel: tuple[float, float] | None
    transcript: str
