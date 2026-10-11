#!/usr/bin/env python3
"""
Browser-Use Autonomous Web Agent Tool for Blinky.

Enables Blinky to autonomously navigate the web, inspect interactive DOM elements,
click buttons, fill forms, extract data, and perform multi-step web automation
using the `browser-use` library and Microsoft Edge / Chromium.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any

LOGGER = logging.getLogger("blinky.tools.browser_use")

DEFAULT_MODEL = "gemini-flash-latest"
FALLBACK_MODEL = "gemini-3.1-flash-lite"


def get_browser_use_llm():
    """Resolve and instantiate primary and fallback LLMs for browser-use."""
    from browser_use import ChatGoogle, ChatOpenAI, ChatGroq

    # 1. Primary: Google Gemini
    gemini_key = (
        os.getenv("GEMINI_API_KEY", "").strip()
        or os.getenv("GOOGLE_API_KEY", "").strip()
    )
    if not gemini_key:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            gemini_key = (
                os.getenv("GEMINI_API_KEY", "").strip()
                or os.getenv("GOOGLE_API_KEY", "").strip()
            )
        except Exception:
            pass

    if gemini_key:
        primary = ChatGoogle(model=DEFAULT_MODEL, api_key=gemini_key)
        fallback = ChatGoogle(model=FALLBACK_MODEL, api_key=gemini_key)
        return primary, fallback

    # 2. Secondary: OpenAI
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openai_key:
        primary = ChatOpenAI(model="gpt-4o-mini", api_key=openai_key)
        return primary, None

    # 3. Tertiary: Groq
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if groq_key:
        primary = ChatGroq(model="llama-3.3-70b-versatile", api_key=groq_key)
        return primary, None

    raise RuntimeError("No LLM API key found for browser-use. Please set GEMINI_API_KEY, OPENAI_API_KEY, or GROQ_API_KEY.")


async def run_browser_task(
    task: str,
    max_steps: int = 15,
    headless: bool | None = None,
    channel: str | None = None,
) -> dict[str, Any]:
    """Execute an autonomous web browsing task using browser-use and Microsoft Edge."""
    from browser_use import Agent, Browser

    if headless is None:
        headless_val = os.getenv("BLINKY_BROWSER_HEADLESS", "false").strip().lower()
        headless = headless_val in {"1", "true", "yes", "on"}

    if channel is None:
        channel = os.getenv("BLINKY_BROWSER_CHANNEL", "msedge").strip() or "msedge"

    llm, fallback_llm = get_browser_use_llm()
    browser = Browser(channel=channel, headless=headless)

    LOGGER.info("Starting browser-use agent for task: '%s' (channel=%s, headless=%s)", task, channel, headless)
    agent_kwargs: dict[str, Any] = {
        "task": task,
        "llm": llm,
        "browser": browser,
        "use_vision": True,
        "use_judge": False,
    }
    if fallback_llm is not None:
        agent_kwargs["fallback_llm"] = fallback_llm

    agent = Agent(**agent_kwargs)

    history = await agent.run(max_steps=max_steps)
    final_res = history.final_result() or "Browser task completed."
    errors = history.errors()

    return {
        "success": True,
        "action": "browser_use",
        "task": task,
        "result": final_res,
        "steps": len(history.action_names()),
        "errors": [str(e) for e in errors] if errors else [],
    }


BROWSER_USE_PATTERNS = (
    r"\b(?:go\s+to|navigate\s+to|open\s+website|open\s+url)\s+(https?://[^\s]+|\S+\.(?:com|org|io|net|edu|gov|dev|ai))\s+(?:and|to|then)\s+(?:click|find|extract|scrape|search|fill|type|buy|order|check)\b",
    r"\b(?:automate|use\s+browser|agent\s+in\s+browser|browser\s+agent)\b",
    r"\b(?:click|press|fill|sign\s+in|log\s+in|submit)\b.+?\b(?:on|in|at|to)\s+(?:https?://|\w+\.(?:com|org|io|net|dev|ai))\b",
    r"\b(?:extract|scrape|pull)\s+(?:the\s+)?(?:data|table|prices|items|products|contributors|reviews|heading|text|info)\s+(?:from|on|at)\s+(https?://\S+|\S+\.(?:com|org|io|net|dev|ai))\b",
)


def resolve_browser_use_request(query: str) -> dict[str, Any] | None:
    """Parse query to detect if it requires autonomous browser-use agent execution."""
    if not query:
        return None

    q = query.strip()
    q_lower = q.lower()

    # Skip simple single-cell Excel typing or simple spreadsheet requests
    if q_lower.startswith(("write", "type", "put", "enter")) and "cell" in q_lower:
        return None

    for pattern in BROWSER_USE_PATTERNS:
        match = re.search(pattern, q, re.IGNORECASE)
        if match:
            return {
                "action": "browser_use",
                "task": q,
                "raw_prompt": q,
            }

    # Explicit browser automation triggers
    if any(k in q_lower for k in ("browser-use", "browser use", "autonomous browser", "web agent")):
        return {
            "action": "browser_use",
            "task": q,
            "raw_prompt": q,
        }

    return None
