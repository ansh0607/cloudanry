"""Minimal async Groq client (OpenAI-compatible chat completions).

One API key, multiple models — each role (vision / supporting / adversarial)
uses its own model id, overridable via env. No vendor SDK: plain httpx.
"""
import base64
import json
import re
from typing import Any, Optional

import httpx

from backend.core.config import get_settings


class GroqError(RuntimeError):
    pass


def _headers() -> dict[str, str]:
    settings = get_settings()
    if not settings.groq_configured:
        raise GroqError(
            "Groq is not configured. Set GROQ_API_KEY in .env (get a free key at "
            "https://console.groq.com/keys)."
        )
    return {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }


async def chat(
    messages: list[dict[str, Any]],
    model: str,
    temperature: float = 0.2,
    max_tokens: int = 1500,
) -> str:
    """Send a chat completion request to Groq. Returns the assistant text."""
    settings = get_settings()
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{settings.groq_base_url}/chat/completions",
            headers=_headers(),
            json=payload,
        )
        if resp.status_code != 200:
            raise GroqError(f"Groq API error {resp.status_code}: {resp.text[:500]}")
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError) as e:
            raise GroqError(f"Unexpected Groq response shape: {data}") from e


async def chat_json(
    messages: list[dict[str, Any]],
    model: str,
    temperature: float = 0.2,
    max_tokens: int = 1500,
) -> dict[str, Any]:
    """Chat completion that parses the reply as JSON (tolerates code fences)."""
    text = await chat(messages, model=model, temperature=temperature, max_tokens=max_tokens)
    return parse_json_object(text)


def image_data_url(image_bytes: bytes, mime: str = "image/jpeg") -> str:
    """Encode image bytes as a data URL for vision messages."""
    return f"data:{mime};base64,{base64.b64encode(image_bytes).decode('ascii')}"


def parse_json_object(text: str) -> dict[str, Any]:
    """Best-effort JSON extraction from a model reply."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    # Last resort: first {...} block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    return {}
