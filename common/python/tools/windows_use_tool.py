#!/usr/bin/env python3
"""
Windows-Use Tool for Blinky.

Provides fast deterministic native Windows UIA desktop automation
(Notepad tab creation, typing, element interaction) and agentic multi-step
desktop loops using windows-use.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

from computer_use.windows_use_engine import (
    resolve_windows_use_request,
    handle_windows_use_request,
    execute_notepad_new_tab_and_type,
    run_windows_use_agent_task,
)

LOGGER = logging.getLogger("blinky.tools.windows_use_tool")


def handle_request(params: dict[str, Any]) -> dict[str, Any]:
    """Execute Windows-Use action and return a standardized Blinky tool result."""
    return handle_windows_use_request(params)


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No parameters provided"}))
        sys.exit(1)

    try:
        raw = sys.argv[1]
        params = json.loads(raw) if raw.startswith("{") else {"raw_query": raw}
        res = handle_request(params)
        print(json.dumps(res, ensure_ascii=True))
    except Exception as exc:
        LOGGER.exception("Windows-Use tool execution failed")
        print(json.dumps({"error": str(exc), "success": False}))
        sys.exit(1)


if __name__ == "__main__":
    main()
