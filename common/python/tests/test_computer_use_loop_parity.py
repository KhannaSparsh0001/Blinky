from __future__ import annotations

from unittest.mock import Mock, patch

import computer_use.loop as loop
from computer_use.tools import ToolResult


def test_tool_map_uses_platform_neutral_app_launcher() -> None:
    assert loop.TOOL_MAP["open_app"] is loop.open_app_tool


def test_loop_is_allowed_on_windows_without_linux_backend() -> None:
    open_app = Mock(
        return_value=ToolResult(
            True,
            "open_app",
            "Opened Calculator.",
            {"app_name": "Calculator"},
        )
    )
    responses = [
        {"tool": "open_app", "args": {"app_name": "Calculator"}},
        {"answer": "Calculator is open."},
    ]

    with (
        patch.object(loop.platform, "system", return_value="Windows"),
        patch.object(loop, "_get_recipe_registry", return_value=None),
        patch.object(loop, "_get_app_inventory", return_value=[]),
        patch.object(loop, "build_system_prompt", return_value="test prompt"),
        patch.object(loop, "_capture_screenshot", side_effect=ModuleNotFoundError("backend")),
        patch.dict(loop.TOOL_MAP, {"open_app": open_app}),
        patch("ai.client.has_vision_capability", return_value=False),
        patch("ai.client.ask_text_model", side_effect=responses),
    ):
        result = loop.run_computer_use_loop("Open Calculator", max_calls=2)

    assert result["success"] is True
    assert result["steps"][0]["tool"] == "open_app"
    open_app.assert_called_once_with(app_name="Calculator")


def test_capture_screenshot_absorbs_missing_linux_backend() -> None:
    with patch.object(loop, "_capture_screenshot", side_effect=ModuleNotFoundError("backend.capture")):
        assert loop.capture_screenshot() is None
