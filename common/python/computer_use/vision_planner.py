"""
Vision-guided planning module.
Called before the first action and after recovery to decide the next atomic step.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from utils.logging import get_logger

from . import config
from . import metrics

LOGGER = get_logger("blinky.computer_use.vision_planner")


def _image_dimensions_for_model(screenshot_path: str) -> tuple[tuple[int, int], tuple[int, int]] | None:
    """Return (native screenshot size, encoded image size) for the selected vision client."""
    try:
        from PIL import Image

        with Image.open(screenshot_path) as source:
            native_size = source.size
            from ai.client import _resolve_provider

            provider = _resolve_provider()
            max_dimension = None
            if provider == "groq":
                from ai.groq_client import _get_configured_image_max_dim

                max_dimension = _get_configured_image_max_dim()
            elif provider == "mimo":
                max_dimension = 1024

            if max_dimension and max(native_size) > max_dimension:
                image = source.copy()
                image.thumbnail((max_dimension, max_dimension))
                return native_size, image.size
            return native_size, native_size
    except Exception:
        LOGGER.debug("Could not determine vision image dimensions", exc_info=True)
        return None


def _scale_action_coordinates(args: dict[str, Any], native_size: tuple[int, int], image_size: tuple[int, int]) -> dict[str, Any]:
    """Convert coordinates in the encoded vision image to native desktop pixels."""
    if native_size == image_size or not isinstance(args, dict):
        return args
    if not all(isinstance(args.get(key), (int, float)) for key in ("x", "y")):
        return args
    scaled = dict(args)
    scaled["x"] = round(args["x"] * native_size[0] / image_size[0])
    scaled["y"] = round(args["y"] * native_size[1] / image_size[1])
    return scaled


def plan_action(
    screenshot_path: str | None,
    query: str,
    history: list[str],
    tool_schema: dict[str, Any],
    app_type: str = "unknown",
) -> dict[str, Any]:
    """
    Given a screenshot and user query, return the next action as a structured plan.

    Args:
        screenshot_path: Path to PNG screenshot file, or None if unavailable
        query: The user's task string
        history: Previous vision observations (most recent first, max MAX_HISTORY_OBSERVATIONS)
        tool_schema: Dict mapping tool names to their parameter specs
        app_type: Always "unknown" in this phase

    Returns:
        On success: {"action": "tool_name", "args": {...}, "reasoning": "..."}
        On failure: {"error": "..."}
    """
    from prompts import get_prompts
    from ai.client import ask_model

    if screenshot_path is None:
        LOGGER.warning("plan_action: screenshot_path is None")
        return {"error": "Screenshot unavailable"}

    # Build prompt
    prompts = get_prompts()
    dimensions = _image_dimensions_for_model(screenshot_path)
    if dimensions:
        native_size, image_size = dimensions
        image_width, image_height = image_size
        screen_width, screen_height = native_size
    else:
        image_width = image_height = screen_width = screen_height = "unknown"
    prompt = prompts.get("vision_planner_prompt", "").format(
        query=query,
        image_width=image_width,
        image_height=image_height,
        screen_width=screen_width,
        screen_height=screen_height,
    )

    start = time.perf_counter()
    try:
        result = ask_model(prompt, Path(screenshot_path))
        latency_ms = (time.perf_counter() - start) * 1000
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        LOGGER.exception("plan_action: vision model error")
        metrics.log_vision_call(
            module="vision_planner",
            latency_ms=latency_ms,
            success=False,
            app_type=app_type,
            model_error=str(exc),
        )
        return {"error": f"Vision model error: {exc}"}

    action = result.get("action", "")
    args = result.get("args", {})
    reasoning = result.get("reasoning", "")

    if not action:
        metrics.log_vision_call(
            module="vision_planner",
            latency_ms=latency_ms,
            success=False,
            app_type=app_type,
            model_error="No action field in response",
        )
        return {"error": "No action returned by vision model"}

    misparses = 0
    while action not in tool_schema and misparses < config.MAX_PLANNER_MISPARSE_RETRIES:
        misparses += 1
        LOGGER.warning("plan_action: misparse #%d: action='%s' not in schema", misparses, action)
        schema_clarification = (
            f"Your previous output had action='{action}' which is not a valid tool. "
            f"Valid tools: {list(tool_schema.keys())}. "
            f"Return a JSON object with 'action' (one of the valid tool names), 'args' (dict), and 'reasoning' (string)."
        )
        try:
            result = ask_model(schema_clarification, Path(screenshot_path))
            action = result.get("action", "")
            args = result.get("args", {})
            reasoning = result.get("reasoning", "")
        except Exception:
            break

    if action not in tool_schema:
        metrics.log_vision_call(
            module="vision_planner",
            latency_ms=latency_ms,
            success=True,
            app_type=app_type,
            action_taken=f"raw_text after {misparses} misparses",
        )
        return {
            "action": "raw_text",
            "args": {"suggestion": f"{action}: {json.dumps(args)}"},
            "reasoning": f"Model returned unparseable tool call after {misparses} retries",
        }

    if dimensions and action in {"mouse", "click_element"}:
        args = _scale_action_coordinates(args, native_size, image_size)

    metrics.log_vision_call(
        module="vision_planner",
        latency_ms=latency_ms,
        success=True,
        app_type=app_type,
        action_taken=action,
    )

    return {
        "action": action,
        "args": args,
        "reasoning": reasoning,
    }
