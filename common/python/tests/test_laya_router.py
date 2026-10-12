"""
Tests for Laya Intent Router and Cua Integration in Blinky.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from ai.laya_router import classify_with_laya, get_preflight_from_laya
from computer_use.windows_use_engine import resolve_windows_use_request
from main import classify_request


class TestLayaRouter(unittest.TestCase):
    def test_microsoft_store_search_phrase_resolves_to_fast_windows_use_path(self):
        for query in (
            "open Microsoft Store and search for Minecraft",
            "search minecraft in Microsoft Store",
            "find Minecraft on the Microsoft Store",
        ):
            with self.subTest(query=query):
                params = resolve_windows_use_request(query)
                self.assertEqual(params["action"], "microsoft_store_search")
                self.assertEqual(params["app"], "store")
                self.assertEqual(params["query"].casefold(), "minecraft")

        classified = classify_request(
            "open Microsoft Store and search for Minecraft",
            previous_question=None,
            warnings=[],
        )
        self.assertEqual(classified["intent"], "WINDOWS_USE")
        self.assertEqual(classified["extracted_params"]["query"], "Minecraft")

    def test_microsoft_store_install_request_keeps_full_task_for_cua(self):
        query = "open microsoft store search for instagram and download it"

        self.assertIsNone(resolve_windows_use_request(query))

        classified = classify_with_laya(query)
        self.assertEqual(classified["intent"], "COMPUTER_USE")
        self.assertEqual(classified["source"], "structural_guard")
        self.assertEqual(classified["params"]["query"], query)

        preflight = get_preflight_from_laya(query)
        self.assertEqual(preflight["intent"], "COMPUTER_USE")
        self.assertTrue(preflight["needs_screen"])
        self.assertEqual(preflight["extracted_params"]["query"], query)

        main_result = classify_request(query, None, [])
        self.assertEqual(main_result["intent"], "COMPUTER_USE")
        self.assertEqual(main_result["extracted_params"]["query"], query)

        # Safety wording after the install verb must still keep the whole task
        # out of the search-only shortcut.
        guarded_query = query + ", but stop at the Install button without clicking it"
        self.assertIsNone(resolve_windows_use_request(guarded_query))
        guarded = classify_with_laya(guarded_query)
        self.assertEqual(guarded["intent"], "COMPUTER_USE")
        self.assertEqual(guarded["params"]["query"], guarded_query)

    def test_notepad_new_tab_phrase_resolves_without_llm(self):
        result = resolve_windows_use_request("open notepad and in new tab type hello world")
        self.assertEqual(result["action"], "notepad_new_tab_and_type")
        self.assertEqual(result["text"], "hello world")

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


    def test_windows_use_notepad_tab_and_type_routes_to_windows_use(self):
        """Notepad tab and type requests must route to WINDOWS_USE with needs_screen: False."""
        queries = [
            "open notepad in new tab and write hello world",
            "open notepad in a new tab and write hello world",
            "open Notepad in a new tab then type 'hello world'",
            "open notepad and in new tab type hello world",
            "open notepad and in a new tab write hello world",
            "open notepad then in a new tab type hello world",
            "open notepad and create new tab and type hello world",
            "open notepad and create a new tab and type hello world",
            "open notepad and then create a new tab and write hello world",
            "create a new tab in notepad and type hello world",
            "in notepad create new tab and type hello world",
            "open notepad and write hello world",
            "open notepad and write something",
            "open notepad and type hello world",
            "create new tab in notepad",
            "open notepad and create new tab",
        ]
        for q in queries:
            result = classify_with_laya(q)
            self.assertIsNotNone(result, f"classify_with_laya failed for: {q}")
            self.assertEqual(result["intent"], "WINDOWS_USE", f"Expected WINDOWS_USE for '{q}', got '{result['intent']}'")

            preflight = get_preflight_from_laya(q)
            self.assertIsNotNone(preflight, f"get_preflight_from_laya failed for: {q}")
            self.assertEqual(preflight["intent"], "WINDOWS_USE", f"Expected preflight WINDOWS_USE for '{q}'")
            self.assertFalse(preflight["needs_screen"], f"Expected needs_screen False for '{q}'")

            main_res = classify_request(q, None, [])
            self.assertIsNotNone(main_res, f"classify_request in main failed for: {q}")
            self.assertEqual(main_res["intent"], "WINDOWS_USE", f"Expected main classify_request WINDOWS_USE for '{q}'")
            self.assertFalse(main_res["needs_screen"], f"Expected needs_screen False in main for '{q}'")


if __name__ == "__main__":
    unittest.main()

