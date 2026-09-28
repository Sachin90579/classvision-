"""Settings loaded from .env (never hardcode secrets)."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv, set_key

from utils.paths import ENV_PATH

PLACEHOLDER_KEY = "your_api_key_here"


@dataclass
class Settings:
    api_key: str = ""
    model: str = "claude-sonnet-5"
    whisper_model: str = "base"
    mic_device: str = ""
    overlay_position: str = "right"  # "right" | "left"
    transcript_seconds: int = 45
    max_regenerations: int = 5

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key) and self.api_key != PLACEHOLDER_KEY


def _int(value: str | None, default: int) -> int:
    try:
        return max(10, min(300, int(value))) if value else default
    except ValueError:
        return default


def load_settings() -> Settings:
    load_dotenv(ENV_PATH, override=True)
    env = os.environ.get
    return Settings(
        api_key=(env("AI_API_KEY") or "").strip(),
        model=(env("AI_MODEL") or "claude-sonnet-5").strip(),
        whisper_model=(env("WHISPER_MODEL") or "base").strip(),
        mic_device=(env("MIC_DEVICE") or "").strip(),
        overlay_position=(env("OVERLAY_POSITION") or "right").strip().lower(),
        transcript_seconds=_int(env("TRANSCRIPT_SECONDS"), 45),
    )


def save_settings(s: Settings) -> None:
    ENV_PATH.touch(exist_ok=True)
    values = {
        "AI_API_KEY": s.api_key,
        "AI_MODEL": s.model,
        "WHISPER_MODEL": s.whisper_model,
        "MIC_DEVICE": s.mic_device,
        "OVERLAY_POSITION": s.overlay_position,
        "TRANSCRIPT_SECONDS": str(s.transcript_seconds),
    }
    for key, value in values.items():
        set_key(str(ENV_PATH), key, value)
        os.environ[key] = value
