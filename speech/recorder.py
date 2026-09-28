"""Microphone capture with a tiny energy-based utterance splitter (audio never leaves the machine)."""
from __future__ import annotations

from typing import Callable

import numpy as np

SAMPLE_RATE = 16_000
BLOCK = 1_600            # 0.1 s
VOICE_THRESHOLD = 0.012  # RMS level treated as speech
SILENCE_END = 0.8        # seconds of silence that end an utterance
MAX_UTTERANCE = 12.0
MIN_UTTERANCE = 0.5
PREROLL_BLOCKS = 3


class MicRecorder:
    def __init__(self, device: str, on_utterance: Callable[[np.ndarray], None]):
        self.device: int | str | None = None if not device else (int(device) if device.isdigit() else device)
        self._on_utterance = on_utterance
        self._stream = None
        self._active = False
        self._chunks: list[np.ndarray] = []
        self._preroll: list[np.ndarray] = []
        self._silence = 0.0

    def start(self) -> None:
        import sounddevice as sd

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32", blocksize=BLOCK,
            device=self.device, callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            finally:
                self._stream = None

    def _callback(self, indata, frames, time_info, status) -> None:  # audio thread: keep it light
        block = indata[:, 0].copy()
        loud = float(np.sqrt(np.mean(block ** 2))) >= VOICE_THRESHOLD
        if not self._active:
            self._preroll.append(block)
            del self._preroll[:-PREROLL_BLOCKS]
            if loud:
                self._active, self._chunks, self._silence = True, list(self._preroll), 0.0
                self._preroll.clear()
            return
        self._chunks.append(block)
        self._silence = 0.0 if loud else self._silence + BLOCK / SAMPLE_RATE
        if self._silence >= SILENCE_END or len(self._chunks) * BLOCK / SAMPLE_RATE >= MAX_UTTERANCE:
            self._flush()

    def _flush(self) -> None:
        audio = np.concatenate(self._chunks)
        self._active, self._chunks, self._silence = False, [], 0.0
        if len(audio) / SAMPLE_RATE >= MIN_UTTERANCE:
            self._on_utterance(audio)
