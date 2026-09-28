"""Local speech-to-text using faster-whisper (CPU, int8)."""
from __future__ import annotations

import numpy as np


class Transcriber:
    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None

    def load(self) -> None:
        from faster_whisper import WhisperModel  # first run downloads the model once

        self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")

    def transcribe(self, audio: np.ndarray) -> str:
        if self._model is None:
            self.load()
        segments, _info = self._model.transcribe(audio, beam_size=1, vad_filter=True, condition_on_previous_text=False)
        return " ".join(seg.text.strip() for seg in segments).strip()
