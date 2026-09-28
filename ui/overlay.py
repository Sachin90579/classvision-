"""Always-on-top diagram overlay: movable, resizable, with Regenerate and Close."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizeGrip, QVBoxLayout, QWidget

from ui.widgets import DiagramView


class DragBar(QFrame):
    """Title bar that moves the whole window when dragged."""

    def __init__(self, window: QWidget):
        super().__init__()
        self._window, self._offset = window, None

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._offset = event.globalPosition().toPoint() - self._window.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._offset is not None:
            self._window.move(event.globalPosition().toPoint() - self._offset)

    def mouseReleaseEvent(self, _event) -> None:  # noqa: N802
        self._offset = None


class OverlayWindow(QWidget):
    regenerate_requested = Signal()

    def __init__(self, position: str = "right"):
        super().__init__()
        self.position = position
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)  # don't steal focus from the slideshow
        self.setMinimumSize(360, 300)
        self.setStyleSheet("QWidget#shell { background: #0F1420; border: 2px solid #2563EB; border-radius: 12px; }")

        shell = QFrame(self)
        shell.setObjectName("shell")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(shell)
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(8, 6, 8, 8)

        bar = DragBar(self)
        row = QHBoxLayout(bar)
        row.setContentsMargins(6, 0, 0, 0)
        self.title = QLabel("ClassVision AI")
        self.title.setStyleSheet("font-weight:700; color:#E5E9F0;")
        self.regen_btn = QPushButton("⟳ Regenerate")
        self.regen_btn.clicked.connect(self.regenerate_requested)
        close_btn = QPushButton("✕")
        close_btn.setFixedWidth(40)
        close_btn.clicked.connect(self.hide)
        for button in (self.regen_btn, close_btn):
            button.setStyleSheet("padding:4px 10px; font-size:13px; color:#E5E9F0; background:#1B2438; "
                                 "border:1px solid #2A3654; border-radius:8px;")
        row.addWidget(self.title, 1)
        row.addWidget(self.regen_btn)
        row.addWidget(close_btn)
        layout.addWidget(bar)

        self.view = DiagramView()
        layout.addWidget(self.view, 1)
        grip_row = QHBoxLayout()
        grip_row.addStretch(1)
        grip_row.addWidget(QSizeGrip(self))
        layout.addLayout(grip_row)
        self.place()

    def place(self) -> None:
        area = QGuiApplication.primaryScreen().availableGeometry()
        w, h = int(area.width() * 0.38), int(area.height() * 0.78)
        x = area.left() + 12 if self.position == "left" else area.right() - w - 12
        self.setGeometry(x, area.top() + (area.height() - h) // 2, w, h)

    def show_diagram(self, svg: str, title: str) -> None:
        self.title.setText(f"ClassVision AI · {title}")
        self.view.show_svg(svg)
        self.setWindowOpacity(1.0)
        self.show()
        self.raise_()

    def set_busy(self, busy: bool) -> None:
        self.regen_btn.setEnabled(not busy)
        self.regen_btn.setText("Generating…" if busy else "⟳ Regenerate")
