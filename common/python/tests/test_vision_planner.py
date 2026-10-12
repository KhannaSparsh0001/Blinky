"""Tests for vision-guided planning module."""

from __future__ import annotations

from PIL import Image
from unittest.mock import ANY, patch

from computer_use.vision_planner import _scale_action_coordinates, plan_action


def _tool_schema() -> dict:
    return {"open_app": {}, "screenshot": {}, "type_text": {}, "press_key": {}, "click_element": {}, "list_windows": {}, "get_app_state": {}, "mouse": {}}


@patch("ai.client.ask_model")
def test_plan_action_returns_structured_action(mock_ask) -> None:
    mock_ask.return_value = {"action": "screenshot", "args": {}, "reasoning": "Need to see the screen first"}
    result = plan_action(
        screenshot_path="/tmp/test.png",
        query="open calculator",
        history=[],
        tool_schema=_tool_schema(),
    )
    assert "error" not in result
    assert result["action"] == "screenshot"
    assert result["args"] == {}
    assert "reasoning" in result


@patch("ai.client.ask_model")
def test_plan_action_none_screenshot(mock_ask) -> None:
    result = plan_action(
        screenshot_path=None,
        query="open calculator",
        history=[],
        tool_schema=_tool_schema(),
    )
    assert "error" in result
    assert result["error"] == "Screenshot unavailable"
    mock_ask.assert_not_called()


@patch("ai.client.ask_model")
def test_plan_action_model_error(mock_ask) -> None:
    mock_ask.side_effect = RuntimeError("API timeout")
    result = plan_action(
        screenshot_path="/tmp/test.png",
        query="open calculator",
        history=[],
        tool_schema=_tool_schema(),
    )
    assert "error" in result
    assert "API timeout" in result["error"]


@patch("ai.client.ask_model")
def test_plan_action_no_action_field(mock_ask) -> None:
    mock_ask.return_value = {"args": {}, "reasoning": "something"}
    result = plan_action(
        screenshot_path="/tmp/test.png",
        query="open calculator",
        history=[],
        tool_schema=_tool_schema(),
    )
    assert "error" in result
    assert "No action" in result["error"]


@patch("ai.client.ask_model")
def test_plan_action_misparse_retries_then_raw_text(mock_ask) -> None:
    mock_ask.side_effect = [
        {"action": "invalid_tool", "args": {}, "reasoning": "bad"},
        {"action": "also_invalid", "args": {}, "reasoning": "still bad"},
        {"action": "still_wrong", "args": {}, "reasoning": "nope"},
        {"action": "still_wrong_again", "args": {}, "reasoning": "nope"},
    ]
    result = plan_action(
        screenshot_path="/tmp/test.png",
        query="open calculator",
        history=[],
        tool_schema=_tool_schema(),
    )
    assert "error" not in result
    assert result["action"] == "raw_text"
    assert "unparseable" in result["reasoning"]


@patch("ai.client.ask_model")
def test_plan_action_misparse_recovers(mock_ask) -> None:
    mock_ask.side_effect = [
        {"action": "invalid_tool", "args": {}, "reasoning": "bad"},
        {"action": "screenshot", "args": {}, "reasoning": "fixed"},
    ]
    result = plan_action(
        screenshot_path="/tmp/test.png",
        query="open calculator",
        history=[],
        tool_schema=_tool_schema(),
    )
    assert "error" not in result
    assert result["action"] == "screenshot"


@patch("ai.client.ask_model")
def test_plan_action_metrics_logged_on_success(mock_ask) -> None:
    mock_ask.return_value = {"action": "open_app", "args": {"app_name": "calc"}, "reasoning": "launch"}
    with patch("computer_use.vision_planner.metrics.log_vision_call") as mock_log:
        result = plan_action(
            screenshot_path="/tmp/test.png",
            query="open calc",
            history=[],
            tool_schema=_tool_schema(),
        )
        assert "error" not in result
        mock_log.assert_called_once_with(
            module="vision_planner",
            latency_ms=ANY,
            success=True,
            app_type="unknown",
            action_taken="open_app",
        )


@patch("ai.client.ask_model")
def test_plan_action_metrics_logged_on_error(mock_ask) -> None:
    mock_ask.side_effect = RuntimeError("fail")
    with patch("computer_use.vision_planner.metrics.log_vision_call") as mock_log:
        result = plan_action(
            screenshot_path="/tmp/test.png",
            query="open calc",
            history=[],
            tool_schema=_tool_schema(),
        )
        assert "error" in result
        mock_log.assert_called_once_with(
            module="vision_planner",
            latency_ms=ANY,
            success=False,
            app_type="unknown",
            model_error=ANY,
        )


@patch("ai.client.ask_model")
def test_plan_action_scales_groq_vision_coordinates_to_native_pixels(mock_ask, tmp_path, monkeypatch) -> None:
    screenshot = tmp_path / "screen.png"
    Image.new("RGB", (2560, 1600)).save(screenshot)
    monkeypatch.setenv("BLINKY_AI_PROVIDER", "groq")
    mock_ask.return_value = {
        "action": "mouse",
        "args": {"action": "click", "x": 384, "y": 240},
        "reasoning": "Click target",
    }

    result = plan_action(str(screenshot), "click target", [], _tool_schema())

    assert result["args"]["x"] == 1280
    assert result["args"]["y"] == 800
    assert "768x480" in mock_ask.call_args.args[0]
    assert "2560x1600" in mock_ask.call_args.args[0]


@patch("ai.client.ask_model")
def test_plan_action_keeps_custom_provider_native_coordinates(mock_ask, tmp_path, monkeypatch) -> None:
    screenshot = tmp_path / "screen.png"
    Image.new("RGB", (1280, 800)).save(screenshot)
    monkeypatch.setenv("BLINKY_AI_PROVIDER", "custom")
    mock_ask.return_value = {
        "action": "mouse",
        "args": {"action": "click", "x": 384, "y": 240},
        "reasoning": "Click target",
    }

    result = plan_action(str(screenshot), "click target", [], _tool_schema())

    assert result["args"]["x"] == 384
    assert result["args"]["y"] == 240
    assert "1280x800" in mock_ask.call_args.args[0]


def test_scale_action_coordinates_preserves_non_coordinate_actions() -> None:
    args = {"name": "Save"}
    assert _scale_action_coordinates(args, (2560, 1600), (768, 480)) is args
