#!/usr/bin/env python3
"""Tests for fast folder and File Explorer launcher."""

import os
from pathlib import Path
from unittest.mock import patch

from computer_use.folder_launcher import (
    is_folder_or_explorer_request,
    open_folder_or_path,
    resolve_folder_path,
)
from computer_use.agent import try_run_agent_action
from ai.laya_router import classify_with_laya


def test_is_folder_or_explorer_request() -> None:
    assert is_folder_or_explorer_request("open the blinky folder in projects folder in file explorer") is True
    assert is_folder_or_explorer_request("open projects folder") is True
    assert is_folder_or_explorer_request("open downloads folder") is True
    assert is_folder_or_explorer_request("open file explorer") is True
    assert is_folder_or_explorer_request("launch windows explorer") is True
    assert is_folder_or_explorer_request("open C:\\Projects\\Blinky") is True
    assert is_folder_or_explorer_request("what is the weather today") is False
    assert is_folder_or_explorer_request("play spotify") is False


def test_resolve_folder_path_blinky_in_projects() -> None:
    resolved = resolve_folder_path("open the blinky folder in projects folder in file explorer")
    assert resolved is not None
    assert "blinky" in str(resolved).lower()
    assert resolved.exists()


def test_resolve_folder_path_user_folders() -> None:
    downloads = resolve_folder_path("open downloads folder")
    assert downloads is not None
    assert "downloads" in str(downloads).lower()


def test_laya_router_routes_folder_request() -> None:
    routed = classify_with_laya("open the blinky folder in projects folder in file explorer")
    assert routed is not None
    assert routed["intent"] == "OPEN_FOLDER"
    assert routed["source"] == "structural_guard"


def test_try_run_agent_action_handles_folder_instantaneously() -> None:
    with patch("computer_use.folder_launcher.subprocess.Popen") as mock_popen, \
         patch("computer_use.folder_launcher.os.startfile", create=True) as mock_startfile:
        res = try_run_agent_action("open the blinky folder in projects folder in file explorer")
        assert res is not None
        assert res.success is True
        assert res.tool == "open_folder"
        assert "Blinky" in res.message or "blinky" in res.message.lower()
