"""OpenRouter client — backend only.

Why OpenRouter (over a vendor SDK):
  * One key, many models. Swap providers per-feature via env / per-call argument.
  * OpenAI-compatible /chat/completions schema, so the wire format stays familiar.
  * Built-in fallback list — if the primary model 429s or errors, the next one runs.

This module is the single chokepoint for every AI call in the backend.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class AIClientError(Exception):
    """Anything that prevented us from getting a usable model response."""


class AIDisabledError(AIClientError):
    """No API key configured — caller should fall back to the deterministic engine."""


@dataclass(frozen=True)
class ChatResult:
    model: str
    content: str
    usage: dict[str, Any] | None
    raw: dict[str, Any]


def _headers() -> dict[str, str]:
    h = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        # Optional but recommended by OpenRouter for app-attribution.
        "HTTP-Referer": settings.OPENROUTER_HTTP_REFERER,
        "X-Title": settings.OPENROUTER_APP_TITLE,
    }
    return h


def chat(
    *,
    system: str,
    user: str,
    model: str | None = None,
    fallback_models: list[str] | None = None,
    max_tokens: int = 800,
    temperature: float = 0.2,
    response_format_json: bool = False,
) -> ChatResult:
    """Synchronous chat completion call. Raises AIClientError on any failure."""
    if not settings.ai_enabled:
        raise AIDisabledError("OPENROUTER_API_KEY is not set")

    primary = model or settings.OPENROUTER_MODEL
    fallbacks = fallback_models if fallback_models is not None else settings.openrouter_fallback_models
    # OpenRouter accepts a `models` array for in-platform fallback routing.
    body: dict[str, Any] = {
        "model": primary,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if fallbacks:
        body["models"] = [primary, *fallbacks]
    if response_format_json:
        body["response_format"] = {"type": "json_object"}

    url = f"{settings.OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"
    try:
        with httpx.Client(timeout=settings.AI_REQUEST_TIMEOUT_S) as http:
            r = http.post(url, headers=_headers(), json=body)
    except httpx.HTTPError as e:
        raise AIClientError(f"transport error: {e}") from e

    if r.status_code >= 400:
        raise AIClientError(
            f"openrouter {r.status_code}: {r.text[:300]}"
        )

    try:
        data = r.json()
    except ValueError as e:
        raise AIClientError(f"non-json response: {r.text[:200]}") from e

    try:
        choice = data["choices"][0]["message"]
        content = choice.get("content") or ""
        used_model = data.get("model") or primary
    except (KeyError, IndexError, TypeError) as e:
        raise AIClientError(f"malformed response: {data}") from e

    return ChatResult(
        model=used_model,
        content=content,
        usage=data.get("usage"),
        raw=data,
    )


def chat_json(
    schema: type[T],
    *,
    system: str,
    user: str,
    model: str | None = None,
    fallback_models: list[str] | None = None,
    max_tokens: int = 800,
    temperature: float = 0.2,
) -> tuple[T, ChatResult]:
    """Call the model asking for strict JSON, validate against `schema`.

    Raises AIClientError if the model output cannot be parsed/validated.
    Callers should catch and fall back to a deterministic engine.
    """
    result = chat(
        system=system + "\n\nReply ONLY with a JSON object matching the schema. No prose.",
        user=user,
        model=model,
        fallback_models=fallback_models,
        max_tokens=max_tokens,
        temperature=temperature,
        response_format_json=True,
    )
    text = result.content.strip()
    # Some models still wrap JSON in code fences — strip defensively.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as e:
        raise AIClientError(f"model returned non-json: {text[:200]}") from e
    try:
        validated = schema.model_validate(payload)
    except ValidationError as e:
        raise AIClientError(f"schema validation failed: {e}") from e
    return validated, result
