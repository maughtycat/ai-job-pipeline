"""OpenRouter LLM client with structured output and retry logic."""

import json
import os
import time
from typing import Any

from openai import OpenAI


def get_client() -> OpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY not set. "
            "Copy .env.example to .env and add your key."
        )
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )


def call_llm(
    prompt: str,
    system: str = "",
    model: str = "deepseek/deepseek-v4-flash",
    temperature: float = 0.3,
    max_retries: int = 3,
) -> str:
    """Call LLM with retry logic. Returns raw text response."""
    client = get_client()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt
            print(f"  Retry {attempt + 1}/{max_retries} after {wait}s: {e}")
            time.sleep(wait)
    return ""


def call_llm_json(
    prompt: str,
    system: str = "",
    model: str = "deepseek/deepseek-v4-flash",
    temperature: float = 0.3,
    max_retries: int = 3,
) -> dict[str, Any]:
    """Call LLM and parse response as JSON. Retries on parse failure."""
    for attempt in range(max_retries):
        raw = call_llm(prompt, system, model, temperature, max_retries=1)
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
            return json.loads(cleaned)
        except json.JSONDecodeError:
            if attempt == max_retries - 1:
                raise ValueError(f"LLM returned invalid JSON after {max_retries} attempts:\n{raw[:500]}")
    return {}
