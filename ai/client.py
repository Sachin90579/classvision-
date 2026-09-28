"""Anthropic Messages API client (multimodal). Sends screenshot + transcript text only, never audio."""
from __future__ import annotations

import base64

import requests

from ai.diagram_schema import DiagramError, DiagramSpec, parse_diagram
from ai.prompts import SYSTEM_PROMPT, build_repair_text, build_user_text
from core.state import ClassVisionError
from utils.logger import get_logger

log = get_logger("ai")
API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"


class AIError(ClassVisionError):
    pass


class AIClient:
    def __init__(self, api_key: str, model: str, timeout: float = 90):
        self.api_key, self.model, self.timeout = api_key, model, timeout

    def generate_diagram(self, *, image: bytes | None, transcript: str, cursor_description: str,
                         previous: tuple[str, str] | None = None) -> DiagramSpec:
        if not self.api_key:
            raise AIError("No API key configured. Open Settings and add your AI API key.")
        content: list[dict] = []
        if image:
            content.append({"type": "image", "source": {
                "type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(image).decode()}})
        content.append({"type": "text", "text": build_user_text(transcript, cursor_description, bool(image), previous)})

        log.info("AI request started")
        raw = self._post([{"role": "user", "content": content}])
        try:
            spec = parse_diagram(raw)
        except DiagramError as exc:
            log.warning("Invalid diagram JSON, attempting one repair: %s", exc)
            raw = self._post([{"role": "user", "content": build_repair_text(raw, str(exc))}])
            spec = parse_diagram(raw)  # raises DiagramError with a readable message
        log.info("AI request completed")
        return spec

    def _post(self, messages: list[dict]) -> str:
        headers = {"x-api-key": self.api_key, "anthropic-version": API_VERSION, "content-type": "application/json"}
        body = {"model": self.model, "max_tokens": 2000, "system": SYSTEM_PROMPT, "messages": messages}
        try:
            resp = requests.post(API_URL, headers=headers, json=body, timeout=self.timeout)
        except requests.exceptions.Timeout as exc:
            raise AIError("The AI service took too long to respond.") from exc
        except requests.exceptions.RequestException as exc:
            raise AIError("Could not reach the AI service. Check your internet connection.") from exc
        if resp.status_code != 200:
            raise AIError(self._explain(resp))
        try:
            blocks = resp.json()["content"]
            return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        except (ValueError, KeyError, TypeError) as exc:
            raise AIError("The AI service returned an unexpected response.") from exc

    @staticmethod
    def _explain(resp: requests.Response) -> str:
        try:
            detail = resp.json().get("error", {}).get("message", "")
        except ValueError:
            detail = ""
        code = resp.status_code
        if code in (401, 403):
            return "The AI service rejected the API key. Check it in Settings."
        if code == 404:
            return f"The AI model was not found. Check the model name in Settings. {detail}".strip()
        if code == 429:
            return "The AI service is rate-limiting requests. Wait a moment and try again."
        if code >= 500:
            return "The AI service is unavailable right now."
        return f"The AI service rejected the request. {detail}".strip()
