"""Gemini teacher integration for QUOS University.

The worker intentionally uses one provider: Gemini. The API key is read only
from the environment; no credential is stored in source.
"""

from __future__ import annotations

import os
import time
from typing import Any

import requests


DEFAULT_TIMEOUT = float(os.getenv("HTTP_TIMEOUT_SECONDS", "90"))
MAX_RETRIES = int(os.getenv("HTTP_MAX_RETRIES", "2"))


def _post_json(url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    """POST JSON with small exponential backoff and provider-safe diagnostics."""
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
            if not response.ok:
                detail = response.text.strip().replace("\\n", " ")[:800]
                raise RuntimeError(f"HTTP {response.status_code}: {detail}")
            return response.json()
        except (requests.RequestException, RuntimeError, ValueError) as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(2**attempt)
    raise RuntimeError(f"Request failed after retries: {last_error}") from last_error


def _require_key(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def ask_gemini(question: str, *, system_instruction: str | None = None) -> str:
    """Ask Gemini through the Gemini REST generateContent endpoint."""
    api_key = _require_key("GEMINI_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
    prompt = question if not system_instruction else f"{system_instruction}\n\nUser task:\n{question}"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1200},
    }
    data = _post_json(url, {"Content-Type": "application/json", "x-goog-api-key": api_key}, payload)
    try:
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(part.get("text", "") for part in parts)
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected Gemini response: {data}") from exc
    if not text.strip():
        raise RuntimeError("Gemini response contained no text")
    return text.strip()
