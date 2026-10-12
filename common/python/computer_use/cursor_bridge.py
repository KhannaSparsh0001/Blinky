"""Forward CUA click targets to Blinky's own animated agent cursor."""

from __future__ import annotations

import contextvars
import json
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

CursorEventSink = Callable[[str, int | None, int | None, str], None]
_event_sink: contextvars.ContextVar[CursorEventSink | None] = contextvars.ContextVar(
    "blinky_agent_cursor_event_sink", default=None
)


def emit_cursor_protocol_event(
    action: str, x: int | None, y: int | None, label: str
) -> None:
    """Emit a status frame intercepted by the Tauri worker, not worker output."""
    out = sys.__stdout__ if hasattr(sys, "__stdout__") else sys.stdout
    data: dict[str, Any] = {"type": action}
    if x is not None and y is not None:
        data.update({"x": int(x), "y": int(y), "label": label})
    print(
        json.dumps(
            {
                "type": "status",
                "phase": "cursor_action",
                "message": "",
                "data": data,
            }
        ),
        flush=True,
        file=out,
    )


@contextmanager
def agent_cursor_events(sink: CursorEventSink) -> Iterator[None]:
    token = _event_sink.set(sink)
    try:
        yield
    finally:
        _event_sink.reset(token)


def click_with_agent_cursor(
    backend: Any,
    *,
    x: int,
    y: int,
    label: str,
    button: str = "left",
    click_count: int = 1,
) -> Any:
    """Animate Blinky's cursor to a target, then deliver the real CUA click."""
    return run_with_agent_cursor(
        lambda: backend.click(
            x=int(x), y=int(y), button=button, click_count=click_count
        ),
        x=x,
        y=y,
        label=label,
    )


def run_with_agent_cursor(
    action: Callable[[], Any], *, x: int, y: int, label: str
) -> Any:
    """Animate Blinky's cursor before a background UIA or mouse action."""
    sink = _event_sink.get()
    if sink is not None:
        sink("point", int(x), int(y), label)
        # Match the overlay's 220 ms glide before dispatching the action.
        time.sleep(0.24)
    try:
        return action()
    finally:
        if sink is not None:
            sink("done", None, None, label)


def move_with_agent_cursor(
    backend: Any, *, x: int, y: int, label: str = "target"
) -> Any:
    """Point with Blinky's overlay when a desktop-action bridge is active."""
    sink = _event_sink.get()
    if sink is not None:
        sink("point", int(x), int(y), label)
        return None
    return backend.move_agent_cursor(int(x), int(y))
