"""Groq teacher integration for QUOS University.

The worker uses Groq's OpenAI-compatible chat-completions API. The API key is
read only from the environment; no credential is stored in source.
"""

from __future__ import annotations

import os
import time
from typing import Any

import requests


DEFAULT_TIMEOUT = float(os.getenv("HTTP_TIMEOUT_SECONDS", "90"))
MAX_RETRIES = int(os.getenv("HTTP_MAX_RETRIES", "2"))
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _post_json(url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    """POST JSON with bounded exponential backoff and provider-safe diagnostics."""
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
            if not response.ok:
                detail = response.text.strip().replace("\n", " ")[:800]
                retry_after = response.headers.get("retry-after")
                suffix = f"; retry-after={retry_after}s" if retry_after else ""
                raise RuntimeError(f"HTTP {response.status_code}: {detail}{suffix}")
            return response.json()
        except (requests.RequestException, RuntimeError, ValueError) as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(min(30, 4**attempt))
    raise RuntimeError(f"Request failed after retries: {last_error}") from last_error


def _require_key(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def ask_groq(prompt: str, *, system_instruction: str | None = None) -> str:
    """Ask Groq through its OpenAI-compatible chat-completions endpoint."""
    api_key = _require_key("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    messages: list[dict[str, str]] = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_completion_tokens": 1200,
        "stream": False,
    }
    data = _post_json(
        GROQ_URL,
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        payload,
    )
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected Groq response: {data}") from exc
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("Groq response contained no text")
    return text.strip()
