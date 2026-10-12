from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from computer_use.tools import ToolResult
from computer_use.windows_use_engine import (
    _verify_store_search_with_ocr,
    execute_microsoft_store_search,
    handle_windows_use_request,
)
import tools_win


def _success_verification():
    return {"verified": True, "observation": "Store search results are visible", "confidence": 0.8, "verification_method": "local_ocr"}


def test_store_search_uses_visible_gui_and_verifies_results() -> None:
    backend = MagicMock()
    with (
        patch("computer_use.tools.open_app_tool", return_value=ToolResult(True, "open_app", "Opened Store", {})),
        patch("computer_use.actuator._cua_backend", return_value=backend),
        patch("computer_use.windows_use_engine._focus_store_foreground", return_value=(None, None)),
        patch("computer_use.actuator.click_element", return_value={"ok": True}) as click,
        patch("computer_use.actuator.type_text", return_value={"ok": True}) as type_text,
        patch("computer_use.windows_use_engine._send_store_foreground_key", return_value={"ok": True}) as press_enter,
        patch("computer_use.windows_use_engine._capture_store_search_screenshot", return_value="store.png"),
        patch("computer_use.windows_use_engine._verify_store_search_with_ocr", return_value=_success_verification()),
        patch("computer_use.windows_use_engine.subprocess.Popen") as popen,
    ):
        result = handle_windows_use_request(
            {"action": "microsoft_store_search", "query": "Minecraft"}
        )

    assert result["success"] is True
    assert result["method"] == "gui_click_type_verify"
    click.assert_called_once_with(name="Search", app_id="store")
    type_text.assert_called_once_with("Minecraft", target_app="store")
    press_enter.assert_called_once_with(backend, "{ENTER}")
    popen.assert_not_called()


def test_store_search_clicks_search_bar_center_when_store_uia_has_no_search_field() -> None:
    backend = MagicMock()
    backend.list_windows.return_value = [
        SimpleNamespace(
            title="Store",
            process="WinStore.App.exe",
            supported=True,
            x=100,
            y=50,
            width=1280,
            height=800,
        ),
        # A stale hidden duplicate must never win over the visible Store window.
        SimpleNamespace(
            title="Store",
            process="WinStore.App.exe",
            supported=False,
            x=-32000,
            y=-32000,
            width=219,
            height=39,
        ),
    ]

    def click(*, name=None, x=None, y=None, app_id=None, **_kwargs):
        if name == "Search":
            return {"ok": False, "message": "No UIA search field"}
        assert (x, y, name, app_id) == (740, 68, "Microsoft Store search field", "store")
        return {"ok": True}

    with (
        patch("computer_use.tools.open_app_tool", return_value=ToolResult(True, "open_app", "Opened Store", {})),
        patch("computer_use.actuator._cua_backend", return_value=backend),
        patch("computer_use.windows_use_engine._focus_store_foreground", return_value=(None, None)),
        patch("computer_use.actuator.click_element", side_effect=click) as click_mock,
        patch("computer_use.actuator.type_text", return_value={"ok": True}) as type_text,
        patch("computer_use.windows_use_engine._send_store_foreground_key", return_value={"ok": True}),
        patch("computer_use.windows_use_engine._capture_store_search_screenshot", return_value="store.png"),
        patch("computer_use.windows_use_engine._verify_store_search_with_ocr", return_value=_success_verification()),
        patch("computer_use.windows_use_engine.time.monotonic", side_effect=[0.0, 0.0, 4.0]),
        patch("computer_use.windows_use_engine.time.sleep"),
    ):
        result = execute_microsoft_store_search("Minecraft")

    assert result["success"] is True
    assert result["method"] == "gui_click_type_verify"
    assert click_mock.call_args_list == [
        call(name="Search", app_id="store"),
        call(x=740, y=68, name="Microsoft Store search field", app_id="store"),
    ]
    type_text.assert_called_once_with("Minecraft", target_app="store")


def test_store_search_does_not_claim_success_when_visual_verification_fails() -> None:
    backend = MagicMock()
    with (
        patch("computer_use.tools.open_app_tool", return_value=ToolResult(True, "open_app", "Opened Store", {})),
        patch("computer_use.actuator._cua_backend", return_value=backend),
        patch("computer_use.windows_use_engine._focus_store_foreground", return_value=(None, None)),
        patch("computer_use.actuator.click_element", return_value={"ok": True}),
        patch("computer_use.actuator.type_text", return_value={"ok": True}),
        patch("computer_use.windows_use_engine._send_store_foreground_key", return_value={"ok": True}),
        patch("computer_use.windows_use_engine._capture_store_search_screenshot", return_value="store.png"),
        patch(
            "computer_use.windows_use_engine._verify_store_search_with_ocr",
            return_value={"verified": False, "observation": "OCR found no query", "confidence": 0.0},
        ),
    ):
        result = execute_microsoft_store_search("Minecraft")

    assert result["success"] is False
    assert "could not confirm the Store results" in result["message"]


def test_store_search_uses_local_ocr_as_the_success_gate() -> None:
    backend = MagicMock()
    with (
        patch("computer_use.tools.open_app_tool", return_value=ToolResult(True, "open_app", "Opened Store", {})),
        patch("computer_use.actuator._cua_backend", return_value=backend),
        patch("computer_use.windows_use_engine._focus_store_foreground", return_value=(None, None)),
        patch("computer_use.actuator.click_element", return_value={"ok": True}),
        patch("computer_use.actuator.type_text", return_value={"ok": True}),
        patch("computer_use.windows_use_engine._send_store_foreground_key", return_value={"ok": True}),
        patch("computer_use.windows_use_engine._capture_store_search_screenshot", return_value="store.png"),
        patch(
            "computer_use.windows_use_engine._verify_store_search_with_ocr",
            return_value={"verified": True, "observation": "query visible in results", "verification_method": "local_ocr"},
        ),
    ):
        result = execute_microsoft_store_search("Minecraft")

    assert result["success"] is True
    assert result["verification"]["verification_method"] == "local_ocr"


def test_store_search_retries_by_clicking_search_icon_if_enter_leaves_home_screen() -> None:
    backend = MagicMock()
    backend.list_windows.return_value = [
        SimpleNamespace(
            title="Store",
            process="WinStore.App.exe",
            supported=True,
            x=0,
            y=0,
            width=1280,
            height=800,
        )
    ]
    ocr_states = [
        {"verified": False, "observation": "Trending games; results not visible"},
        _success_verification(),
    ]

    def click(*, name=None, x=None, y=None, app_id=None, **_kwargs):
        if name == "Search":
            return {"ok": True}
        assert (x, y, name, app_id) == (940, 24, "Microsoft Store submit search button", "store")
        return {"ok": True}

    with (
        patch("computer_use.tools.open_app_tool", return_value=ToolResult(True, "open_app", "Opened Store", {})),
        patch("computer_use.actuator._cua_backend", return_value=backend),
        patch("computer_use.windows_use_engine._focus_store_foreground", return_value=(None, None)),
        patch("computer_use.actuator.click_element", side_effect=click) as click_mock,
        patch("computer_use.actuator.type_text", return_value={"ok": True}),
        patch("computer_use.windows_use_engine._send_store_foreground_key", return_value={"ok": True}),
        patch("computer_use.windows_use_engine._capture_store_search_screenshot", side_effect=["home.png", "results.png"]),
        patch("computer_use.windows_use_engine._verify_store_search_with_ocr", side_effect=ocr_states),
        patch("computer_use.windows_use_engine.time.sleep"),
    ):
        result = execute_microsoft_store_search("Minecraft")

    assert result["success"] is True
    assert click_mock.call_count == 2
    assert result["verification"]["verification_method"] == "local_ocr"


def test_store_home_recommendation_is_not_mistaken_for_search_results() -> None:
    items = [
        {"text": "minecraft"},
        {"text": "Trending games"},
        {"text": "Minecraft Launcher"},
    ]
    with patch("ocr.extract_visible_text", return_value=items):
        result = _verify_store_search_with_ocr("store-home.png", "Minecraft")

    assert result["verified"] is False
    assert "results heading: False" in result["observation"]


def test_store_results_require_a_results_heading_and_query_match() -> None:
    items = [
        {"text": "minecraft"},
        {"text": "Search results for Minecraft"},
        {"text": "Minecraft"},
    ]
    with patch("ocr.extract_visible_text", return_value=items):
        result = _verify_store_search_with_ocr("store-results.png", "Minecraft")

    assert result["verified"] is True
    assert result["verification_method"] == "local_ocr"


def test_store_search_uses_foreground_keyboard_when_background_typing_fails() -> None:
    backend = MagicMock()
    with (
        patch("computer_use.tools.open_app_tool", return_value=ToolResult(True, "open_app", "Opened Store", {})),
        patch("computer_use.actuator._cua_backend", return_value=backend),
        patch("computer_use.windows_use_engine._focus_store_foreground", return_value=(None, None)),
        patch("computer_use.actuator.click_element", return_value={"ok": True}),
        patch("computer_use.actuator.type_text", return_value={"ok": False, "message": "UWP background input failed"}),
        patch("computer_use.windows_use_engine._send_store_foreground_text", return_value={"ok": True}) as foreground_text,
        patch("computer_use.windows_use_engine._send_store_foreground_key", return_value={"ok": True}) as foreground_enter,
        patch("computer_use.windows_use_engine._capture_store_search_screenshot", return_value="store.png"),
        patch("computer_use.windows_use_engine._verify_store_search_with_ocr", return_value=_success_verification()),
    ):
        result = execute_microsoft_store_search("Minecraft")

    assert result["success"] is True
    foreground_text.assert_called_once_with(backend, "Minecraft")
    foreground_enter.assert_called_once_with(backend, "{ENTER}")


def test_store_search_fails_when_cursor_backend_is_unavailable() -> None:
    with (
        patch("computer_use.tools.open_app_tool", return_value=ToolResult(True, "open_app", "Opened Store", {})),
        patch("computer_use.actuator._cua_backend", return_value=None),
    ):
        result = execute_microsoft_store_search("Minecraft")

    assert result["success"] is False
    assert "cursor input backend is unavailable" in result["message"]


def test_store_search_refuses_to_click_when_store_cannot_be_foregrounded() -> None:
    backend = MagicMock()
    with (
        patch("computer_use.tools.open_app_tool", return_value=ToolResult(True, "open_app", "Opened Store", {})),
        patch("computer_use.actuator._cua_backend", return_value=backend),
        patch(
            "computer_use.windows_use_engine._focus_store_foreground",
            return_value=(None, "foreground is another app"),
        ),
        patch("computer_use.actuator.click_element") as click,
    ):
        result = execute_microsoft_store_search("Minecraft")

    assert result["success"] is False
    assert "could not bring its window to the foreground" in result["message"]
    click.assert_not_called()


def test_store_search_screenshot_is_captured_from_store_window() -> None:
    backend = MagicMock()
    store_window = SimpleNamespace(
        title="Store",
        process="WinStore.App.exe",
        supported=True,
        x=0,
        y=0,
        width=1280,
        height=800,
    )
    backend.list_windows.return_value = [store_window]
    backend._capture_window.return_value = SimpleNamespace(path="store-window.png")

    from computer_use.windows_use_engine import _capture_store_search_screenshot

    assert _capture_store_search_screenshot(backend) == "store-window.png"
    backend._capture_window.assert_called_once_with(store_window)


def test_store_launcher_uses_activation_api_and_requires_visible_window() -> None:
    with (
        patch.object(tools_win.os, "name", "nt"),
        patch("tools_win._activate_app_user_model_id", return_value=1234) as activate,
        patch("tools_win._wait_for_visible_store_window", return_value=True) as visible,
        patch("fast_app_launcher.launch_app_fast") as fast_launcher,
    ):
        result = tools_win.open_app_tool_impl("Microsoft Store")

    assert result.success is True
    assert result.details["method"] == "windows_app_activation_manager"
    activate.assert_called_once_with("Microsoft.WindowsStore_8wekyb3d8bbwe!App")
    visible.assert_called_once_with(timeout=8.0)
    fast_launcher.assert_not_called()


def test_store_launcher_restores_minimized_store_window_before_declaring_success() -> None:
    hidden = SimpleNamespace(
        title="Microsoft Store",
        process="ApplicationFrameHost.exe",
        supported=False,
        x=-31991,
        y=-32000,
        width=219,
        height=39,
        pid=123,
        window_id="456",
    )
    visible = SimpleNamespace(
        title="Microsoft Store",
        process="ApplicationFrameHost.exe",
        supported=True,
        x=0,
        y=0,
        width=1280,
        height=800,
        pid=123,
        window_id="456",
    )
    backend = MagicMock()
    backend.list_windows.side_effect = [[hidden], [visible]]
    with (
        patch("computer_use.actuator._cua_backend", return_value=backend),
        patch("tools_win._restore_store_window", return_value=True) as restore,
        patch("tools_win.time.sleep"),
    ):
        result = tools_win._wait_for_visible_store_window(timeout=0.1)

    assert result is True
    restore.assert_called_once_with(hidden)


def test_store_launcher_never_falls_back_to_windows_search() -> None:
    with (
        patch.object(tools_win.os, "name", "nt"),
        patch("tools_win._activate_app_user_model_id", side_effect=RuntimeError("activation failed")),
        patch("fast_app_launcher.launch_app_fast") as fast_launcher,
        patch("computer_use.tools.open_app_via_windows_search") as windows_search,
    ):
        result = tools_win.open_app_tool_impl("store")

    assert result.success is False
    fast_launcher.assert_not_called()
    windows_search.assert_not_called()


def test_store_launcher_does_not_claim_success_without_visible_window() -> None:
    with (
        patch.object(tools_win.os, "name", "nt"),
        patch("tools_win._activate_app_user_model_id", return_value=1234),
        patch("tools_win._wait_for_visible_store_window", return_value=False),
        patch("fast_app_launcher.launch_app_fast") as fast_launcher,
        patch("computer_use.tools.open_app_via_windows_search") as windows_search,
    ):
        result = tools_win.open_app_tool_impl("store")

    assert result.success is False
    assert result.details["launch_dispatched"] is True
    fast_launcher.assert_not_called()
    windows_search.assert_not_called()
