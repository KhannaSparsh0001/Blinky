from __future__ import annotations

import unittest

from utils.window import is_ignored_overlay_window
from main import filter_ignored_overlay_items


class WindowSelectionTests(unittest.TestCase):
    def test_ignores_snipping_recording_toolbar(self) -> None:
        self.assertTrue(is_ignored_overlay_window("snippingtool.exe", "Recording toolbar"))

    def test_ignores_wispr_flow_overlay(self) -> None:
        self.assertTrue(is_ignored_overlay_window("wispr flow.exe", "status"))
        self.assertTrue(is_ignored_overlay_window("WisprFlow.exe", ""))
        self.assertTrue(is_ignored_overlay_window("whisper flow.exe", "status"))
        self.assertTrue(is_ignored_overlay_window("flow.exe", "status"))
        self.assertTrue(is_ignored_overlay_window("flow.exe", "wispr"))

    def test_ignores_raycast_overlay(self) -> None:
        self.assertTrue(is_ignored_overlay_window("raycast.exe", "Raycast"))
        self.assertTrue(is_ignored_overlay_window("raycast", ""))
        self.assertTrue(is_ignored_overlay_window("some_wrapper.exe", "Raycast"))

    def test_does_not_ignore_normal_app_window(self) -> None:
        self.assertFalse(is_ignored_overlay_window("code.exe", "Jarvis - Visual Studio Code"))
        self.assertFalse(is_ignored_overlay_window("notepad.exe", "Untitled - Notepad"))
        self.assertFalse(is_ignored_overlay_window("chrome.exe", "Google - Google Chrome"))
        self.assertFalse(is_ignored_overlay_window("antigravity ide.exe", "Blinky - Antigravity IDE - laya_router.py - Modified"))
        self.assertFalse(is_ignored_overlay_window("antigravity ide.exe", "deepglobal - Antigravity IDE - .env.local"))
        self.assertFalse(is_ignored_overlay_window("code.exe", "Blinky - Visual Studio Code"))
        self.assertFalse(is_ignored_overlay_window("chrome.exe", "KingSahil/Blinky: AI companion - Google Chrome"))

    def test_filters_ocr_inside_ignored_overlay_rect(self) -> None:
        class Screenshot:
            width = 500
            height = 250
            screen_width = 1000
            screen_height = 500

        items = [
            {"text": "Stop recording", "x": 210, "y": 30, "width": 80, "height": 20},
            {"text": "Real app", "x": 10, "y": 160, "width": 80, "height": 20},
        ]

        from unittest.mock import patch
        with patch("main.get_ignored_overlay_rects", return_value=[{"x": 400, "y": 40, "width": 200, "height": 80}]):
            filtered = filter_ignored_overlay_items(items, Screenshot())

        self.assertEqual([item["text"] for item in filtered], ["Real app"])

    def test_discards_oversized_fullscreen_overlay_rect(self) -> None:
        class Screenshot:
            width = 500
            height = 250
            screen_width = 1000
            screen_height = 500

        items = [
            {"text": "Real app button", "x": 100, "y": 100, "width": 80, "height": 20},
            {"text": "Extensions tab", "x": 200, "y": 50, "width": 80, "height": 20},
        ]

        from unittest.mock import patch
        # Simulating NVIDIA or CUA overlay returning fullscreen rect (1000x500)
        with patch("main.get_ignored_overlay_rects", return_value=[{"x": 0, "y": 0, "width": 1000, "height": 500}]):
            filtered = filter_ignored_overlay_items(items, Screenshot())

        # All items must be preserved!
        self.assertEqual([item["text"] for item in filtered], ["Real app button", "Extensions tab"])


if __name__ == "__main__":
    unittest.main()
