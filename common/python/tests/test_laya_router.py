"""
Tests for Laya Intent Router and Cua Integration in Blinky.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from ai.laya_router import classify_with_laya, get_preflight_from_laya
from main import classify_request


class TestLayaRouter(unittest.TestCase):
    def test_url_with_video_never_routes_to_video_edit(self):
        """Web URLs mentioning 'video' or 'instagram' must route to BROWSER_USE, NEVER VIDEO_EDIT."""
        queries = [
            "go to https://instagram.com/blinky_ai and tell me the first comment of latest video",
            "https://youtube.com/watch?v=123 cut out the intro",
            "visit https://tiktok.com/@creator/video/456",
            "go to www.reddit.com and check video posts",
            "https://github.com/KingSahil/blinky check latest release",
        ]
        for q in queries:
            result = classify_with_laya(q)
            self.assertIsNotNone(result, f"Failed for query: {q}")
            self.assertEqual(result["intent"], "BROWSER_USE", f"Expected BROWSER_USE for query: {q}, got: {result['intent']}")
            self.assertNotEqual(result["intent"], "VIDEO_EDIT")

    def test_local_video_editing_routes_to_video_edit(self):
        """Local media files with editing verbs must route to VIDEO_EDIT."""
        queries = [
            "trim intro.mp4 from 00:05 to 00:15",
            "cut video.mkv from 10s to 20s",
            "burn subtitles into lecture.mov with instagram style",
            "remove silence from podcast.mp3",
        ]
        for q in queries:
            result = classify_with_laya(q)
            self.assertIsNotNone(result, f"Failed for query: {q}")
            self.assertEqual(result["intent"], "VIDEO_EDIT", f"Expected VIDEO_EDIT for query: {q}")

    def test_spreadsheet_cell_queries_route_to_spreadsheet(self):
        """Excel cell operations must route to SPREADSHEET."""
        queries = [
            "type 42 in cell A1",
            "write Hello World in cell B5",
            "in C10 put 100",
        ]
        for q in queries:
            result = classify_with_laya(q)
            self.assertIsNotNone(result, f"Failed for query: {q}")
            self.assertEqual(result["intent"], "SPREADSHEET", f"Expected SPREADSHEET for query: {q}")

    def test_whatsapp_queries_route_to_whatsapp(self):
        """WhatsApp message requests must route to WHATSAPP."""
        queries = [
            "send hello mom on whatsapp",
            "message john on whatsapp",
        ]
        for q in queries:
            result = classify_with_laya(q)
            self.assertIsNotNone(result, f"Failed for query: {q}")
            self.assertEqual(result["intent"], "WHATSAPP", f"Expected WHATSAPP for query: {q}")

    def test_general_qa_routes_to_chat(self):
        """Informational questions without system action must route to CHAT."""
        result = classify_with_laya("what is the capital of France")
        self.assertIsNotNone(result)
        self.assertEqual(result["intent"], "CHAT")

    def test_get_preflight_from_laya_structure(self):
        """Ensure get_preflight_from_laya produces valid Blinky preflight structures."""
        # Browser-Use
        bu = get_preflight_from_laya("go to https://github.com/KingSahil/blinky")
        self.assertIsNotNone(bu)
        self.assertEqual(bu["intent"], "BROWSER_USE")
        self.assertFalse(bu["needs_screen"])

        # Spreadsheet
        sheet = get_preflight_from_laya("type 99 in cell D4")
        self.assertIsNotNone(sheet)
        self.assertEqual(sheet["intent"], "SPREADSHEET")
        self.assertFalse(sheet["needs_screen"])

        # Chat
        chat = get_preflight_from_laya("tell me a fun fact about dolphins")
        self.assertIsNotNone(chat)
        self.assertEqual(chat["intent"], "INFORMATIONAL_CHAT")
        self.assertFalse(chat["needs_screen"])

    def test_classify_request_in_main_uses_laya(self):
        """Ensure classify_request in main.py routes through Laya successfully."""
        # Query that formerly failed into AiCut
        res = classify_request(
            "go to https://instagram.com/blinky_ai and tell me the first comment of latest video",
            None,
            [],
        )
        self.assertIsNotNone(res)
        self.assertEqual(res["intent"], "BROWSER_USE")
        self.assertFalse(res["needs_screen"])


if __name__ == "__main__":
    unittest.main()
