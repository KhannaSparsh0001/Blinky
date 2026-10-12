"""Regression tests for consistent raw and normalized CUA window caches."""

from __future__ import annotations

from computer_use.backends.cua_driver import CuaDriverBackend


class _Transport:
    def __init__(self) -> None:
        self.calls = 0

    def call(self, tool: str, payload: dict | None = None) -> dict:
        assert tool == "list_windows"
        self.calls += 1
        return {
            "windows": [
                {
                    "title": "Microsoft Store",
                    "app_name": "WinStore.App.exe",
                    "pid": 42,
                    "window_id": 77,
                    "is_on_screen": True,
                    "bounds": {"x": 20, "y": 30, "width": 900, "height": 700},
                }
            ]
        }


def test_cached_active_window_keeps_raw_mapping_shape() -> None:
    backend = CuaDriverBackend(binary="fake-cua-driver")
    transport = _Transport()
    backend._transport = transport
    backend._started = True

    first_raw = backend._list_windows_raw()
    active = backend.get_active_window()

    assert active is not None
    assert active.title == "Microsoft Store"
    assert active.process == "WinStore.App.exe"
    assert (active.x, active.y, active.width, active.height) == (20, 30, 900, 700)
    assert backend._list_windows_raw() == first_raw
    assert transport.calls == 1
