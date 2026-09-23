"""Minimal LLM provider abstraction: a common `complete(prompt) -> text`
interface over Groq (primary, free tier) and Gemini (fallback, free tier).

This is deliberately small and scoped to what Phase 5's extraction fallback
needs (a single completion call). Phase 7 builds the fuller
narrative-generation provider layer with retry/failover logging for the
case-summary step; both can share these adapters.
"""

from __future__ import annotations

from typing import Protocol

import httpx

from backend.app.core.config import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
REQUEST_TIMEOUT_SECONDS = 30


class LLMProvider(Protocol):
    name: str

    def complete(self, prompt: str) -> str: ...

    def complete_with_usage(self, prompt: str) -> tuple[str, int]: ...


class GroqProvider:
    name = "groq"

    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model

    def _call(self, prompt: str) -> dict:
        response = httpx.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()

    def complete(self, prompt: str) -> str:
        return self._call(prompt)["choices"][0]["message"]["content"]

    def complete_with_usage(self, prompt: str) -> tuple[str, int]:
        data = self._call(prompt)
        text = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        return text, tokens


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model

    def _call(self, prompt: str) -> dict:
        response = httpx.post(
            GEMINI_URL_TEMPLATE.format(model=self._model),
            params={"key": self._api_key},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()

    def complete(self, prompt: str) -> str:
        return self._call(prompt)["candidates"][0]["content"]["parts"][0]["text"]

    def complete_with_usage(self, prompt: str) -> tuple[str, int]:
        data = self._call(prompt)
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        tokens = data.get("usageMetadata", {}).get("totalTokenCount", 0)
        return text, tokens


def get_configured_providers() -> list[LLMProvider]:
    """Providers in priority order (Groq first), limited to whichever have
    an API key configured. Empty if neither is configured."""
    providers: list[LLMProvider] = []
    if settings.groq_api_key:
        providers.append(GroqProvider(settings.groq_api_key, settings.groq_model))
    if settings.gemini_api_key:
        providers.append(GeminiProvider(settings.gemini_api_key, settings.gemini_model))
    return providers


def complete_with_failover(prompt: str) -> tuple[str, str] | None:
    """Try each configured provider in order; return (text, provider_name)
    from the first that succeeds, or None if none are configured or all
    fail."""
    for provider in get_configured_providers():
        try:
            return provider.complete(prompt), provider.name
        except (httpx.HTTPError, KeyError, IndexError):
            continue
    return None


def complete_with_usage_and_failover(prompt: str) -> tuple[str, str, int] | None:
    """Same failover behavior as `complete_with_failover`, but also returns
    the provider's reported total token count for per-case accounting."""
    for provider in get_configured_providers():
        try:
            text, tokens = provider.complete_with_usage(prompt)
            return text, provider.name, tokens
        except (httpx.HTTPError, KeyError, IndexError):
            continue
    return None
