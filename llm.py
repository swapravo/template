"""
llm.py — OpenRouter API client. All LLM calls and prompt templates live here.
Model is controlled exclusively via settings.LLM_MODEL — never hardcoded.
Only this file calls the OpenRouter API.
"""
from __future__ import annotations

import json
from typing import Any, Literal

import httpx
import tiktoken

from config import settings

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# cl100k_base is a safe approximation for GPT-4 and most modern models
_ENCODER = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    """Estimate the token count of a string using cl100k_base encoding."""
    return len(_ENCODER.encode(text))


def _build_messages(prompt: str, files: list[dict] | None) -> list[dict]:
    """
    Build the OpenAI-style messages array.
    Files are attached as base64-encoded data URIs.
    """
    content: list[dict] = [{"type": "text", "text": prompt}]

    if files:
        for f in files:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{f['mime_type']};base64,{f['content_base64']}"
                },
            })

    return [{"role": "user", "content": content}]


def _validate_output(raw: str, output_type: Literal["string", "integer", "json"]) -> Any:
    """
    Coerce the LLM raw text output to the requested type.
    Raises ValueError if the output cannot be coerced.
    """
    raw = raw.strip()

    if output_type == "string":
        return raw

    if output_type == "integer":
        try:
            return int(raw)
        except ValueError:
            raise ValueError(
                f"LLM returned output that cannot be parsed as integer: {raw!r}"
            )

    if output_type == "json":
        # Strip markdown code fences if the model wrapped its output
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1])
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"LLM returned output that is not valid JSON: {raw!r}"
            ) from exc

    raise ValueError(f"Unknown output_type: {output_type!r}")


async def complete(
    prompt: str,
    files: list[dict] | None = None,
    output_type: Literal["string", "integer", "json"] = "string",
) -> dict:
    """
    Send a prompt (and optional file attachments) to OpenRouter.

    Args:
        prompt:      The user prompt string.
        files:       Optional list of dicts with keys:
                         filename       (str)
                         mime_type      (str)
                         content_base64 (str)
        output_type: Expected return type — "string", "integer", or "json".
                     The response is validated and coerced to this type.

    Returns:
        dict with keys: output, output_type, model, input_tokens, output_tokens

    Raises:
        ValueError: if input exceeds LLM_MAX_INPUT_TOKENS or output type mismatches.
        httpx.HTTPStatusError: on API errors.
    """
    # Pre-flight token guard
    input_tokens = _count_tokens(prompt)
    if input_tokens > settings.LLM_MAX_INPUT_TOKENS:
        raise ValueError(
            f"Input prompt is {input_tokens} tokens, which exceeds the configured "
            f"maximum of {settings.LLM_MAX_INPUT_TOKENS} tokens."
        )

    messages = _build_messages(prompt, files)

    system_msg: str | None = None
    if output_type == "integer":
        system_msg = "Respond with only an integer number. No explanation or extra text."
    elif output_type == "json":
        system_msg = (
            "Respond with only valid JSON. "
            "No markdown code fences, no explanation, no extra text."
        )

    if system_msg:
        messages = [{"role": "system", "content": system_msg}] + messages

    payload: dict = {
        "model": settings.LLM_MODEL,
        "messages": messages,
        "max_tokens": settings.LLM_MAX_OUTPUT_TOKENS,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            OPENROUTER_BASE_URL,
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://github.com/template",
                "X-Title": "Template App",
            },
            json=payload,
        )
        response.raise_for_status()

    data = response.json()
    raw_output = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})

    validated = _validate_output(raw_output, output_type)

    return {
        "output": validated,
        "output_type": output_type,
        "model": settings.LLM_MODEL,
        "input_tokens": usage.get("prompt_tokens", input_tokens),
        "output_tokens": usage.get("completion_tokens", 0),
    }
