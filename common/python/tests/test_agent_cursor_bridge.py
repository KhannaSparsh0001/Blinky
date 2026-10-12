from __future__ import annotations

from computer_use.cursor_bridge import (
    agent_cursor_events,
    click_with_agent_cursor,
    emit_cursor_protocol_event,
    move_with_agent_cursor,
)


class _Backend:
    def __init__(self, events: list[tuple]) -> None:
        self.events = events

    def click(self, *, x: int, y: int, button: str, click_count: int) -> dict:
        self.events.append(("native-click", x, y, button, click_count))
        return {"ok": True}


def test_click_uses_blinky_cursor_before_native_click_and_resets_after() -> None:
    events: list[tuple] = []
    backend = _Backend(events)

    with agent_cursor_events(lambda *event: events.append(event)):
        result = click_with_agent_cursor(
            backend, x=420, y=275, label="Store search", click_count=2
        )

    assert result == {"ok": True}
    assert events[0] == ("point", 420, 275, "Store search")
    assert events[1] == ("native-click", 420, 275, "left", 2)
    assert events[2] == ("done", None, None, "Store search")


def test_move_uses_blinky_cursor_without_moving_cua_driver_cursor() -> None:
    events: list[tuple] = []

    class Backend:
        def move_agent_cursor(self, x: int, y: int) -> None:
            events.append(("cua-cursor", x, y))

    with agent_cursor_events(lambda *event: events.append(event)):
        result = move_with_agent_cursor(Backend(), x=80, y=140, label="Search")

    assert result is None
    assert events == [("point", 80, 140, "Search")]


def test_cursor_event_uses_intercepted_status_frame(capfd) -> None:
    import json

    emit_cursor_protocol_event("point", 120, 240, "Search")
    captured = capfd.readouterr()

    assert json.loads(captured.out) == {
        "type": "status",
        "phase": "cursor_action",
        "message": "",
        "data": {"type": "point", "x": 120, "y": 240, "label": "Search"},
    }
