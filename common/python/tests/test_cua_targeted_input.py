from __future__ import annotations

from unittest.mock import patch

from computer_use.backends.cua_driver import CuaDriverBackend, _CuaTransport
from computer_use.backends.base import ActionResult, UIElement, WindowInfo
from computer_use.cursor_bridge import agent_cursor_events
from computer_use.actuator import _match_element, click_element


class _Transport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def call(self, tool: str, payload: dict | None = None) -> dict:
        args = payload or {}
        self.calls.append((tool, args))
        if tool == "list_windows":
            return {
                "windows": [
                    {
                        "title": "Microsoft Store",
                        "app_name": "WinStore.App.exe",
                        "pid": 501,
                        "window_id": 77,
                        "is_on_screen": True,
                        "bounds": {"x": 100, "y": 50, "width": 900, "height": 700},
                    }
                ]
            }
        return {}


def test_typing_and_enter_are_scoped_to_store_window() -> None:
    backend = CuaDriverBackend(binary="fake", session="blinky")
    transport = _Transport()
    backend._transport = transport
    backend._started = True

    typed = backend.type_text("minecraft", target_app="store")
    submitted = backend.key("enter", target_app="store")

    assert typed.ok and submitted.ok
    type_call = next(payload for tool, payload in transport.calls if tool == "type_text")
    enter_call = next(payload for tool, payload in transport.calls if tool == "press_key")
    for payload in (type_call, enter_call):
        assert payload["scope"] == "window"
        assert payload["pid"] == 501
        assert payload["window_id"] == 77


def test_targeted_typing_skips_hidden_duplicate_store_window() -> None:
    class DuplicateStoreTransport(_Transport):
        def call(self, tool: str, payload: dict | None = None) -> dict:
            if tool == "list_windows":
                args = payload or {}
                self.calls.append((tool, args))
                return {
                    "windows": [
                        {
                            "title": "Microsoft Store",
                            "app_name": "WinStore.App.exe",
                            "pid": 501,
                            "window_id": 77,
                            "is_on_screen": False,
                            "bounds": {"x": -31991, "y": -32000, "width": 219, "height": 39},
                        },
                        {
                            "title": "Microsoft Store",
                            "app_name": "WinStore.App.exe",
                            "pid": 502,
                            "window_id": 78,
                            "is_on_screen": True,
                            "bounds": {"x": 0, "y": 11, "width": 2560, "height": 1528},
                        },
                    ]
                }
            return super().call(tool, payload)

    backend = CuaDriverBackend(binary="fake", session="blinky")
    transport = DuplicateStoreTransport()
    backend._transport = transport
    backend._started = True

    result = backend.type_text("Minecraft", target_app="store")

    assert result.ok
    payload = next(payload for tool, payload in transport.calls if tool == "type_text")
    assert payload["pid"] == 502
    assert payload["window_id"] == 78


def test_targeted_input_refuses_when_only_hidden_window_exists() -> None:
    class HiddenStoreTransport(_Transport):
        def call(self, tool: str, payload: dict | None = None) -> dict:
            if tool == "list_windows":
                self.calls.append((tool, payload or {}))
                return {
                    "windows": [
                        {
                            "title": "Microsoft Store",
                            "app_name": "WinStore.App.exe",
                            "pid": 501,
                            "window_id": 77,
                            "is_on_screen": False,
                            "bounds": {"x": -31991, "y": -32000, "width": 219, "height": 39},
                        }
                    ]
                }
            return super().call(tool, payload)

    backend = CuaDriverBackend(binary="fake", session="blinky")
    transport = HiddenStoreTransport()
    backend._transport = transport
    backend._started = True

    result = backend.type_text("Minecraft", target_app="store")

    assert not result.ok
    assert "No visible window" in result.message
    assert not any(tool == "type_text" for tool, _ in transport.calls)


def test_set_value_uses_snapshot_token_and_target_pid() -> None:
    backend = CuaDriverBackend(binary="fake", session="blinky")
    transport = _Transport()
    backend._transport = transport
    backend._started = True

    result = backend.set_value(element_token="s1:4", pid=501, value="minecraft")

    assert result.ok
    tool, payload = transport.calls[-1]
    assert tool == "set_value"
    assert payload == {"element_token": "s1:4", "pid": 501, "value": "minecraft"}


def test_click_search_uses_snapshot_token_without_pointer_pixels() -> None:
    backend = CuaDriverBackend(binary="fake", session="blinky")
    transport = _Transport()
    backend._transport = transport
    backend._started = True

    result = backend.click_element(
        element_token="s1:4", window_id="77", pid=501
    )

    assert result.ok
    tool, payload = transport.calls[-1]
    assert tool == "click"
    assert payload["element_token"] == "s1:4"
    assert payload["scope"] == "window"
    assert payload["pid"] == 501
    assert payload["window_id"] == 77
    assert "x" not in payload and "y" not in payload


def test_backend_start_hides_cua_cursor_in_shared_session() -> None:
    backend = CuaDriverBackend(binary="fake", session="blinky")
    calls: list[tuple[str, dict]] = []

    def call(tool: str, payload: dict | None = None) -> dict:
        calls.append((tool, payload or {}))
        return {}

    with patch.object(backend, "_call", side_effect=call):
        backend.start()

    assert calls == [
        ("start_session", {"session": "blinky"}),
        ("set_agent_cursor_enabled", {"enabled": False}),
    ]


def test_revived_session_hides_cua_cursor_again() -> None:
    transport = _CuaTransport("fake", session="blinky")
    calls: list[tuple[str, dict]] = []

    def call(tool: str, payload: dict | None = None, *, _retry: bool = True) -> dict:
        calls.append((tool, payload or {}))
        return {}

    with patch.object(transport, "call", side_effect=call):
        assert transport._revive()

    assert calls == [
        ("start_session", {"session": "blinky"}),
        ("set_agent_cursor_enabled", {"enabled": False}),
    ]


def test_search_field_uses_snapshot_element_click() -> None:
    events: list[tuple] = []

    class Backend:
        def list_windows(self) -> list[WindowInfo]:
            return [
                WindowInfo(
                    title="Microsoft Store",
                    process="WinStore.App.exe",
                    pid=501,
                    window_id="77",
                    x=100,
                    y=50,
                    width=900,
                    height=700,
                )
            ]

        def get_window_elements(self, window_id: str, pid: int | None = None) -> list[UIElement]:
            return [
                UIElement(
                    text="Search",
                    x=800,
                    y=80,
                    width=180,
                    height=40,
                    role="Edit",
                    extra={
                        "element_index": 4,
                        "element_token": "s1:4",
                        "snapshot_id": "s1",
                        "window_id": "77",
                        "pid": 501,
                    },
                )
            ]

        def click_element(self, **kwargs) -> ActionResult:
            events.append(("uia-click", kwargs))
            return ActionResult(True, "click_element", "activated", {})

        def click(self, **kwargs) -> ActionResult:
            events.append(("pixel-click", kwargs))
            return ActionResult(True, "click", "clicked", {})

    with patch("computer_use.actuator._cua_backend", return_value=Backend()):
        with agent_cursor_events(lambda *event: events.append(event)):
            result = click_element(name="Search", app_id="store")

    assert result["ok"] is True
    assert events[0] == ("point", 890, 100, "Search")
    assert events[1] == (
        "uia-click",
        {
            "element_index": 4,
            "element_token": "s1:4",
            "window_id": "77",
            "pid": 501,
            "snapshot_id": "s1",
        },
    )
    assert events[-1][0] == "done"


def test_search_match_prefers_edit_field_over_titlebar_and_toolbar_controls() -> None:
    elements = [
        UIElement(
            text="Minimize",
            x=2380,
            y=0,
            width=50,
            height=40,
            role="Button",
            automation_id="Minimize",
        ),
        UIElement(
            text="Search",
            x=1100,
            y=0,
            width=50,
            height=40,
            role="Button",
            automation_id="SearchButton",
        ),
        UIElement(
            text="Search apps, games, and more",
            x=820,
            y=12,
            width=850,
            height=48,
            role="Edit",
            automation_id="SearchTextBox",
        ),
    ]

    match = _match_element("Search", elements)

    assert match is elements[2]


def test_search_match_refuses_unrelated_fuzzy_uia_items() -> None:
    elements = [
        UIElement(
            text="Minimize",
            x=2380,
            y=0,
            width=50,
            height=40,
            role="Button",
            automation_id="Minimize",
        ),
        UIElement(
            text="Settings",
            x=2200,
            y=0,
            width=50,
            height=40,
            role="Button",
            automation_id="Settings",
        ),
    ]

    assert _match_element("Search", elements) is None


def test_store_search_click_never_falls_through_to_windows_search_window() -> None:
    events: list[tuple] = []

    class Backend:
        def list_windows(self) -> list[WindowInfo]:
            return [
                WindowInfo(
                    title="Microsoft Store",
                    process="WinStore.App.exe",
                    pid=501,
                    window_id="77",
                    supported=True,
                    x=0,
                    y=11,
                    width=2560,
                    height=1528,
                ),
                WindowInfo(
                    title="Search",
                    process="SearchHost.exe",
                    pid=900,
                    window_id="99",
                    supported=True,
                    x=0,
                    y=0,
                    width=2560,
                    height=1600,
                ),
            ]

        def get_window_elements(self, window_id: str, pid: int | None = None) -> list[UIElement]:
            return []

        def click(self, **kwargs) -> ActionResult:
            events.append(("pixel-click", kwargs))
            return ActionResult(True, "click", "clicked", {})

    with patch("computer_use.actuator._cua_backend", return_value=Backend()):
        with agent_cursor_events(lambda *event: events.append(event)):
            result = click_element(name="Search", app_id="store")

    assert result["ok"] is False
    assert events == []
