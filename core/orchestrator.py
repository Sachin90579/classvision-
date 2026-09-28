"""Glue: capture context -> ask AI -> render SVG. Qt-free so it can run on a worker thread."""
from __future__ import annotations

import threading
import time

from ai.client import AIClient
from ai.diagram_schema import DiagramSpec
from capture.cursor_tracker import describe_cursor, get_cursor_position, relative_position
from capture.screen_capture import capture_screen
from config.settings import Settings
from core.session import TranscriptBuffer
from core.state import ClassVisionError, VisualizationContext
from diagram.renderer import render_svg
from utils.logger import get_logger

log = get_logger("orchestrator")


class Orchestrator:
    def __init__(self, settings: Settings, buffer: TranscriptBuffer):
        self.settings, self.buffer = settings, buffer
        self.use_screen = True
        self._lock = threading.Lock()  # prevents duplicate concurrent generations

    def try_begin(self) -> bool:
        return self._lock.acquire(blocking=False)

    def end(self) -> None:
        if self._lock.locked():
            self._lock.release()

    def capture_context(self, settle: float = 0.15) -> VisualizationContext:
        """Grab screen + cursor + recent transcript. `settle` lets our own windows finish hiding."""
        log.info("Visualization triggered")
        time.sleep(settle)
        try:
            cursor = get_cursor_position()
        except Exception as exc:  # noqa: BLE001
            log.warning("Cursor unavailable: %s", exc)
            cursor = None
        transcript = self.buffer.recent_text()
        image, size, rel = None, (0, 0), None
        if self.use_screen:
            shot = capture_screen(cursor)
            image, size = shot.jpeg, (shot.width, shot.height)
            if cursor:
                rel = relative_position(cursor[0], cursor[1], shot.left, shot.top, shot.width, shot.height)
            log.info("Screenshot captured")
        elif not transcript:
            raise ClassVisionError("Nothing to visualize: screen capture is off and no speech has been heard yet.")
        log.info("Transcript received for request (%d chars)", len(transcript))
        return VisualizationContext(image, size, cursor, rel, transcript)

    def generate(self, ctx: VisualizationContext, previous: DiagramSpec | None = None) -> tuple[DiagramSpec, str]:
        client = AIClient(self.settings.api_key, self.settings.model)
        prev = (previous.title, previous.diagram_type) if previous else None
        spec = client.generate_diagram(image=ctx.image, transcript=ctx.transcript,
                                       cursor_description=describe_cursor(ctx.cursor_rel), previous=prev)
        try:
            svg = render_svg(spec)
        except Exception as exc:  # noqa: BLE001
            log.exception("SVG rendering failed")
            raise ClassVisionError("The diagram could not be drawn. Try regenerating.") from exc
        log.info("SVG generated")
        return spec, svg
