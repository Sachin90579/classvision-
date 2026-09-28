"""Transcript buffer + session manager (mic, transcription, F9 hotkey). No Qt in here."""
from __future__ import annotations

import queue
import threading
import time
from typing import TYPE_CHECKING, Callable

from speech.trigger_detector import TriggerDetector
from utils.logger import get_logger

if TYPE_CHECKING:
    from config.settings import Settings

log = get_logger("session")
VOICE_UNAVAILABLE = "Voice recognition unavailable. Use F9 to visualize manually."


class TranscriptBuffer:
    """Keeps only the last N seconds of transcribed speech."""

    def __init__(self, seconds: float = 45, clock: Callable[[], float] = time.monotonic):
        self.seconds = seconds
        self._clock = clock
        self._items: list[tuple[float, str]] = []
        self._pinned = ""  # demo-mode transcript that does not expire
        self._lock = threading.Lock()

    def set_seconds(self, seconds: float) -> None:
        self.seconds = seconds

    def add(self, text: str, at: float | None = None) -> None:
        if text.strip():
            with self._lock:
                self._items.append((self._clock() if at is None else at, text.strip()))

    def set_pinned(self, text: str) -> None:
        self._pinned = text

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def recent_text(self, now: float | None = None) -> str:
        now = self._clock() if now is None else now
        with self._lock:
            self._items = [(t, s) for t, s in self._items if now - t <= self.seconds]
            text = " ".join(s for _, s in self._items)
        return text or self._pinned


class SessionManager:
    def __init__(self, settings: Settings, buffer: TranscriptBuffer, *, on_transcript: Callable[[], None],
                 on_trigger: Callable[[str], None], on_hotkey: Callable[[], None], on_notice: Callable[[str], None]):
        self.settings, self.buffer = settings, buffer
        self._on_transcript, self._on_trigger = on_transcript, on_trigger
        self._on_hotkey, self._notice = on_hotkey, on_notice
        self.running = False
        self._stop = threading.Event()
        self._utterances: queue.Queue = queue.Queue(maxsize=20)
        self._hotkeys = None
        self._voice_thread: threading.Thread | None = None
        self._detector = TriggerDetector()

    def start(self, voice: bool = True) -> None:
        if self.running:
            return
        self._stop.clear()
        self.running = True
        log.info("Session started (voice=%s)", voice)
        self._start_hotkey()
        if voice:
            self._voice_thread = threading.Thread(target=self._voice_loop, name="voice", daemon=True)
            self._voice_thread.start()

    def stop(self) -> None:
        if not self.running:
            return
        self._stop.set()
        if self._hotkeys is not None:
            self._hotkeys.stop()
            self._hotkeys = None
        if self._voice_thread is not None:
            self._voice_thread.join(timeout=5)
            self._voice_thread = None
        self.running = False
        log.info("Session stopped")

    def _start_hotkey(self) -> None:
        try:
            from pynput import keyboard

            self._hotkeys = keyboard.GlobalHotKeys({"<f9>": self._on_hotkey})
            self._hotkeys.start()
        except Exception as exc:  # noqa: BLE001
            log.warning("Global hotkey unavailable: %s", exc)
            self._notice("Global F9 hotkey unavailable. F9 works while this window is focused; "
                         "the Visualize Now button always works.")

    def _voice_loop(self) -> None:
        recorder = None
        try:
            from speech.recorder import MicRecorder
            from speech.transcriber import Transcriber

            self._notice("Loading local speech model (first run downloads it)…")
            transcriber = Transcriber(self.settings.whisper_model)
            transcriber.load()
            recorder = MicRecorder(self.settings.mic_device, self._enqueue)
            recorder.start()
            self._notice("Listening. Say “visualize this” or press F9.")
        except Exception as exc:  # noqa: BLE001
            log.warning("Voice unavailable: %s", exc)
            self._notice(VOICE_UNAVAILABLE)
            return
        try:
            while not self._stop.is_set():
                try:
                    audio = self._utterances.get(timeout=0.3)
                except queue.Empty:
                    continue
                try:
                    text = transcriber.transcribe(audio)
                except Exception as exc:  # noqa: BLE001
                    log.warning("Transcription failed: %s", exc)
                    continue
                if text:
                    self.buffer.add(text)
                    log.info("Transcript received (%d chars)", len(text))
                    self._on_transcript()
                    phrase = self._detector.check(text)
                    if phrase:
                        log.info("Voice trigger detected")
                        self._on_trigger(phrase)
        finally:
            if recorder:
                recorder.stop()

    def _enqueue(self, audio) -> None:
        try:
            self._utterances.put_nowait(audio)
        except queue.Full:
            pass  # drop audio rather than block the audio thread
