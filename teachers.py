"""Provider adapters for the QUOS multi-teacher pipeline.

The worker asks Gemini, DeepSeek, and Groq for independent perspectives. Groq is
also used for the Dean synthesis because its OpenAI-compatible endpoint is
already deployed in production. API keys are read only from environment
variables; no credentials are stored in source.
"""

from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import quote

import requests


DEFAULT_TIMEOUT = float(os.getenv("HTTP_TIMEOUT_SECONDS", "90"))
MAX_RETRIES = int(os.getenv("HTTP_MAX_RETRIES", "2"))
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


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


def _require_key(*names: str) -> str:
    """Return the first configured key, supporting legacy deployment names."""
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    joined = " or ".join(names)
    raise RuntimeError(f"Missing required environment variable: {joined}")


def _extract_openai_text(data: dict[str, Any], provider: str) -> str:
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected {provider} response: {data}") from exc
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError(f"{provider} response contained no text")
    return text.strip()


def _ask_openai_compatible(
    *,
    provider: str,
    url: str,
    key_names: tuple[str, ...],
    model_env: str,
    default_model: str,
    prompt: str,
    system_instruction: str | None,
    token_field: str = "max_tokens",
) -> str:
    api_key = _require_key(*key_names)
    model = os.getenv(model_env, default_model).strip() or default_model
    messages: list[dict[str, str]] = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        token_field: 1200,
        "stream": False,
    }
    data = _post_json(
        url,
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        payload,
    )
    return _extract_openai_text(data, provider)


def ask_groq(prompt: str, *, system_instruction: str | None = None) -> str:
    """Ask Groq through its OpenAI-compatible chat-completions endpoint."""
    return _ask_openai_compatible(
        provider="Groq",
        url=GROQ_URL,
        key_names=("GROQ_API_KEY", "GROQ_KEY"),
        model_env="GROQ_MODEL",
        default_model="openai/gpt-oss-120b",
        prompt=prompt,
        system_instruction=system_instruction,
        token_field="max_completion_tokens",
    )


def ask_deepseek(prompt: str, *, system_instruction: str | None = None) -> str:
    """Ask DeepSeek through its OpenAI-compatible chat-completions endpoint."""
    return _ask_openai_compatible(
        provider="DeepSeek",
        url=DEEPSEEK_URL,
        key_names=("DEEPSEEK_API_KEY", "DEEPSEEK_KEY"),
        model_env="DEEPSEEK_MODEL",
        default_model="deepseek-v4-flash",
        prompt=prompt,
        system_instruction=system_instruction,
    )


def ask_gemini(prompt: str, *, system_instruction: str | None = None) -> str:
    """Ask Gemini through the Gemini REST generateContent endpoint."""
    api_key = _require_key("GEMINI_API_KEY", "GEMINI_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip() or "gemini-1.5-flash"
    url = f"{GEMINI_BASE_URL}/{quote(model, safe='')}:generateContent?key={quote(api_key, safe='')}"
    contents = [{"role": "user", "parts": [{"text": prompt}]}]
    payload: dict[str, Any] = {
        "contents": contents,
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1200},
    }
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
    data = _post_json(url, {"Content-Type": "application/json"}, payload)
    try:
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected Gemini response: {data}") from exc
    if not text.strip():
        raise RuntimeError("Gemini response contained no text")
    return text.strip()
