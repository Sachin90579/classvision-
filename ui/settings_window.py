"""Settings dialog. Values are saved to .env."""
from __future__ import annotations

from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QSpinBox,
                               QVBoxLayout)

from config.settings import Settings, save_settings

PRIVACY = ("Privacy: speech is transcribed locally with Whisper; raw audio is never uploaded. Only the slide "
           "screenshot, the recent transcript text and the cursor position are sent to the AI service when you "
           "visualize. Screenshots are kept in memory only and are not saved to disk.")


class SettingsWindow(QDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("ClassVision AI · Settings")
        self.setMinimumWidth(480)
        form = QFormLayout()

        self.key = QLineEdit(settings.api_key if settings.has_api_key else "")
        self.key.setEchoMode(QLineEdit.Password)
        self.key.setPlaceholderText("Paste your AI API key")
        self.model = QLineEdit(settings.model)
        self.mic = QComboBox()
        self.mic.addItem("System default", "")
        for index, name in self._input_devices():
            self.mic.addItem(f"{index}: {name}", str(index))
        self.mic.setCurrentIndex(max(0, self.mic.findData(settings.mic_device)))
        self.overlay = QComboBox()
        self.overlay.addItems(["right", "left"])
        self.overlay.setCurrentText(settings.overlay_position if settings.overlay_position in ("right", "left") else "right")
        self.seconds = QSpinBox()
        self.seconds.setRange(10, 300)
        self.seconds.setSuffix(" seconds")
        self.seconds.setValue(settings.transcript_seconds)
        self.whisper = QComboBox()
        self.whisper.addItems(["tiny", "base", "small", "medium"])
        self.whisper.setCurrentText(settings.whisper_model)

        form.addRow("AI API key", self.key)
        form.addRow("AI model", self.model)
        form.addRow("Microphone", self.mic)
        form.addRow("Overlay position", self.overlay)
        form.addRow("Transcript duration", self.seconds)
        form.addRow("Whisper model", self.whisper)

        notice = QLabel(PRIVACY)
        notice.setWordWrap(True)
        notice.setStyleSheet("color:#8B95A7; font-size:12px;")
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(notice)
        layout.addWidget(buttons)

    @staticmethod
    def _input_devices() -> list[tuple[int, str]]:
        try:
            import sounddevice as sd
            return [(i, d["name"]) for i, d in enumerate(sd.query_devices()) if d["max_input_channels"] > 0]
        except Exception:  # noqa: BLE001
            return []

    def _save(self) -> None:
        s = self.settings
        s.api_key = self.key.text().strip()
        s.model = self.model.text().strip() or s.model
        s.mic_device = self.mic.currentData() or ""
        s.overlay_position = self.overlay.currentText()
        s.transcript_seconds = self.seconds.value()
        s.whisper_model = self.whisper.currentText()
        save_settings(s)
        self.accept()
