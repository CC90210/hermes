"""
adapters/cloud_parser.py
------------------------
Cloud LLM fallback for PO parsing.

The default parser uses local Ollama (`qwen2.5:32b`). This module exists so
Hermes does not become unusable when:

  - Ollama isn't running (process died, machine rebooted, model wasn't pulled)
  - The local box doesn't have the RAM for the 32B model
  - The trial is running on a laptop where Ollama is impractical

The cloud providers we route to (Anthropic, OpenAI) operate under the
no-storage / no-training Data Processing Agreements covered in
`docs/SECURITY.md`. The same DPA framing the meeting agreed on applies here.

Routing:

  HERMES_PO_PARSER=ollama-local    → Ollama only, no fallback
  HERMES_PO_PARSER=cloud-anthropic → Anthropic Claude only
  HERMES_PO_PARSER=cloud-openai    → OpenAI GPT only
  HERMES_PO_PARSER=auto            → try Ollama; on failure, try Anthropic; then OpenAI

Required environment for cloud paths:

  ANTHROPIC_API_KEY  for cloud-anthropic
  OPENAI_API_KEY     for cloud-openai

If `auto` is selected and no cloud key is set, behaviour degrades to
Ollama-only — same as before this module existed.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


_ROUTER_ENV = "HERMES_PO_PARSER"
_VALID_ROUTES = ("auto", "ollama-local", "cloud-anthropic", "cloud-openai")


def _route() -> str:
    val = (os.environ.get(_ROUTER_ENV) or "ollama-local").strip().lower()
    if val not in _VALID_ROUTES:
        logger.warning("Invalid %s=%r, falling back to 'ollama-local'", _ROUTER_ENV, val)
        return "ollama-local"
    return val


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------

async def _call_anthropic(prompt: str, text: str) -> dict[str, Any]:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set; cannot use cloud-anthropic")
    model = os.environ.get("HERMES_ANTHROPIC_MODEL", "claude-sonnet-4-6")
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    full_prompt = prompt.replace("{text}", text[:30000])
    payload = {
        "model": model,
        "max_tokens": 4096,
        "temperature": 0.0,
        "system": (
            "You return ONLY a single JSON object. No prose. No markdown. "
            "No code fences. Begin your response with '{'."
        ),
        "messages": [{"role": "user", "content": full_prompt}],
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
    body = resp.json()
    parts = body.get("content") or []
    raw = "".join(p.get("text", "") for p in parts if p.get("type") == "text").strip()
    return _parse_json_strict(raw, source="anthropic")


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------

async def _call_openai(prompt: str, text: str) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set; cannot use cloud-openai")
    model = os.environ.get("HERMES_OPENAI_MODEL", "gpt-4.1-mini")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    full_prompt = prompt.replace("{text}", text[:30000])
    payload = {
        "model": model,
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system",
             "content": "You return ONLY a single JSON object. No prose."},
            {"role": "user", "content": full_prompt},
        ],
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
    body = resp.json()
    raw = body["choices"][0]["message"]["content"].strip()
    return _parse_json_strict(raw, source="openai")


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------

def _parse_json_strict(raw: str, source: str) -> dict[str, Any]:
    # Strip stray code fences in case the model ignored instructions.
    if raw.startswith("```"):
        first_nl = raw.find("\n")
        last_fence = raw.rfind("```")
        if first_nl != -1 and last_fence > first_nl:
            raw = raw[first_nl + 1:last_fence].strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"{source} returned invalid JSON (first 200 chars): {raw[:200]}"
        ) from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(
            f"{source} returned non-dict JSON: type={type(parsed).__name__}"
        )
    return parsed


# ---------------------------------------------------------------------------
# Public extraction with routing + fallback
# ---------------------------------------------------------------------------

async def extract_with_fallback(
    prompt: str,
    text: str,
    ollama_call,  # async callable: ollama_call(text) -> dict
) -> dict[str, Any]:
    """Run extraction via the configured route, falling back if needed.

    `ollama_call` is injected so this module does not import po_parser
    (avoids a circular import).
    """
    route = _route()
    last_err: Optional[Exception] = None

    if route == "ollama-local":
        return await ollama_call(text)

    if route == "cloud-anthropic":
        return await _call_anthropic(prompt, text)

    if route == "cloud-openai":
        return await _call_openai(prompt, text)

    # route == "auto" — try Ollama first; only attempt cloud backends if their
    # API keys are actually configured. If no cloud key is set and Ollama
    # fails, re-raise Ollama's specific error so callers see the real cause
    # (matches pre-fallback behaviour).
    cloud_backends: list[tuple[str, Any]] = []
    if os.environ.get("ANTHROPIC_API_KEY"):
        cloud_backends.append(("anthropic", lambda: _call_anthropic(prompt, text)))
    if os.environ.get("OPENAI_API_KEY"):
        cloud_backends.append(("openai", lambda: _call_openai(prompt, text)))

    try:
        return await ollama_call(text)
    except Exception as exc:
        if not cloud_backends:
            raise
        logger.warning("PO parser ollama failed: %s — trying cloud fallbacks", exc)
        last_err = exc

    for name, callable_ in cloud_backends:
        try:
            return await callable_()
        except Exception as exc:
            logger.warning("PO parser %s failed: %s", name, exc)
            last_err = exc
            continue

    raise RuntimeError(
        f"All PO parser backends failed. Last error: {last_err}"
    )
