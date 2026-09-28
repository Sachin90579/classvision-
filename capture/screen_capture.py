"""Screen capture with mss. Screenshots stay in memory and are never written to disk."""
from __future__ import annotations

import io
from dataclasses import dataclass

from core.state import CaptureError

MAX_SEND_WIDTH = 1600  # downscale before upload to keep requests small and fast


@dataclass
class CapturedScreen:
    jpeg: bytes
    width: int   # original monitor size (used for cursor math)
    height: int
    left: int
    top: int


def pick_monitor(monitors: list[dict], cursor: tuple[int, int] | None) -> dict:
    """Choose the monitor containing the cursor, else the first one."""
    if cursor:
        for m in monitors:
            if m["left"] <= cursor[0] < m["left"] + m["width"] and m["top"] <= cursor[1] < m["top"] + m["height"]:
                return m
    return monitors[0]


def capture_screen(cursor: tuple[int, int] | None = None) -> CapturedScreen:
    try:
        import mss
        from PIL import Image

        with mss.mss() as sct:
            monitor = pick_monitor(list(sct.monitors[1:]) or [sct.monitors[0]], cursor)
            shot = sct.grab(monitor)
            image = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        if image.width > MAX_SEND_WIDTH:
            image = image.resize((MAX_SEND_WIDTH, round(image.height * MAX_SEND_WIDTH / image.width)))
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=85)
        return CapturedScreen(buf.getvalue(), monitor["width"], monitor["height"], monitor["left"], monitor["top"])
    except Exception as exc:  # noqa: BLE001 - any capture failure becomes a friendly error
        raise CaptureError(f"Could not capture the screen ({exc}).") from exc
