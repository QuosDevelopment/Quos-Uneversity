"""QUOS University teacher integrations.

Each function accepts a question and returns a plain-text answer. API keys are
read only from environment variables; no credentials are stored in source.
"""

from __future__ import annotations

import os
import time
from typing import Any

import requests


DEFAULT_TIMEOUT = float(os.getenv("HTTP_TIMEOUT_SECONDS", "90"))
MAX_RETRIES = int(os.getenv("HTTP_MAX_RETRIES", "2"))


def _post_json(url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    """POST JSON with small exponential backoff for transient failures."""
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(2**attempt)
    raise RuntimeError(f"Request failed after retries: {last_error}") from last_error


def _require_key(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _extract_openai_text(data: dict[str, Any]) -> str:
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected chat-completions response: {data}") from exc
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Chat-completions response contained no text")
    return content.strip()


def ask_gemini(question: str, *, system_instruction: str | None = None) -> str:
    """Ask Gemini through the Gemini REST generateContent endpoint."""
    api_key = _require_key("GEMINI_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
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


def ask_claude(question: str) -> str:
    """Ask Claude through the Anthropic Messages API."""
    api_key = _require_key("CLAUDE_KEY")
    model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5")
    payload = {
        "model": model,
        "max_tokens": 1200,
        "temperature": 0.7,
        "system": "You are a thoughtful teacher at QUOS University. Give practical, nuanced, original guidance.",
        "messages": [{"role": "user", "content": question}],
    }
    data = _post_json(
        "https://api.anthropic.com/v1/messages",
        {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        payload,
    )
    try:
        blocks = data["content"]
        text = "".join(block.get("text", "") for block in blocks if block.get("type") == "text")
    except (KeyError, TypeError) as exc:
        raise RuntimeError(f"Unexpected Claude response: {data}") from exc
    if not text.strip():
        raise RuntimeError("Claude response contained no text")
    return text.strip()


def ask_deepseek(question: str) -> str:
    """Ask DeepSeek through its OpenAI-compatible chat-completions API."""
    api_key = _require_key("DEEPSEEK_KEY")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    payload = {
        "model": model,
        "temperature": 0.7,
        "max_tokens": 1200,
        "messages": [
            {"role": "system", "content": "You are a rigorous QUOS University teacher of habits, money psychology, and personal growth."},
            {"role": "user", "content": question},
        ],
    }
    data = _post_json(
        "https://api.deepseek.com/chat/completions",
        {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        payload,
    )
    return _extract_openai_text(data)


def ask_chatgpt(question: str) -> str:
    """Ask ChatGPT through the OpenAI-compatible chat-completions API."""
    api_key = _require_key("CHATGPT_KEY")
    model = os.getenv("CHATGPT_MODEL", "gpt-4.1-mini")
    payload = {
        "model": model,
        "temperature": 0.7,
        "max_tokens": 1200,
        "messages": [
            {"role": "system", "content": "You are a clear, compassionate QUOS University teacher. Prefer actionable insight over platitudes."},
            {"role": "user", "content": question},
        ],
    }
    data = _post_json(
        os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/") + "/chat/completions",
        {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        payload,
    )
    return _extract_openai_text(data)


TEACHERS = {
    "Gemini": ask_gemini,
    "Claude": ask_claude,
    "DeepSeek": ask_deepseek,
    "ChatGPT": ask_chatgpt,
}
