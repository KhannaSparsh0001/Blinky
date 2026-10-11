from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ai.groq_client import ask_groq_text, ask_groq_vision
from ai.ollama_client import ask_ollama, ask_ollama_text
from ai.deepseek_client import ask_deepseek_text
from ai.mimo_client import ask_mimo_text, ask_mimo_vision
from ai.custom_client import ask_custom_text, ask_custom_vision


from utils.logging import get_logger

LOGGER = get_logger("blinky.ai.client")


def _resolve_provider() -> str:
    provider = os.getenv("BLINKY_AI_PROVIDER", "").strip().lower()
    if provider:
        return provider
    if os.getenv("GROQ_API_KEY"):
        return "groq"
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        return "gemini"
    if os.getenv("MIMO_API_KEY"):
        return "mimo"
    if os.getenv("DEEPSEEK_API_KEY"):
        return "deepseek"
    return "ollama"


def ask_model(prompt: str, screenshot_path: Path) -> dict[str, Any]:
    provider = _resolve_provider()
    primary_err: Exception | None = None
    if provider == "groq":
        try:
            return ask_groq_vision(prompt=prompt, screenshot_path=screenshot_path)
        except Exception as exc:
            primary_err = exc
            LOGGER.warning("Groq vision query failed (%s); trying fallback providers...", exc)

    # Fallback to Gemini Vision if Groq failed or Gemini is selected
    if (primary_err is not None or provider == "gemini") and (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        try:
            from ai.gemini_client import ask_gemini_vision
            return ask_gemini_vision(prompt=prompt, image_input=screenshot_path)
        except Exception as g_exc:
            LOGGER.warning("Gemini vision fallback failed: %s", g_exc)

    if provider == "mimo":
        return ask_mimo_vision(prompt=prompt, screenshot_path=screenshot_path)
    if provider == "deepseek":
        return ask_deepseek_text(prompt, max_tokens=1024)
    if provider == "custom":
        return ask_custom_vision(prompt, screenshot_path)
    if provider == "ollama":
        return ask_ollama(prompt)

    if primary_err:
        raise primary_err

    raise RuntimeError(
        "Unsupported BLINKY_AI_PROVIDER. Use 'ollama', 'groq', 'gemini', 'deepseek', 'mimo', or 'custom'."
    )


def ask_text_model(prompt: str, max_tokens: int = 300) -> dict[str, Any]:
    provider = _resolve_provider()
    primary_err: Exception | None = None

    if provider == "groq":
        try:
            return ask_groq_text(prompt, max_tokens)
        except Exception as exc:
            primary_err = exc
            LOGGER.warning("Groq text model hit an error or rate limit (%s); trying fallback providers...", exc)

    # Automatic fallback to Gemini if Groq failed or Gemini is selected
    if (primary_err is not None or provider == "gemini") and (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        try:
            from ai.gemini_client import ask_gemini_text
            from ai.groq_client import _parse_json
            res = ask_gemini_text(prompt, max_tokens)
            text = str(res.get("text", "")).strip()
            return _parse_json(text)
        except Exception as g_exc:
            LOGGER.warning("Gemini text fallback failed: %s", g_exc)

    if provider == "mimo":
        return ask_mimo_text(prompt, max_tokens)
    if provider == "deepseek" or (primary_err is not None and os.getenv("DEEPSEEK_API_KEY")):
        try:
            return ask_deepseek_text(prompt, max_tokens=max_tokens)
        except Exception as d_exc:
            LOGGER.warning("DeepSeek text fallback failed: %s", d_exc)

    if provider == "custom":
        return ask_custom_text(prompt, max_tokens=max_tokens)
    if provider == "ollama":
        return ask_ollama_text(prompt, max_tokens)

    if primary_err:
        raise primary_err

    raise RuntimeError(
        "Unsupported BLINKY_AI_PROVIDER. Use 'ollama', 'groq', 'gemini', 'deepseek', 'mimo', or 'custom'."
    )



def get_provider_label() -> str:
    provider = _resolve_provider()
    return provider.capitalize()


def has_vision_capability() -> bool:
    provider = (os.getenv("BLINKY_AI_PROVIDER", "").strip() or "").lower()
    if provider == "custom":
        from ai.custom_client import has_vision_capability as _custom_vision

        return _custom_vision()
    return provider in ("groq", "mimo", "gemini") or bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
