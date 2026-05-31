from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from ai.client import ask_model, get_provider_label
from ai.prompt import build_prompt
from capture.screen import capture_screen
from ocr.extract import extract_visible_text
from utils.logging import get_logger
from utils.matching import attach_matches
from utils.uia import get_visible_ui_text
from utils.window import get_active_window

LOGGER = get_logger("blinky.main")


def run(question: str) -> dict:
    started = time.perf_counter()
    warnings: list[str] = []

    # Lock the target window by PID *before* the long OCR pass starts.
    # Caching the pywinauto element itself would cause a stale COM descriptor
    # after ~15 s; caching the PID is stable and forces a fresh element
    # lookup when UIA runs.
    from utils.window import get_target_window_element
    _initial = get_target_window_element()
    target_pid: int | None = None
    try:
        target_pid = _initial.process_id() if _initial else None
    except Exception:
        pass

    screenshot = capture_screen()
    active_app = get_active_window(target_pid=target_pid)
    ocr_items = extract_visible_text(screenshot.path)
    uia_items = get_visible_ui_text(target_pid=target_pid)



    # UIA returns coordinates in screen-absolute space (physical pixel dimensions).
    # The screenshot is scaled down to fit within 1920×1080 (thumbnail).
    # The overlay then scales everything back up by (window.innerWidth / screenshot.width).
    # To make both scales cancel correctly, we must first convert UIA coords
    # from screen space → screenshot space before the overlay sees them.
    if screenshot.screen_width != screenshot.width or screenshot.screen_height != screenshot.height:
        sx = screenshot.width  / screenshot.screen_width
        sy = screenshot.height / screenshot.screen_height
        LOGGER.info(
            "Scaling UIA coords from screen (%dx%d) → screenshot (%dx%d)  sx=%.4f sy=%.4f",
            screenshot.screen_width, screenshot.screen_height,
            screenshot.width, screenshot.height, sx, sy,
        )
        scaled: list[dict] = []
        for item in uia_items:
            scaled.append({
                **item,
                "x":      int(item["x"]      * sx),
                "y":      int(item["y"]      * sy),
                "width":  max(1, int(item["width"]  * sx)),
                "height": max(1, int(item["height"] * sy)),
            })
        uia_items = scaled

    visible_items = merge_visible_items(ocr_items, uia_items)


    if not visible_items:
        warnings.append("No OCR text was detected. Try zooming in or opening a supported app.")

    prompt = build_prompt(
        question=question,
        active_app=active_app,
        ocr_items=visible_items,
    )
    ai_result = ask_model(prompt=prompt, screenshot_path=screenshot.path)

    steps = attach_matches(ai_result.get("steps", []), visible_items)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return {
        "summary": ai_result.get("summary", "I found a short path using the visible controls."),
        "steps": steps,
        "active_app": active_app,
        "ocr": {"count": len(visible_items), "items": visible_items},
        "screenshot": {
            "path": str(screenshot.path),
            "width": screenshot.width,
            "height": screenshot.height,
        },
        "elapsed_ms": elapsed_ms,
        "provider": get_provider_label(),
        "warnings": warnings + ai_result.get("warnings", []),
    }


def merge_visible_items(ocr_items: list[dict], uia_items: list[dict]) -> list[dict]:
    merged: list[dict] = []
    seen: set[tuple] = set()
    # Prioritize UIA items first so they are never sliced off by prompt truncation,
    # followed by OCR items as fallback.
    for item in [*uia_items, *ocr_items]:
        key = (
            str(item.get("text", "")).lower(),
            int(item.get("x", 0) / 8),
            int(item.get("y", 0) / 8),
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        question = str(payload.get("question", "")).strip()
        if not question:
            raise ValueError("Question is required.")

        result = run(question)
        print(json.dumps(result, ensure_ascii=True))
    except Exception as exc:
        LOGGER.exception("Worker failed")
        print(json.dumps({"error": str(exc), "steps": [], "warnings": [str(exc)]}))
        sys.exit(1)


if __name__ == "__main__":
    ROOT = Path(__file__).resolve().parent
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    main()
