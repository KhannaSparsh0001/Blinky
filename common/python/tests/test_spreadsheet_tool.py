import unittest
from unittest.mock import patch, MagicMock
import pytest

from tools.spreadsheet_tool import (
    resolve_spreadsheet_request,
    generate_table_tsv,
    handle_request,
    cell_to_row_col,
    focus_spreadsheet_window,
)
from main import classify_request, run_spreadsheet_tool


class TestSpreadsheetTool(unittest.TestCase):
    def test_resolve_spreadsheet_request_phrasings(self):
        cases = [
            (
                "create a spreadsheet with columns Name, Email, Phone",
                {"action": "create", "columns": ["Name", "Email", "Phone"], "has_match": True},
            ),
            (
                "make a spreadsheet for monthly budget",
                {"action": "create", "topic": "monthly budget", "has_match": True},
            ),
            (
                "create a new excel sheet of top 5 tech companies with columns Company, Valuation, CEO",
                {"action": "create", "columns": ["Company", "Valuation", "CEO"], "has_match": True},
            ),
            (
                "open excel and create a spreadsheet",
                {"action": "create", "has_match": True},
            ),
            (
                "create a spreadsheet",
                {"action": "create", "has_match": True},
            ),
            (
                "new spreadsheet",
                {"action": "create", "has_match": True},
            ),
            (
                "play music on spotify",
                {"has_match": False},
            ),
            (
                "python cheat sheet",
                {"has_match": False},
            ),
            (
                "search for best restaurants",
                {"has_match": False},
            ),
        ]
        for query, expected in cases:
            with self.subTest(query=query):
                res = resolve_spreadsheet_request(query)
                if expected.get("has_match"):
                    self.assertIsNotNone(res, f"Failed to match query: {query}")
                    self.assertEqual(res["action"], expected["action"])
                    if "columns" in expected:
                        self.assertEqual(res["columns"], expected["columns"])
                    if "topic" in expected:
                        self.assertIn(expected["topic"].lower(), str(res["topic"]).lower())
                else:
                    self.assertIsNone(res, f"Query should not have matched: {query}")

    def test_generate_table_tsv_explicit_columns(self):
        tsv, cols = generate_table_tsv(None, ["First Name", "Last Name", "Email"], "")
        self.assertEqual(cols, ["First Name", "Last Name", "Email"])
        lines = tsv.splitlines()
        self.assertGreaterEqual(len(lines), 2)
        self.assertEqual(lines[0], "First Name\tLast Name\tEmail")
        for line in lines:
            self.assertEqual(len(line.split("\t")), 3)

    def test_generate_table_tsv_topic_budget(self):
        tsv, cols = generate_table_tsv("monthly budget", [], "")
        self.assertIn("Category", cols)
        lines = tsv.splitlines()
        self.assertGreaterEqual(len(lines), 3)
        self.assertIn("\t", lines[0])

    @patch("tools.spreadsheet_tool.set_system_clipboard", return_value=True)
    @patch("tools.spreadsheet_tool.find_open_spreadsheet_window")
    def test_handle_request_creates_excel_spreadsheet(self, mock_find_win, mock_clipboard):
        mock_find_win.return_value = {
            "title": "Book1 - Excel",
            "process": "excel.exe",
            "pid": 1234,
            "window_id": "1",
            "source": "cua",
            "app_type": "excel",
        }
        res = handle_request({
            "action": "create",
            "topic": "student grades",
            "columns": ["Student", "Math", "Science"],
            "raw_prompt": "create a student grades spreadsheet",
        })
        self.assertTrue(res["success"])
        self.assertEqual(res["target_app"], "Microsoft Excel")
        self.assertIn("Microsoft Excel", res["message"])
        self.assertEqual(res["columns"], ["Student", "Math", "Science"])
        self.assertIn("Student\tMath\tScience", res["tsv_data"])

    def test_classify_request_spreadsheet_fastpath_bypasses_screen_capture(self):
        warnings = []
        with patch("ai.client.ask_groq_vision", side_effect=AssertionError("Groq vision must not be called")) as mock_vision:
            result = classify_request(
                "create a spreadsheet with columns Name, Email, Phone",
                None,
                warnings,
                None,
                agent_mode=True,
            )
            self.assertIsNotNone(result)
            self.assertEqual(result["intent"], "SPREADSHEET")
            self.assertFalse(result["needs_screen"])
            self.assertFalse(result["is_continuation"])
            mock_vision.assert_not_called()

    @patch("tools.spreadsheet_tool.set_system_clipboard", return_value=True)
    @patch("tools.spreadsheet_tool.find_open_spreadsheet_window")
    def test_run_spreadsheet_tool_returns_clean_blinky_result(
        self, mock_find_win, mock_clipboard
    ):
        mock_find_win.return_value = {
            "title": "Book1 - Excel",
            "process": "excel.exe",
            "pid": 1234,
            "window_id": "1",
            "source": "cua",
            "app_type": "excel",
        }
        params = {
            "action": "create",
            "topic": "project tasks",
            "columns": ["Task", "Owner", "Status"],
            "raw_prompt": "create a project tasks spreadsheet",
        }
        started = 0.0
        warnings = []
        out = run_spreadsheet_tool(params, started, warnings)

        self.assertIn("Microsoft Excel", out["summary"])
        self.assertEqual(out["steps"], [])
        self.assertEqual(out["ocr"], {"count": 0, "items": []})
        self.assertEqual(out["active_app"]["title"], "Microsoft Excel")
        self.assertEqual(out["active_app"]["process"], "excel")
        self.assertTrue(out["active_app"]["supported"])

    def test_resolve_spreadsheet_request_cell_operations(self):
        # 1. Direct type in cell
        res1 = resolve_spreadsheet_request("type hello in cell b1")
        self.assertIsNotNone(res1)
        self.assertEqual(res1["action"], "type_in_cell")
        self.assertEqual(res1["cell"], "B1")
        self.assertEqual(res1["text"], "hello")
        self.assertEqual(res1["preferred_app"], "excel")

        # 2. To type in cell A1
        res2 = resolve_spreadsheet_request("to type hello in cell a1")
        self.assertIsNotNone(res2)
        self.assertEqual(res2["action"], "type_in_cell")
        self.assertEqual(res2["cell"], "A1")
        self.assertEqual(res2["text"], "hello")
        self.assertEqual(res2["preferred_app"], "excel")

        # 3. Write in cell with Excel app
        res3 = resolve_spreadsheet_request("in excel type hello in cell a1")
        self.assertIsNotNone(res3)
        self.assertEqual(res3["action"], "type_in_cell")
        self.assertEqual(res3["cell"], "A1")
        self.assertEqual(res3["text"], "hello")
        self.assertEqual(res3["preferred_app"], "excel")

        # 4. Continuation switch to Excel
        res4 = resolve_spreadsheet_request("do it in the excel microsoft app instead that is opened now")
        self.assertIsNotNone(res4)
        self.assertEqual(res4["action"], "type_in_cell")
        self.assertEqual(res4["preferred_app"], "excel")

    def test_classify_request_cell_operations_bypass_screen_capture(self):
        prompts = [
            "type hello in cell b1",
            "to type hello in cell a1",
            "write 100 in cell c2",
            "do it in the excel microsoft app instead that is opened now",
        ]
        for p in prompts:
            with self.subTest(prompt=p):
                res = classify_request(p, None, [])
                self.assertEqual(res["intent"], "SPREADSHEET")
                self.assertFalse(res["needs_screen"])

    @patch("tools.spreadsheet_tool.execute_type_in_cell")
    def test_handle_request_type_in_cell(self, mock_exec):
        mock_exec.return_value = {
            "success": True,
            "action": "type_in_cell",
            "message": "Focused Microsoft Excel, selected cell A1, and entered 'hello'.",
            "cell": "A1",
            "text": "hello",
            "target_app": "Microsoft Excel",
        }
        res = handle_request({
            "action": "type_in_cell",
            "cell": "A1",
            "text": "hello",
            "preferred_app": "excel",
        })
        self.assertTrue(res["success"])
        self.assertEqual(res["action"], "type_in_cell")
        self.assertIn("Focused Microsoft Excel", res["message"])
        mock_exec.assert_called_once_with("A1", "hello", preferred_app="excel")

    def test_cell_to_row_col(self):
        self.assertEqual(cell_to_row_col("A1"), (0, 0))
        self.assertEqual(cell_to_row_col("C2"), (1, 2))
        self.assertEqual(cell_to_row_col("B10"), (9, 1))
        self.assertEqual(cell_to_row_col("AA1"), (0, 26))

    def test_resolve_multi_cell_and_whole_text_queries(self):
        # 1. Multi-cell query
        res1 = resolve_spreadsheet_request("write hello in google sheets at a1 and bye at c2")
        self.assertIsNotNone(res1)
        self.assertEqual(res1["action"], "type_in_cells")
        self.assertEqual(res1["preferred_app"], "excel")
        self.assertEqual(
            res1["cells"],
            [{"cell": "A1", "text": "hello"}, {"cell": "C2", "text": "bye"}],
        )

        # 2. Whole text in cell C2
        res2 = resolve_spreadsheet_request("write this whole text in c2 hello in google sheets at a1 and bye")
        self.assertIsNotNone(res2)
        self.assertEqual(res2["action"], "type_in_cell")
        self.assertEqual(res2["cell"], "C2")
        self.assertEqual(res2["text"], "hello in google sheets at a1 and bye")
        self.assertEqual(res2["preferred_app"], "excel")

        # 3. Exact user compound prompt
        exact_query = """write hello in google sheets at a1 and bye at c2

but write this whole text in c2 hello in google sheets at a1 and bye"""
        res3 = resolve_spreadsheet_request(exact_query)
        self.assertIsNotNone(res3)
        self.assertEqual(res3["action"], "type_in_cells")
        self.assertEqual(res3["preferred_app"], "excel")
        self.assertEqual(
            res3["cells"],
            [
                {"cell": "A1", "text": "hello"},
                {"cell": "C2", "text": "hello in google sheets at a1 and bye"},
            ],
        )

    @patch("tools.spreadsheet_tool.execute_type_in_cells")
    def test_handle_request_type_in_cells(self, mock_exec):
        mock_exec.return_value = {
            "success": True,
            "action": "type_in_cells",
            "message": "Focused Microsoft Excel and entered into 2 cells: A1='hello', C2='bye'.",
            "cells": [{"cell": "A1", "text": "hello"}, {"cell": "C2", "text": "bye"}],
            "target_app": "Microsoft Excel",
        }
        res = handle_request({
            "action": "type_in_cells",
            "cells": [{"cell": "A1", "text": "hello"}, {"cell": "C2", "text": "bye"}],
            "preferred_app": "excel",
        })
        self.assertTrue(res["success"])
        self.assertEqual(res["action"], "type_in_cells")
        self.assertIn("Focused Microsoft Excel", res["message"])
        mock_exec.assert_called_once_with(
            [{"cell": "A1", "text": "hello"}, {"cell": "C2", "text": "bye"}],
            preferred_app="excel",
        )

    @patch("ctypes.windll.user32")
    def test_focus_already_foreground_strictly_preserves_state(self, mock_user32):
        mock_user32.GetForegroundWindow.return_value = 12345
        focus_spreadsheet_window({"hwnd": 12345, "title": "Book1 - Excel"})
        mock_user32.ShowWindow.assert_not_called()
        mock_user32.BringWindowToTop.assert_not_called()

    @patch("ctypes.windll.user32")
    def test_focus_visible_window_preserves_maximized_or_normal_state(self, mock_user32):
        mock_user32.GetForegroundWindow.return_value = 999
        mock_user32.IsIconic.return_value = 0
        mock_user32.GetWindowThreadProcessId.side_effect = [1, 2]
        focus_spreadsheet_window({"hwnd": 12345, "title": "Book1 - Excel"})
        # Must call ShowWindow with 5 (SW_SHOW), NEVER 9 (SW_RESTORE which un-maximizes)
        mock_user32.ShowWindow.assert_called_once_with(12345, 5)
        mock_user32.BringWindowToTop.assert_called_once_with(12345)
        mock_user32.SetForegroundWindow.assert_called_once_with(12345)

    @patch("ctypes.windll.user32")
    def test_focus_minimized_maximized_window_restores_maximized(self, mock_user32):
        mock_user32.GetForegroundWindow.return_value = 999
        mock_user32.IsIconic.return_value = 1

        def fake_placement(hwnd, lpp):
            lpp._obj.flags = 2  # WPF_RESTORETOMAXIMIZED
            return True

        mock_user32.GetWindowPlacement.side_effect = fake_placement
        mock_user32.GetWindowThreadProcessId.side_effect = [1, 1]
        focus_spreadsheet_window({"hwnd": 12345, "title": "Book1 - Excel"})
        # Must call ShowWindow with 3 (SW_MAXIMIZE)
        mock_user32.ShowWindow.assert_called_once_with(12345, 3)

    @patch("ctypes.windll.user32")
    def test_focus_minimized_normal_window_restores_normal(self, mock_user32):
        mock_user32.GetForegroundWindow.return_value = 999
        mock_user32.IsIconic.return_value = 1

        def fake_placement(hwnd, lpp):
            lpp._obj.flags = 0
            return True

        mock_user32.GetWindowPlacement.side_effect = fake_placement
        mock_user32.GetWindowThreadProcessId.side_effect = [1, 1]
        focus_spreadsheet_window({"hwnd": 12345, "title": "Book1 - Excel"})
        # Must call ShowWindow with 9 (SW_RESTORE)
        mock_user32.ShowWindow.assert_called_once_with(12345, 9)

    @patch("tools.spreadsheet_tool.extract_table_data_from_url")
    def test_generate_table_tsv_extracts_from_url(self, mock_extract):
        mock_extract.return_value = (
            "Repository: KingSahil/Blinky\nSource: https://github.com/KingSahil/blinky\n\nContributor\tGitHub\nSahil\t@KingSahil",
            ["Contributor", "GitHub"],
        )
        tsv, cols = generate_table_tsv(
            None,
            None,
            "go to https://github.com/KingSahil/blinky and extract contributors to excel",
        )
        mock_extract.assert_called_once_with(
            "https://github.com/KingSahil/blinky",
            "go to https://github.com/KingSahil/blinky and extract contributors to excel",
        )
        self.assertIn("Repository: KingSahil/Blinky", tsv)
        self.assertEqual(cols, ["Contributor", "GitHub"])

    def test_resolve_spreadsheet_request_format_phrasings(self):
        cases = [
            "good just formatting is little bad also format the text so everything clearly visible",
            "format excel so everything clearly visible",
            "autofit columns in excel",
            "format the text so everything clearly visible",
        ]
        for query in cases:
            res = resolve_spreadsheet_request(query)
            self.assertIsNotNone(res, f"Failed to match format query: {query}")
            self.assertEqual(res["action"], "format")
            self.assertEqual(res["preferred_app"], "excel")

    @patch("tools.spreadsheet_tool.execute_format_spreadsheet")
    def test_handle_request_format_action(self, mock_fmt):
        mock_fmt.return_value = {
            "success": True,
            "action": "format",
            "message": "Formatted Microsoft Excel worksheet: auto-fitted all columns, styled headers, and ensured all text is clearly visible.",
            "target_app": "Microsoft Excel",
        }
        res = handle_request({"action": "format"})
        self.assertTrue(res["success"])
        self.assertEqual(res["action"], "format")
        mock_fmt.assert_called_once()


if __name__ == "__main__":
    unittest.main()
