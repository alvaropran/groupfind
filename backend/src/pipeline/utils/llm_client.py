"""Unified LLM client supporting Ollama (local) and Groq (cloud).

Both providers serve Llama 3.1 — same model, same prompts.
Toggle via GROUPFIND_LLM_PROVIDER env var ("ollama" or "groq").
"""

import json
import logging
from dataclasses import dataclass

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 120.0  # LLM calls can be slow, especially local Ollama


@dataclass(frozen=True)
class LLMResponse:
    content: str
    model: str
    provider: str


class LLMError(Exception):
    pass


async def _call_ollama(prompt: str, system: str = "") -> LLMResponse:
    """Call Ollama's local API."""
    url = f"{settings.ollama_base_url}/api/chat"
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1},
    }

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise LLMError(f"Ollama request failed: {e}") from e

        data = response.json()
        content = data.get("message", {}).get("content", "")
        return LLMResponse(
            content=content,
            model=settings.ollama_model,
            provider="ollama",
        )


async def _call_groq(prompt: str, system: str = "") -> LLMResponse:
    """Call Groq's cloud API (OpenAI-compatible)."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": settings.groq_model,
        "messages": messages,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "max_tokens": 4096,
    }

    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise LLMError(f"Groq request failed: {e}") from e

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return LLMResponse(
            content=content,
            model=settings.groq_model,
            provider="groq",
        )


async def call_llm(prompt: str, system: str = "") -> LLMResponse:
    """Call the configured LLM provider.

    Returns structured JSON content from the model.
    """
    provider = settings.llm_provider

    if provider == "ollama":
        return await _call_ollama(prompt, system)
    elif provider == "groq":
        if not settings.groq_api_key:
            raise LLMError("GROUPFIND_GROQ_API_KEY is not set")
        return await _call_groq(prompt, system)
    else:
        raise LLMError(f"Unknown LLM provider: {provider}")


def parse_llm_json(response: LLMResponse) -> dict | list:
    """Parse JSON from an LLM response, handling common issues."""
    content = response.content.strip()

    # Sometimes models wrap JSON in markdown code blocks
    if content.startswith("```"):
        lines = content.split("\n")
        # Remove first and last lines (```json and ```)
        content = "\n".join(lines[1:-1])

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise LLMError(f"Failed to parse LLM JSON response: {e}\nContent: {content[:500]}") from e
