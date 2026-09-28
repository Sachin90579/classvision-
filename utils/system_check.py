"""Start-up checks that tell the teacher exactly what to fix."""
from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass


@dataclass
class CheckResult:
    name: str
    ok: bool
    hint: str = ""


def _has(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def run_system_check(settings) -> list[CheckResult]:
    results = [CheckResult("Python 3.11+", sys.version_info >= (3, 11), f"Found {sys.version.split()[0]}; install Python 3.11 or newer.")]
    modules = ["PySide6", "mss", "pyautogui", "pynput", "faster_whisper", "sounddevice", "pydantic", "requests", "PIL", "dotenv"]
    missing = [m for m in modules if not _has(m)]
    results.append(CheckResult("Required packages", not missing, f"Missing: {', '.join(missing)}. Run: pip install -r requirements.txt"))

    try:
        import mss
        with mss.mss() as sct:
            sct.grab({"left": 0, "top": 0, "width": 2, "height": 2})
        results.append(CheckResult("Screen capture", True))
    except Exception as exc:  # noqa: BLE001
        results.append(CheckResult("Screen capture", False, f"Screen capture failed: {exc}"))

    results.append(CheckResult("Keyboard shortcut (F9)", _has("pynput"), "Install pynput: pip install pynput"))
    results.append(CheckResult("AI configuration", settings.has_api_key, "Add AI_API_KEY to .env or open Settings."))

    try:
        import sounddevice as sd
        has_mic = any(d["max_input_channels"] > 0 for d in sd.query_devices())
        results.append(CheckResult("Microphone", has_mic, "No microphone found. F9 and Demo Mode still work."))
    except Exception as exc:  # noqa: BLE001
        results.append(CheckResult("Microphone", False, f"Microphone unavailable ({exc}). F9 and Demo Mode still work."))

    results.append(CheckResult("Local speech engine (Whisper)", _has("faster_whisper"),
                               "Install faster-whisper. Without it, use F9 to visualize manually."))
    return results
