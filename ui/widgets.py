"""Reusable UI pieces: cards, diagram web view, demo slide."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from diagram.renderer import message_page, svg_page

STYLE = """
* { font-family: 'Segoe UI', Arial, sans-serif; color: #E5E9F0; }
QMainWindow, QDialog, QWidget#root { background: #0B0F19; }
QLabel#title { font-size: 26px; font-weight: 700; }
QLabel#subtitle { color: #8B95A7; font-size: 13px; }
QFrame#card { background: #141B2B; border: 1px solid #222C42; border-radius: 14px; }
QLabel#cardTitle { color: #8B95A7; font-size: 11px; font-weight: 700; letter-spacing: 1px; }
QLabel#body { font-size: 13px; color: #C9D1DE; }
QLabel#toast { background: #1E293B; border-radius: 10px; padding: 10px 14px; color: #E2E8F0; }
QPushButton { background: #1B2438; border: 1px solid #2A3654; border-radius: 10px; padding: 10px 14px; font-size: 14px; }
QPushButton:hover { background: #24304A; }
QPushButton:disabled { color: #566178; background: #131A2A; }
QPushButton:checked { background: #1E3A5F; border-color: #3B82F6; }
QPushButton#primary { background: #2563EB; border: none; font-weight: 700; }
QPushButton#primary:hover { background: #3B82F6; }
QPushButton#accent { background: #7C3AED; border: none; font-weight: 700; }
QPushButton#accent:hover { background: #8B5CF6; }
QProgressBar { background: #1B2438; border: none; border-radius: 3px; max-height: 6px; }
QProgressBar::chunk { background: #7C3AED; border-radius: 3px; }
QLineEdit, QComboBox, QSpinBox { background: #1B2438; border: 1px solid #2A3654; border-radius: 8px; padding: 6px 8px; }
"""


class Card(QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setObjectName("card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(16, 14, 16, 14)
        heading = QLabel(title.upper())
        heading.setObjectName("cardTitle")
        self.body.addWidget(heading)


def body_label(text: str = "") -> QLabel:
    label = QLabel(text)
    label.setObjectName("body")
    label.setWordWrap(True)
    return label


class DiagramView(QWebEngineView):
    """Shows locally generated SVG (no scripts, no network)."""

    def __init__(self):
        super().__init__()
        self.page().setBackgroundColor(QColor("#0F1420"))
        self.show_message("Press F9 to visualize the concept being taught.")

    def show_svg(self, svg: str) -> None:
        self.setHtml(svg_page(svg))

    def show_message(self, message: str) -> None:
        self.setHtml(message_page(message))


class DemoSlide(QWidget):
    """A stand-in 'PowerPoint slide' for demos when no presentation is handy."""

    def __init__(self, screen_width: int):
        super().__init__()
        self.setWindowTitle("ClassVision demo slide")
        width = int(min(960, screen_width * 0.55))
        self.resize(width, int(width * 9 / 16))

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.scale(self.width() / 960, self.height() / 540)
        p.fillRect(0, 0, 960, 540, QColor("#FFFFFF"))
        p.fillRect(0, 0, 960, 12, QColor("#2563EB"))
        p.setPen(QColor("#0F172A"))
        p.setFont(QFont("Segoe UI", 34, QFont.Bold))
        p.drawText(48, 90, "Client–Server Communication")
        p.setFont(QFont("Segoe UI", 20))
        for i, line in enumerate(["• The client sends a request", "• The server processes the request",
                                  "• The server sends a response back"]):
            p.drawText(60, 160 + 44 * i, line)
        for x, label in ((110, "Client (Browser)"), (600, "Web Server")):
            p.setPen(QPen(QColor("#2563EB"), 3))
            p.setBrush(QColor("#DBEAFE"))
            p.drawRoundedRect(QRectF(x, 340, 250, 110), 16, 16)
            p.setPen(QColor("#0F172A"))
            p.setFont(QFont("Segoe UI", 18, QFont.Bold))
            p.drawText(QRectF(x, 340, 250, 110), Qt.AlignCenter, label)
        p.setPen(QPen(QColor("#64748B"), 3))
        p.drawLine(370, 375, 590, 375)
        p.drawLine(590, 420, 370, 420)
        p.setFont(QFont("Segoe UI", 14))
        p.drawText(440, 366, "request")
        p.drawText(438, 448, "response")
