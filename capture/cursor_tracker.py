"""Cursor position helpers."""
from __future__ import annotations


def get_cursor_position() -> tuple[int, int]:
    import pyautogui  # imported lazily so tests/headless machines don't need a display

    pos = pyautogui.position()
    return int(pos.x), int(pos.y)


def relative_position(x: float, y: float, left: float, top: float, width: float, height: float) -> tuple[float, float]:
    """Convert screen coordinates to 0..1 fractions of a captured region (clamped)."""
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    rx = min(1.0, max(0.0, (x - left) / width))
    ry = min(1.0, max(0.0, (y - top) / height))
    return rx, ry


def describe_cursor(rel: tuple[float, float] | None) -> str:
    if rel is None:
        return "The cursor position is unavailable."
    return (
        f"The teacher's cursor is approximately at {rel[0] * 100:.0f}% width and "
        f"{rel[1] * 100:.0f}% height of the screenshot.\n"
        "Use this location as a hint for the part of the slide currently being discussed."
    )
