"""ClassVision AI entry point:  python app.py"""
import sys

# QtWebEngine must be imported before QApplication is created.
from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: F401
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from config.settings import load_settings
from ui.main_window import MainWindow
from ui.widgets import STYLE
from utils.logger import get_logger


def main() -> int:
    log = get_logger("app")
    app = QApplication(sys.argv)
    app.setApplicationName("ClassVision AI")
    app.setStyleSheet(STYLE)
    window = MainWindow(load_settings())
    window.show()
    QTimer.singleShot(400, window.show_system_check)  # first-run system check
    log.info("Main window shown")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
