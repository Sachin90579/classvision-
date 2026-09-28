"""Main ClassVision AI window."""
from __future__ import annotations

import threading

from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QProgressBar, QPushButton,
                               QVBoxLayout, QWidget)

from ai.diagram_schema import DiagramSpec
from capture.cursor_tracker import get_cursor_position
from config.settings import Settings
from core.orchestrator import Orchestrator
from core.session import SessionManager, TranscriptBuffer
from core.state import ClassVisionError, Status, VisualizationContext
from ui.overlay import OverlayWindow
from ui.settings_window import SettingsWindow
from ui.widgets import Card, DemoSlide, DiagramView, body_label
from utils.logger import get_logger
from utils.system_check import CheckResult, run_system_check

log = get_logger("ui")
DEMO_TRANSCRIPT = ("The client sends a request to the server. The server processes the request "
                   "and sends the response back to the client.")
STATUS_COLORS = {Status.READY: "#22C55E", Status.LISTENING: "#3B82F6", Status.GENERATING: "#F59E0B", Status.ERROR: "#EF4444"}


class MainWindow(QMainWindow):
    # Signals let background threads talk to the UI safely.
    sig_transcript = Signal()
    sig_trigger = Signal(str)
    sig_hotkey = Signal()
    sig_notice = Signal(str)
    sig_captured = Signal(object)
    sig_done = Signal(object, str)
    sig_failed = Signal(str)

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.buffer = TranscriptBuffer(settings.transcript_seconds)
        self.orchestrator = Orchestrator(settings, self.buffer)
        self.session = SessionManager(
            settings, self.buffer, on_transcript=self.sig_transcript.emit, on_trigger=self.sig_trigger.emit,
            on_hotkey=self.sig_hotkey.emit, on_notice=self.sig_notice.emit)
        self.overlay = OverlayWindow(settings.overlay_position)
        self.demo_slide: DemoSlide | None = None
        self.last_ctx: VisualizationContext | None = None
        self.last_spec: DiagramSpec | None = None
        self.regen_used = 0
        self._toast_id = 0

        self._build_ui()
        self.sig_transcript.connect(self._refresh_context)
        self.sig_trigger.connect(lambda _phrase: self.begin_visualization())
        self.sig_hotkey.connect(self.begin_visualization)
        self.sig_notice.connect(self._toast)
        self.sig_captured.connect(self._on_captured)
        self.sig_done.connect(self._on_done)
        self.sig_failed.connect(self._on_failed)
        self.overlay.regenerate_requested.connect(lambda: self.begin_visualization(alternative=True))
        QShortcut(QKeySequence("F9"), self, activated=self.begin_visualization)  # works when this window is focused

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_context)
        self._timer.start(1000)
        self._set_status(Status.READY)
        log.info("Application started")

    # ---------- UI construction ----------
    def _build_ui(self) -> None:
        self.setWindowTitle("ClassVision AI")
        self.resize(1180, 760)
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        title = QLabel("ClassVision AI")
        title.setObjectName("title")
        tagline = QLabel("AI Teaching Visualizer · Visualizing every explanation, live.")
        tagline.setObjectName("subtitle")
        titles.addWidget(title)
        titles.addWidget(tagline)
        self.status_label = QLabel()
        settings_btn = QPushButton("⚙  Settings")
        settings_btn.clicked.connect(self.open_settings)
        check_btn = QPushButton("System check")
        check_btn.clicked.connect(self.show_system_check)
        header.addLayout(titles, 1)
        header.addWidget(self.status_label)
        header.addWidget(check_btn)
        header.addWidget(settings_btn)
        outer.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(16)
        left = QVBoxLayout()
        left.setSpacing(12)

        self.start_btn = QPushButton("▶  Start Session")
        self.start_btn.setObjectName("primary")
        self.start_btn.clicked.connect(self.start_session)
        self.stop_btn = QPushButton("■  Stop Session")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_session)
        toggles = QHBoxLayout()
        self.mic_btn = QPushButton("🎤 Microphone")
        self.screen_btn = QPushButton("🖥 Screen Capture")
        for b in (self.mic_btn, self.screen_btn):
            b.setCheckable(True)
            b.setChecked(True)
            toggles.addWidget(b)
        self.screen_btn.toggled.connect(lambda on: setattr(self.orchestrator, "use_screen", on))
        self.visualize_btn = QPushButton("✨  Visualize Now      F9")
        self.visualize_btn.setObjectName("accent")
        self.visualize_btn.clicked.connect(lambda: self.begin_visualization())
        self.demo_btn = QPushButton("Load Demo Slide")
        self.demo_btn.clicked.connect(self.load_demo)
        for w in (self.start_btn, self.stop_btn):
            left.addWidget(w)
        left.addLayout(toggles)
        left.addWidget(self.visualize_btn)
        left.addWidget(self.demo_btn)

        transcript_card = Card("Recent explanation")
        self.transcript_label = body_label()
        transcript_card.body.addWidget(self.transcript_label)
        context_card = Card("Context")
        self.slide_label, self.cursor_label, self.speech_label = body_label(), body_label(), body_label()
        for w in (self.slide_label, self.cursor_label, self.speech_label):
            context_card.body.addWidget(w)
        left.addWidget(transcript_card, 1)
        left.addWidget(context_card)
        left_holder = QWidget()
        left_holder.setLayout(left)
        left_holder.setFixedWidth(380)
        body.addWidget(left_holder)

        preview = Card("Generated diagram")
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # indeterminate loading animation
        self.progress.setTextVisible(False)
        self.progress.hide()
        self.preview = DiagramView()
        preview.body.addWidget(self.progress)
        preview.body.addWidget(self.preview, 1)
        body.addWidget(preview, 1)
        outer.addLayout(body, 1)

        self.toast = QLabel()
        self.toast.setObjectName("toast")
        self.toast.setWordWrap(True)
        self.toast.hide()
        outer.addWidget(self.toast)
        self._refresh_context()

    # ---------- status / feedback ----------
    def _set_status(self, status: Status) -> None:
        color = STATUS_COLORS[status]
        self.status_label.setText(f"● {status.value}")
        self.status_label.setStyleSheet(f"color:{color}; font-weight:700; padding:6px 14px; background:#141B2B; "
                                        f"border:1px solid {color}; border-radius:14px;")

    def _idle_status(self) -> Status:
        return Status.LISTENING if self.session.running else Status.READY

    def _toast(self, message: str) -> None:
        self._toast_id += 1
        current = self._toast_id
        self.toast.setText(message)
        self.toast.show()
        QTimer.singleShot(9000, lambda: self.toast.hide() if current == self._toast_id else None)

    def _refresh_context(self) -> None:
        text = self.buffer.recent_text()
        self.transcript_label.setText(f"“…{text[-350:]}”" if text else "No speech yet. Press F9 any time.")
        try:
            self.cursor_label.setText("Cursor: {}, {}".format(*get_cursor_position()))
        except Exception:  # noqa: BLE001
            self.cursor_label.setText("Cursor: unavailable")
        self.slide_label.setText("Current slide: Captured" if self.last_ctx and self.last_ctx.image else "Current slide: Not captured yet")
        self.speech_label.setText("Transcript: Available" if text else "Transcript: Empty")

    # ---------- session ----------
    def start_session(self) -> None:
        self.buffer.set_seconds(self.settings.transcript_seconds)
        self.session.start(voice=self.mic_btn.isChecked())
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._set_status(Status.LISTENING)
        self._toast("Session started. Open your slides, then press F9 (or say “visualize this”).")

    def stop_session(self) -> None:
        self.session.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._set_status(Status.READY)

    def open_settings(self) -> None:
        if SettingsWindow(self.settings, self).exec() == QDialog.Accepted:
            self.buffer.set_seconds(self.settings.transcript_seconds)
            self.overlay.position = self.settings.overlay_position
            self.overlay.place()
            self._toast("Settings saved.")

    def show_system_check(self) -> None:
        results: list[CheckResult] = run_system_check(self.settings)
        lines = [f"{'✓' if r.ok else '✗'} {r.name}" + ("" if r.ok else f"\n    → {r.hint}") for r in results]
        ready = all(r.ok for r in results)
        QMessageBox.information(self, "System check", "System check\n\n" + "\n".join(lines) + (
            "\n\nReady to start." if ready else
            "\n\nFix the items marked ✗. F9 and Demo Mode work even without a microphone."))

    def load_demo(self) -> None:
        if self.demo_slide is None:
            self.demo_slide = DemoSlide(QGuiApplication.primaryScreen().availableGeometry().width())
        self.demo_slide.move(40, 70)
        self.demo_slide.show()
        self.buffer.set_pinned(DEMO_TRANSCRIPT)
        self._refresh_context()
        self._toast("Demo slide loaded. Put your cursor on it and press F9 (or click Visualize Now).")

    # ---------- visualization pipeline ----------
    def begin_visualization(self, alternative: bool = False) -> None:
        if alternative and (self.last_ctx is None or self.last_spec is None):
            return
        if alternative and self.regen_used >= self.settings.max_regenerations:
            self._toast("Regeneration limit reached for this slide. Press F9 to start fresh.")
            return
        if not self.orchestrator.try_begin():
            self._toast("Still generating. Please wait for the current visualization.")
            return
        if alternative:
            self.regen_used += 1
        else:
            self.regen_used = 0
        self._set_status(Status.GENERATING)
        self.progress.show()
        self.overlay.set_busy(True)
        self.preview_msg("Generating visualization...")
        if not alternative:  # make our own windows invisible to the screenshot without stealing focus
            self.overlay.setWindowOpacity(0.0)
            self.setWindowOpacity(0.0)
        threading.Thread(target=self._pipeline, args=(alternative,), daemon=True, name="visualize").start()

    def preview_msg(self, message: str) -> None:
        if self.last_spec is None:
            self.preview.show_message(message)

    def _pipeline(self, alternative: bool) -> None:
        try:
            ctx = self.last_ctx if alternative and self.last_ctx else self.orchestrator.capture_context()
            self.last_ctx = ctx
            self.sig_captured.emit(ctx)
            spec, svg = self.orchestrator.generate(ctx, previous=self.last_spec if alternative else None)
            self.sig_done.emit(spec, svg)
        except ClassVisionError as exc:
            log.warning("Visualization failed: %s", exc)
            self.sig_failed.emit(str(exc))
        except Exception:  # noqa: BLE001 - never crash the app
            log.exception("Unexpected error")
            self.sig_failed.emit("Something unexpected went wrong. Details are in logs/classvision.log.")

    def _restore_windows(self) -> None:
        self.setWindowOpacity(1.0)
        if self.overlay.isVisible():
            self.overlay.setWindowOpacity(1.0)

    def _on_captured(self, _ctx) -> None:
        self._restore_windows()
        self._refresh_context()

    def _on_done(self, spec: DiagramSpec, svg: str) -> None:
        self.orchestrator.end()
        self.last_spec = spec
        self._restore_windows()
        self.progress.hide()
        self.preview.show_svg(svg)
        self.overlay.set_busy(False)
        self.overlay.show_diagram(svg, spec.title)
        self._set_status(self._idle_status())
        log.info("Overlay displayed")

    def _on_failed(self, reason: str) -> None:
        self.orchestrator.end()
        self._restore_windows()
        self.progress.hide()
        self.overlay.set_busy(False)
        self._set_status(Status.ERROR)
        message = (f"Unable to generate visualization.\n\nReason:\n{reason}\n\n"
                   "Try again, or continue teaching and press F9 later.")
        if not self.settings.has_api_key:
            message += "\n\nAI generation unavailable without an API key. You can still capture the slide and view the transcript."
        self.preview.show_message(message)
        self._toast(reason)
        QTimer.singleShot(4000, lambda: self._set_status(self._idle_status()))

    def closeEvent(self, event) -> None:  # noqa: N802
        self.session.stop()
        self.overlay.close()
        if self.demo_slide:
            self.demo_slide.close()
        event.accept()
        QApplication.quit()
