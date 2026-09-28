"""Simple file + console logging. Never log API keys, audio or screenshots."""
import logging
from logging.handlers import RotatingFileHandler

from utils.paths import LOG_DIR

_configured = False


def _setup() -> None:
    global _configured
    if _configured:
        return
    LOG_DIR.mkdir(exist_ok=True)
    root = logging.getLogger("classvision")
    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    file_handler = RotatingFileHandler(LOG_DIR / "classvision.log", maxBytes=500_000, backupCount=2, encoding="utf-8")
    file_handler.setFormatter(fmt)
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(file_handler)
    root.addHandler(console)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    _setup()
    return logging.getLogger(f"classvision.{name}")
