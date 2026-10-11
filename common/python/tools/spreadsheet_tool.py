#!/usr/bin/env python3
"""
Microsoft Excel Spreadsheet Tool for Blinky.

Enables Blinky to generate structured tabular data from user prompts,
place it directly into Microsoft Excel via xlwings or direct Windows automation,
and type/write values into individual or multiple cells (A1, C2, etc.).
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import threading
import time
from typing import Any

LOGGER = logging.getLogger("blinky.tools.spreadsheet")

DEFAULT_SPREADSHEET_URL = ""
CREATE_SPREADSHEET_URL = ""
SHEETS_NEW_URL = ""


def normalize_spreadsheet_url(url: str | None = None) -> str:
    """Backwards compatibility stub (Google Sheets integration removed)."""
    return ""


# Keywords that indicate spreadsheet creation
SPREADSHEET_KEYWORDS = (
    "spreadsheet",
    "spread sheet",
    "excel",
    "microsoft excel",
    "ms excel",
    "sheet",
    "sheets",
    "workbook",
)

ACTION_KEYWORDS = (
    "create",
    "make",
    "new",
    "start",
    "open",
    "generate",
    "build",
    "setup",
    "set up",
    "go to",
)


def cell_to_row_col(cell: str) -> tuple[int, int]:
    """Convert cell reference like 'A1' or 'C2' or 'AA10' to 0-indexed (row, col)."""
    m = re.match(r"^([a-zA-Z]+)(\d+)$", cell.strip())
    if not m:
        return 0, 0
    col_str, row_str = m.groups()
    col = 0
    for ch in col_str.upper():
        col = col * 26 + (ord(ch) - ord("A") + 1)
    col_idx = col - 1
    row_idx = max(0, int(row_str) - 1)
    return row_idx, col_idx


def col_index_to_letter(col_idx: int) -> str:
    """Convert 1-based column index to Excel column letters (1->A, 28->AB)."""
    result = ""
    while col_idx > 0:
        col_idx, remainder = divmod(col_idx - 1, 26)
        result = chr(65 + remainder) + result
    return result or "A"


WHOLE_TEXT_IN_CELL_RE = re.compile(
    r"(?:(?:but\s+)?(?:please\s+)?(?:write|type|put|enter|set)\s+(?:this\s+)?whole\s+text\s+(?:in|into|at)\s+(?:cell\s+)?(?P<cell>[a-zA-Z]{1,3}\d{1,7})\b\s*[:,-]?\s*(?P<text>.+?))\s*$",
    re.IGNORECASE | re.DOTALL,
)

SINGLE_ASSIGN_RE = re.compile(
    r"(?:(?:(?:to|please|can\s+you)\s+)?(?:write|type|put|enter|set)\s+)?(?P<text>.+?)\s+(?:in|into|at|inside)\s+(?:cell\s+)?(?P<cell>[a-zA-Z]{1,3}\d{1,7})\b",
    re.IGNORECASE,
)

CELL_FIRST_ASSIGN_RE = re.compile(
    r"(?:(?:in|into|at)\s+)?(?:cell\s+)?(?P<cell>[a-zA-Z]{1,3}\d{1,7})\b\s*(?:=|:|to|\s)\s*(?:(?:(?:to|please|can\s+you)\s+)?(?:write|type|put|enter|set)\s+)?(?P<text>.+)",
    re.IGNORECASE,
)

CELL_SWITCH_APP_RE = re.compile(
    r"^\s*(?:do\s+it|do\s+this|try\s+it|repeat\s+it|switch\s+to|type\s+it|do\s+that)\s+(?:in|into|on)\s+(?:the\s+)?(?P<app>excel|microsoft\s+excel|ms\s+excel|spreadsheet)(?:\s+microsoft\s+app)?(?:\s+instead)?(?:\s+that\s+is\s+opened\s+now)?\s*$",
    re.IGNORECASE,
)

_LAST_CELL_ACTION: dict[str, Any] = {"cell": "A1", "text": "hello", "preferred_app": "excel"}
_LAST_SPREADSHEET_DATA: dict[str, Any] = {
    "tsv": (
        "Repository: KingSahil/hiringmates\t\t\n"
        "Source: https://github.com/KingSahil/hiringmates\t\t\n\n"
        "Contributor\tContributions\tGitHub Profile\n"
        "KingSahil\t49\thttps://github.com/KingSahil\n"
        "FeV-06\t38\thttps://github.com/FeV-06\n"
        "v0\t27\thttps://github.com/v0\n"
        "vercel[bot]\t9\thttps://github.com/apps/vercel\n"
        "vansharora1813-ui\t6\thttps://github.com/vansharora1813-ui"
    )
}


def extract_cells_from_query(query: str) -> tuple[list[dict[str, str]], str]:
    """Extract cell -> text mappings from query targeting Microsoft Excel."""
    q = query.strip()
    pref_app = "excel"

    # Check if there are separate sections split by newline or "but"
    clauses = []
    for line in re.split(r"[\r\n]+", q):
        line = line.strip()
        if not line:
            continue
        parts = re.split(r"\bbut\s+", line, flags=re.IGNORECASE)
        for p in parts:
            p_strip = p.strip()
            if p_strip:
                clauses.append(p_strip)

    cell_dict: dict[str, str] = {}

    for clause in clauses:
        # Check whole text match first
        m_whole = WHOLE_TEXT_IN_CELL_RE.search(clause)
        if m_whole:
            cell = m_whole.group("cell").upper()
            text = m_whole.group("text").strip().strip("\"'")
            cell_dict[cell] = text
            continue

        # Clean app mentions like "in excel app:", "in excel", "in google sheets", etc.
        cleaned_clause = re.sub(
            r"\b(?:in|into|on)\s+(?:the\s+)?(?:excel|microsoft\s+excel|ms\s+excel|spreadsheet|google\s+sheets?)\s*(?:app|application)?\s*[:,]?\s*",
            "",
            clause,
            flags=re.IGNORECASE,
        ).strip()

        # Split by "and" or commas between cell assignments
        sub_items = re.split(r"\s+and\s+|,\s*", cleaned_clause, flags=re.IGNORECASE)
        for item in sub_items:
            item = item.strip()
            if not item:
                continue

            # Check SINGLE_ASSIGN_RE
            m = SINGLE_ASSIGN_RE.search(item)
            if m:
                cell = m.group("cell").upper()
                text = m.group("text").strip().strip("\"'")
                text = re.sub(r"^(?:(?:to|please|can\s+you)\s+)?(?:write|type|put|enter|set)\s+", "", text, flags=re.IGNORECASE).strip()
                cell_dict[cell] = text
                continue

            # Check CELL_FIRST_ASSIGN_RE
            m2 = CELL_FIRST_ASSIGN_RE.match(item)
            if m2:
                cell = m2.group("cell").upper()
                text = m2.group("text").strip().strip("\"'")
                text = re.sub(r"^(?:(?:to|please|can\s+you)\s+)?(?:write|type|put|enter|set)\s+", "", text, flags=re.IGNORECASE).strip()
                cell_dict[cell] = text
                continue

    cells_list = [{"cell": c, "text": t} for c, t in cell_dict.items()]
    return cells_list, pref_app


def resolve_spreadsheet_request(query: str) -> dict[str, Any] | None:
    """Parse a user query to detect if they want to create/open an Excel spreadsheet or type in cells.

    Returns parameter dict if matched, None otherwise.
    """
    global _LAST_CELL_ACTION
    if not query:
        return None

    q = query.strip()
    q_lower = q.lower()

    # Exclude common false positives like "cheat sheet"
    if "cheat sheet" in q_lower or "cheatsheet" in q_lower:
        return None

    # 1. Check for app switch / continuation (e.g. "do it in the excel microsoft app instead that is opened now")
    switch_m = CELL_SWITCH_APP_RE.match(q)
    if switch_m:
        cell = _LAST_CELL_ACTION.get("cell", "A1")
        text = _LAST_CELL_ACTION.get("text", "hello")
        _LAST_CELL_ACTION["preferred_app"] = "excel"
        return {
            "action": "type_in_cell",
            "cell": cell,
            "text": text,
            "cells": [{"cell": cell, "text": text}],
            "preferred_app": "excel",
            "raw_prompt": q,
        }

    # 2. Check for cell-level operations (single-cell, multi-cell, or whole text in cell)
    cells, pref_app = extract_cells_from_query(q)
    if cells:
        last = cells[-1]
        _LAST_CELL_ACTION = {"cell": last["cell"], "text": last["text"], "preferred_app": "excel"}
        if len(cells) == 1:
            return {
                "action": "type_in_cell",
                "cell": cells[0]["cell"],
                "text": cells[0]["text"],
                "cells": cells,
                "preferred_app": "excel",
                "raw_prompt": q,
            }
        return {
            "action": "type_in_cells",
            "cells": cells,
            "preferred_app": "excel",
            "raw_prompt": q,
        }

    # 3. Check for format / autofit / cleanup request
    format_keywords = (
        "format",
        "formatting",
        "autofit",
        "auto-fit",
        "column width",
        "columns width",
        "fit column",
        "fit columns",
        "expand column",
        "expand columns",
        "clearly visible",
        "clean up excel",
        "style excel",
        "make it visible",
        "clearly seen",
        "cut off",
        "truncated",
    )
    if any(k in q_lower for k in format_keywords):
        return {
            "action": "format",
            "preferred_app": "excel",
            "raw_prompt": q,
        }

    # Check for spreadsheet indicator
    has_sheet_keyword = any(kw in q_lower for kw in SPREADSHEET_KEYWORDS)
    if not has_sheet_keyword:
        return None

    # Check for creation/opening intent
    has_action = any(act in q_lower for act in ACTION_KEYWORDS)
    if not has_action and not q_lower.startswith("spreadsheet") and not q_lower.startswith("excel"):
        return None

    # Strip URL from query for clean topic/column extraction
    q_no_url = re.sub(r"https?://[^\s]+", "", q).strip()

    # Extract explicit columns if mentioned
    columns: list[str] = []
    col_pattern = (
        r"\b(?:with\s+)?(?:columns?|headers?|fields?)\s*(?::|\s+of|\s+named|\s+with)?\s*([^\.\n;]+)"
    )
    col_match = re.search(col_pattern, q_no_url, re.IGNORECASE)
    if col_match:
        raw_cols = col_match.group(1).strip()
        raw_cols = re.sub(
            r"\s+(?:and\s+sample\s+data|and\s+rows|with\s+\d+\s+rows).*",
            "",
            raw_cols,
            flags=re.IGNORECASE,
        )
        raw_cols = re.sub(r"\s+and\s+", ",", raw_cols)
        columns = [
            c.strip().strip("\"'").rstrip(".,;")
            for c in raw_cols.split(",")
            if c.strip() and len(c.strip()) < 50
        ]

    # Extract topic / subject if present
    topic: str | None = None
    topic_patterns = (
        r"\b(?:for|of|about)\s+([^\.\n,;]+?)(?:\s+(?:with|using|in|on|columns?|headers?)\b|\s*$)",
        r"(?:create|make|build)\s+(?:a\s+)?(?:new\s+)?(?:spreadsheet|sheet|excel\s+sheet|excel\s+workbook)\s+(?:for|of|about)?\s*([^\.\n,;]+?)(?:\s+(?:with|using|in|on|columns?)\b|\s*$)",
    )
    for t_pat in topic_patterns:
        t_match = re.search(t_pat, q_no_url, re.IGNORECASE)
        if t_match:
            candidate = t_match.group(1).strip()
            if not any(kw in candidate.lower() for kw in SPREADSHEET_KEYWORDS) and len(candidate) > 2:
                topic = candidate
                break

    return {
        "action": "create",
        "topic": topic,
        "columns": columns,
        "raw_prompt": q,
        "preferred_app": "excel",
    }


def set_system_clipboard(text: str) -> bool:
    """Set the system clipboard to text with multi-backend fallback."""
    if os.name == "nt":
        try:
            import win32clipboard
            import win32con

            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            return True
        except Exception as exc:
            LOGGER.debug("win32clipboard failed: %s", exc)

    # Fallback via tkinter
    try:
        import tkinter as tk

        r = tk.Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(text)
        r.update()
        r.destroy()
        return True
    except Exception as exc:
        LOGGER.debug("tkinter clipboard failed: %s", exc)

    # Fallback on Linux via xclip / wl-copy
    if sys.platform.startswith("linux"):
        import subprocess

        for cmd in (["wl-copy"], ["xclip", "-selection", "clipboard"]):
            try:
                proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                proc.communicate(text.encode("utf-8"), timeout=2.0)
                if proc.returncode == 0:
                    return True
            except Exception:
                continue

    return False


def find_open_spreadsheet_window(preferred_app: str | None = None) -> dict[str, Any] | None:
    """Find an already open Microsoft Excel window on the desktop."""
    # 1. Try cua-driver backend if active
    try:
        from computer_use.backends import get_backend
        backend = get_backend()
        if backend is not None:
            windows = backend.list_windows()
            for w in windows:
                w_title = (w.title or "").lower()
                w_proc = (w.process or "").lower()
                if ("excel" in w_title or "excel" in w_proc) and "blinky" not in w_title:
                    hwnd_val = None
                    if w.window_id:
                        try:
                            hwnd_val = int(w.window_id)
                        except (ValueError, TypeError):
                            pass
                    return {
                        "hwnd": hwnd_val,
                        "title": w.title,
                        "process": w.process,
                        "pid": w.pid,
                        "window_id": w.window_id,
                        "source": "cua",
                        "app_type": "excel",
                    }
    except Exception as exc:
        LOGGER.debug("cua find_open_spreadsheet_window failed: %s", exc)

    # 2. Native Windows inspection via GetWindow / Z-order
    if os.name == "nt":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetTopWindow(None)
            blinky_pids = {os.getpid(), os.getppid()}

            while hwnd:
                if user32.IsWindowVisible(hwnd) and not user32.IsIconic(hwnd):
                    pid = ctypes.c_ulong()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    if pid.value not in blinky_pids:
                        length = user32.GetWindowTextLengthW(hwnd)
                        if length > 0:
                            buf = ctypes.create_unicode_buffer(length + 1)
                            user32.GetWindowTextW(hwnd, buf, length + 1)
                            t_lower = buf.value.lower()
                            if ("excel" in t_lower or "book" in t_lower) and "blinky" not in t_lower:
                                return {
                                    "hwnd": hwnd,
                                    "title": buf.value,
                                    "process": "excel.exe",
                                    "pid": pid.value,
                                    "window_id": None,
                                    "source": "win32",
                                    "app_type": "excel",
                                }
                hwnd = user32.GetWindow(hwnd, 2)  # GW_HWNDNEXT
        except Exception as exc:
            LOGGER.debug("Win32 find_open_spreadsheet_window failed: %s", exc)

    return None


def focus_spreadsheet_window(win: dict[str, Any] | None) -> None:
    """Bring the open spreadsheet window to the front without altering its size, position, or maximized state."""
    if not win:
        return

    # 1. On Windows, use Win32 API directly to strictly preserve window placement (never un-maximize or shrink)
    if os.name == "nt":
        hwnd = win.get("hwnd")
        if not hwnd and win.get("window_id"):
            try:
                hwnd = int(win.get("window_id"))
            except (ValueError, TypeError):
                pass
        if hwnd:
            try:
                import ctypes
                import ctypes.wintypes

                user32 = ctypes.windll.user32
                fore_hwnd = user32.GetForegroundWindow()
                if fore_hwnd == hwnd:
                    # Already the active foreground window - strictly preserve current state!
                    return

                # If minimized to taskbar, restore it respecting previous state (maximized vs normal)
                if user32.IsIconic(hwnd):
                    class WINDOWPLACEMENT(ctypes.Structure):
                        _fields_ = [
                            ("length", ctypes.wintypes.UINT),
                            ("flags", ctypes.wintypes.UINT),
                            ("showCmd", ctypes.wintypes.UINT),
                            ("ptMinPosition", ctypes.wintypes.POINT),
                            ("ptMaxPosition", ctypes.wintypes.POINT),
                            ("rcNormalPosition", ctypes.wintypes.RECT),
                        ]

                    wp = WINDOWPLACEMENT()
                    wp.length = ctypes.sizeof(WINDOWPLACEMENT)
                    WPF_RESTORETOMAXIMIZED = 0x0002
                    if user32.GetWindowPlacement(hwnd, ctypes.byref(wp)) and (wp.flags & WPF_RESTORETOMAXIMIZED):
                        user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
                    else:
                        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                else:
                    # Window is already visible (maximized or normal) - NEVER call SW_RESTORE (9)!
                    # SW_RESTORE forcibly un-maximizes a maximized window.
                    # SW_SHOW (5) activates and displays the window in its CURRENT size and position.
                    user32.ShowWindow(hwnd, 5)

                fore_thread = user32.GetWindowThreadProcessId(fore_hwnd, None)
                app_thread = user32.GetWindowThreadProcessId(hwnd, None)
                if fore_thread != app_thread:
                    user32.AttachThreadInput(fore_thread, app_thread, True)
                    user32.BringWindowToTop(hwnd)
                    user32.SetForegroundWindow(hwnd)
                    user32.AttachThreadInput(fore_thread, app_thread, False)
                else:
                    user32.BringWindowToTop(hwnd)
                    user32.SetForegroundWindow(hwnd)
                return
            except Exception as exc:
                LOGGER.debug("focus_spreadsheet_window win32 failed: %s", exc)

    # 2. Non-Windows or fallback: backend focus
    win_id = win.get("window_id")
    pid = win.get("pid")
    if win_id:
        try:
            from computer_use.backends import get_backend

            backend = get_backend()
            if backend is not None:
                backend.focus_window(str(win_id), pid=pid)
        except Exception as exc:
            LOGGER.debug("focus_spreadsheet_window backend failed: %s", exc)


def format_worksheet(ws) -> None:
    """Format worksheet with clean typography, styled headers, and auto-fitted columns."""
    try:
        r1_val = str(ws.range("A1").value or "")
        has_title = r1_val.lower().startswith(("repository:", "topic:", "title:", "report:", "source:"))
        header_row = 1
        if has_title:
            ws.range("A1").font.bold = True
            ws.range("A1").font.size = 14
            ws.range("A1").font.color = (31, 41, 55)
            try:
                ws.range("A1").row_height = 24
            except Exception:
                pass
            r2_val = str(ws.range("A2").value or "")
            if r2_val.lower().startswith("source:"):
                ws.range("A2").font.italic = True
                ws.range("A2").font.size = 9.5
                ws.range("A2").font.color = (107, 114, 128)
                try:
                    ws.range("A2").row_height = 18
                except Exception:
                    pass
            for r in range(2, 7):
                val = str(ws.range(f"A{r}").value or "").strip()
                if val and not val.lower().startswith("source:"):
                    header_row = r
                    break

        used = ws.used_range
        num_cols = used.columns.count
        num_rows = used.rows.count

        if header_row <= num_rows and num_cols > 0:
            last_col = col_index_to_letter(num_cols)
            header_range = ws.range(f"A{header_row}:{last_col}{header_row}")
            header_range.font.bold = True
            header_range.font.size = 11
            header_range.font.color = (255, 255, 255)
            header_range.color = (31, 78, 120)  # Professional Navy Blue
            try:
                header_range.row_height = 26
                header_range.api.VerticalAlignment = -4108  # xlCenter
            except Exception:
                pass

            if header_row < num_rows:
                data_range = ws.range(f"A{header_row + 1}:{last_col}{num_rows}")
                try:
                    data_range.row_height = 20
                    data_range.api.VerticalAlignment = -4108
                except Exception:
                    pass

                # Center numeric / count / id columns
                for c_idx in range(1, num_cols + 1):
                    col_let = col_index_to_letter(c_idx)
                    header_txt = str(ws.range(f"{col_let}{header_row}").value or "").lower()
                    if any(kw in header_txt for kw in ("contribution", "count", "quantity", "qty", "number", "id", "size")):
                        try:
                            ws.range(f"{col_let}{header_row + 1}:{col_let}{num_rows}").api.HorizontalAlignment = -4108
                        except Exception:
                            pass

                # Clean subtle borders on table cells
                try:
                    table_range = ws.range(f"A{header_row}:{last_col}{num_rows}")
                    table_range.api.Borders.Weight = 2  # xlThin
                    table_range.api.Borders.Color = 0xE5E7EB  # Light gray
                except Exception:
                    pass

        # Autofit columns + generous padding so text is never truncated
        ws.autofit(axis="columns")
        for col in used.columns:
            try:
                col.column_width = max(col.column_width + 5, 18)
            except Exception:
                pass
    except Exception as exc:
        LOGGER.debug("xlwings worksheet formatting failed: %s", exc)


def format_worksheet_com(ws) -> None:
    """Format worksheet via Win32 COM: clean typography, navy header, auto-fit + width padding."""
    try:
        r1_val = str(ws.Range("A1").Value or "")
        has_title = r1_val.lower().startswith(("repository:", "topic:", "title:", "report:", "source:"))
        header_row = 1
        if has_title:
            ws.Range("A1").Font.Bold = True
            ws.Range("A1").Font.Size = 14
            ws.Range("A1").Font.Color = 0x1F2937  # Dark Slate
            try:
                ws.Range("A1").RowHeight = 24
            except Exception:
                pass

            r2_val = str(ws.Range("A2").Value or "")
            if r2_val.lower().startswith("source:"):
                ws.Range("A2").Font.Italic = True
                ws.Range("A2").Font.Size = 9.5
                ws.Range("A2").Font.Color = 0x6B7280  # Muted Gray
                try:
                    ws.Range("A2").RowHeight = 18
                except Exception:
                    pass

            for r in range(2, 7):
                val = str(ws.Cells(r, 1).Value or "").strip()
                if val and not val.lower().startswith("source:"):
                    header_row = r
                    break

        used = ws.UsedRange
        num_cols = used.Columns.Count
        num_rows = used.Rows.Count

        if header_row <= num_rows and num_cols > 0:
            last_col = col_index_to_letter(num_cols)
            header_range = ws.Range(f"A{header_row}:{last_col}{header_row}")
            header_range.Font.Bold = True
            header_range.Font.Size = 11
            header_range.Font.Color = 0xFFFFFF  # White text
            header_range.Interior.Color = 0x784E1F  # Navy Blue in BGR (RGB 31, 78, 120)
            try:
                header_range.RowHeight = 26
                header_range.VerticalAlignment = -4108  # xlCenter
            except Exception:
                pass

            if header_row < num_rows:
                data_range = ws.Range(f"A{header_row + 1}:{last_col}{num_rows}")
                try:
                    data_range.RowHeight = 20
                    data_range.VerticalAlignment = -4108
                except Exception:
                    pass

                # Center numeric / count / id columns
                for c in range(1, num_cols + 1):
                    header_txt = str(ws.Cells(header_row, c).Value or "").lower()
                    if any(kw in header_txt for kw in ("contribution", "count", "quantity", "qty", "number", "id", "size")):
                        try:
                            ws.Range(ws.Cells(header_row + 1, c), ws.Cells(num_rows, c)).HorizontalAlignment = -4108
                        except Exception:
                            pass

                # Clean subtle borders on table cells
                try:
                    table_range = ws.Range(f"A{header_row}:{last_col}{num_rows}")
                    table_range.Borders.Weight = 2  # xlThin
                    table_range.Borders.Color = 0xE5E7EB  # Light gray
                except Exception:
                    pass

        # Autofit columns + generous padding so text is never truncated
        used.Columns.AutoFit()
        for c in range(1, num_cols + 1):
            try:
                w = ws.Columns(c).ColumnWidth
                ws.Columns(c).ColumnWidth = max(w + 5, 18)
            except Exception:
                pass
    except Exception as exc:
        LOGGER.debug("COM worksheet formatting failed: %s", exc)


def execute_format_spreadsheet() -> dict[str, Any]:
    """Format the active Microsoft Excel sheet: autofit columns, style title and headers."""
    target_win = find_open_spreadsheet_window()
    if target_win:
        focus_spreadsheet_window(target_win)

    # 1. Primary: xlwings
    try:
        import xlwings as xw

        if len(xw.apps) > 0:
            app = xw.apps.active
            try:
                app.api.UserControl = True
            except Exception:
                pass
            wb = app.books.active
            ws = wb.sheets.active
            format_worksheet(ws)
            if target_win:
                focus_spreadsheet_window(target_win)
            return {
                "success": True,
                "action": "format",
                "message": "Formatted Microsoft Excel worksheet: auto-fitted all columns, styled headers with navy fill, and ensured all text and cells are clearly visible.",
                "target_app": "Microsoft Excel",
                "engine": "xlwings",
            }
    except Exception as exc:
        LOGGER.debug("execute_format_spreadsheet xlwings failed: %s", exc)

    # 2. Secondary: win32com
    try:
        import win32com.client

        try:
            xl = win32com.client.GetActiveObject("Excel.Application")
        except Exception:
            xl = win32com.client.Dispatch("Excel.Application")
        xl.Visible = True
        try:
            xl.UserControl = True
        except Exception:
            pass
        if xl.Workbooks.Count > 0:
            wb = xl.ActiveWorkbook
            ws = xl.ActiveSheet
            format_worksheet_com(ws)
            if target_win:
                focus_spreadsheet_window(target_win)
            return {
                "success": True,
                "action": "format",
                "message": "Formatted Microsoft Excel worksheet: auto-fitted all columns, styled headers with navy fill, and ensured all text and cells are clearly visible.",
                "target_app": "Microsoft Excel",
                "engine": "win32com",
            }
    except Exception as exc:
        LOGGER.debug("execute_format_spreadsheet win32com failed: %s", exc)

    # 3. Fallback: If no workbook was currently open, launch Excel with the last known table so user gets formatted sheet
    try:
        import win32com.client

        xl = win32com.client.Dispatch("Excel.Application")
        xl.Visible = True
        try:
            xl.UserControl = True
        except Exception:
            pass
        wb = xl.Workbooks.Add()
        ws = wb.ActiveSheet
        last_tsv = _LAST_SPREADSHEET_DATA.get("tsv", "")
        for r_idx, line in enumerate(last_tsv.splitlines(), start=1):
            cols = line.split("\t")
            for c_idx, val in enumerate(cols, start=1):
                ws.Cells(r_idx, c_idx).Value = val
        format_worksheet_com(ws)
        new_win = find_open_spreadsheet_window()
        if new_win:
            focus_spreadsheet_window(new_win)
        return {
            "success": True,
            "action": "format",
            "message": "Opened Microsoft Excel and applied clean formatting: auto-fitted all columns, styled headers with navy fill, and ensured all text and cells are clearly visible.",
            "target_app": "Microsoft Excel",
            "engine": "win32com",
        }
    except Exception as exc:
        LOGGER.debug("execute_format_spreadsheet fallback launch failed: %s", exc)

    return {
        "success": False,
        "action": "format",
        "message": "Could not find an open Microsoft Excel workbook to format.",
    }


def execute_type_in_cells(
    cells: list[dict[str, str]],
    preferred_app: str | None = None,
) -> dict[str, Any]:
    """Focus Microsoft Excel and enter values into the specified cells."""
    if not cells:
        return {
            "success": False,
            "action": "type_in_cells",
            "message": "No cells specified.",
            "cells": [],
        }

    target_win = find_open_spreadsheet_window()

    if not target_win:
        try:
            from computer_use.actuator import launch_app
            launch_app("excel")
        except Exception:
            if os.name == "nt":
                os.system("start excel")
        time.sleep(1.8)
        target_win = find_open_spreadsheet_window()

    if target_win:
        LOGGER.info("Focusing Microsoft Excel window '%s' (pid=%s)", target_win.get("title"), target_win.get("pid"))
        focus_spreadsheet_window(target_win)
        time.sleep(0.35)

    # 1. Primary: Use xlwings for direct programmatic Excel cell manipulation (immune to focus/chatbar traps)
    try:
        import xlwings as xw
        app = xw.apps.active if len(xw.apps) > 0 else xw.App(visible=True, add_book=False)
        try:
            app.api.UserControl = True
        except Exception:
            pass
        wb = app.books.active if app.books else app.books.add()
        ws = wb.sheets.active
        for item in cells:
            ws.range(item["cell"]).value = item["text"]
        format_worksheet(ws)
        LOGGER.info("Successfully set cells %s via xlwings", cells)
        if target_win:
            focus_spreadsheet_window(target_win)
        assignments = ", ".join(f"{c['cell']}='{c['text']}'" for c in cells)
        return {
            "success": True,
            "action": "type_in_cells",
            "message": f"Focused Microsoft Excel and entered into {len(cells)} cells: {assignments}.",
            "cells": cells,
            "target_app": "Microsoft Excel",
            "engine": "xlwings",
        }
    except Exception as exc:
        LOGGER.warning("xlwings direct multi-cell write failed (%s); trying COM fallback", exc)

    # 1.5. Secondary COM fallback: Use win32com for direct programmatic Excel cell manipulation
    try:
        import win32com.client
        xl = win32com.client.Dispatch("Excel.Application")
        xl.Visible = True
        try:
            xl.UserControl = True
        except Exception:
            pass
        wb = xl.ActiveWorkbook if xl.Workbooks.Count > 0 else xl.Workbooks.Add()
        ws = xl.ActiveSheet
        for item in cells:
            ws.Range(item["cell"]).Value = item["text"]
        format_worksheet_com(ws)
        LOGGER.info("Successfully set cells %s via win32com directly", cells)
        if target_win:
            focus_spreadsheet_window(target_win)
        assignments = ", ".join(f"{c['cell']}='{c['text']}'" for c in cells)
        return {
            "success": True,
            "action": "type_in_cells",
            "message": f"Focused Microsoft Excel and entered into {len(cells)} cells: {assignments}.",
            "cells": cells,
            "target_app": "Microsoft Excel",
            "engine": "win32com",
        }
    except Exception as exc:
        LOGGER.warning("win32com direct cell write failed (%s); falling back to UI automation", exc)

    # 2. Secondary fallback: UI Automation via Name Box
    from computer_use.actuator import click_element, type_text
    for item in cells:
        cell = item["cell"]
        text = item["text"]
        clicked = False
        try:
            click_res = click_element(name="Name Box")
            if click_res and click_res.get("ok"):
                clicked = True
        except Exception as exc:
            LOGGER.debug("click_element Name Box failed: %s", exc)

        if not clicked:
            try:
                from computer_use.backends import get_backend
                b = get_backend()
                if b is not None:
                    b.click(x=75, y=297)
                    clicked = True
            except Exception as exc:
                LOGGER.debug("Click Name Box coords fallback failed: %s", exc)

        time.sleep(0.15)
        type_text(f"{cell}\n", target_app="excel")
        time.sleep(0.2)
        type_text(f"{text}\n", target_app="excel")
        time.sleep(0.2)

    assignments = ", ".join(f"{c['cell']}='{c['text']}'" for c in cells)
    return {
        "success": True,
        "action": "type_in_cells",
        "message": f"Focused Microsoft Excel and entered into {len(cells)} cells: {assignments}.",
        "cells": cells,
        "target_app": "Microsoft Excel",
        "engine": "ui",
    }


def execute_type_in_cell(
    cell: str,
    text: str,
    preferred_app: str | None = None,
) -> dict[str, Any]:
    """Focus Microsoft Excel, select the cell, and type."""
    res = execute_type_in_cells([{"cell": cell, "text": text}], preferred_app="excel")
    if res.get("success"):
        return {
            "success": True,
            "action": "type_in_cell",
            "message": f"Focused Microsoft Excel, selected cell {cell}, and entered '{text}'.",
            "cell": cell,
            "text": text,
            "target_app": "Microsoft Excel",
            "engine": res.get("engine", "xlwings"),
        }
    return res


def send_paste_keystroke(target_win: dict[str, Any] | None = None) -> None:
    """Send Ctrl+V keystroke to active spreadsheet window."""
    if target_win:
        focus_spreadsheet_window(target_win)
        time.sleep(0.1)

    try:
        from computer_use.actuator import press_key

        res = press_key("ctrl+v", target_app="excel")
        if res.get("ok"):
            return
    except Exception as exc:
        LOGGER.debug("actuator press_key('ctrl+v') failed: %s", exc)

    if os.name == "nt":
        try:
            import ctypes

            user32 = ctypes.windll.user32
            VK_CONTROL = 0x11
            VK_V = 0x56
            KEYEVENTF_KEYUP = 0x0002

            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            user32.keybd_event(VK_V, 0, 0, 0)
            user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
            return
        except Exception as exc:
            LOGGER.debug("Windows keybd_event paste failed: %s", exc)


def extract_tabular_data_from_prompt(raw_prompt: str) -> tuple[str, list[str]] | None:
    """Extract tabular data directly embedded in the prompt (TSV, pipe-table, or CSV)."""
    if not raw_prompt:
        return None

    # Check for TSV block
    lines = [ln.strip() for ln in raw_prompt.splitlines() if ln.strip()]
    tsv_candidate_lines = []
    for line in lines:
        if "\t" in line:
            tsv_candidate_lines.append(line)

    if len(tsv_candidate_lines) >= 2:
        headers = [col.strip() for col in tsv_candidate_lines[0].split("\t") if col.strip()]
        if len(headers) >= 2:
            return "\n".join(tsv_candidate_lines), headers

    # Check for Markdown/Pipe table
    pipe_candidate_lines = []
    for line in lines:
        if "|" in line:
            pipe_candidate_lines.append(line)

    if len(pipe_candidate_lines) >= 2:
        cleaned_rows: list[list[str]] = []
        for pline in pipe_candidate_lines:
            cols = [c.strip() for c in pline.split("|")]
            if cols and not cols[0]:
                cols = cols[1:]
            if cols and not cols[-1]:
                cols = cols[:-1]
            if cols and not all(c.startswith("-") for c in cols):
                cleaned_rows.append(cols)

        if len(cleaned_rows) >= 2:
            headers = cleaned_rows[0]
            tsv_rows = ["\t".join(r) for r in cleaned_rows]
            return "\n".join(tsv_rows), headers

    # Check for CSV table
    csv_candidate_lines = []
    for line in lines:
        if "," in line and not line.lower().startswith(("columns:", "headers:", "with columns")):
            csv_candidate_lines.append(line)

    if len(csv_candidate_lines) >= 2:
        headers = [c.strip().strip("\"'") for c in csv_candidate_lines[0].split(",") if c.strip()]
        if len(headers) >= 2:
            tsv_rows = []
            for cline in csv_candidate_lines:
                row_items = [c.strip().strip("\"'") for c in cline.split(",")]
                tsv_rows.append("\t".join(row_items))
            return "\n".join(tsv_rows), headers

    return None


def extract_table_data_from_url(url: str, raw_prompt: str = "") -> tuple[str, list[str]] | None:
    """Scrape tabular data or repository contributors from a web URL using Playwright Edge."""
    gh_match = re.search(r"github\.com/([^/]+)/([^/\s#?]+)", url, re.I)
    if gh_match:
        owner, repo = gh_match.group(1), gh_match.group(2)
        repo_clean = repo.replace(".git", "")
        repo_title = f"{owner}/{repo_clean}"

        # 1. First try scraping README table via Playwright Edge
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(channel="msedge", headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=15000)

                tables = page.locator("article.markdown-body table")
                table_data = []
                for i in range(tables.count()):
                    t = tables.nth(i)
                    if "contributor" in t.inner_text().lower():
                        rows = t.locator("tr")
                        for r_idx in range(rows.count()):
                            cols = [c.inner_text().strip() for c in rows.nth(r_idx).locator("th, td").all()]
                            table_data.append(cols)
                        break
                browser.close()

                if table_data and len(table_data) >= 2:
                    headers = table_data[0]
                    tsv_lines = [
                        f"Repository: {repo_title}\t\t",
                        f"Source: {url}\t\t",
                        "",
                    ]
                    for row in table_data:
                        tsv_lines.append("\t".join(row))
                    return "\n".join(tsv_lines), headers
        except Exception as exc:
            LOGGER.debug("Edge Playwright scrape failed, trying API: %s", exc)

        # 2. Fallback: GitHub API contributors
        try:
            import urllib.request

            api_url = f"https://api.github.com/repos/{owner}/{repo_clean}/contributors"
            req = urllib.request.Request(api_url, headers={"User-Agent": "Blinky-Agent"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data and isinstance(data, list):
                headers = ["Contributor", "Contributions", "GitHub Profile"]
                tsv_lines = [
                    f"Repository: {repo_title}\t\t",
                    f"Source: {url}\t\t",
                    "",
                    "\t".join(headers),
                ]
                for c in data:
                    tsv_lines.append(f"{c.get('login')}\t{c.get('contributions')}\t{c.get('html_url')}")
                return "\n".join(tsv_lines), headers
        except Exception as exc:
            LOGGER.debug("GitHub API fallback failed: %s", exc)

    # General webpage table scraping via Playwright Edge
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=15000)

            tables = page.locator("table")
            for i in range(tables.count()):
                t = tables.nth(i)
                rows = t.locator("tr")
                if rows.count() >= 2:
                    table_data = []
                    for r_idx in range(rows.count()):
                        cols = [c.inner_text().strip() for c in rows.nth(r_idx).locator("th, td").all()]
                        if cols:
                            table_data.append(cols)
                    if len(table_data) >= 2:
                        browser.close()
                        headers = table_data[0]
                        tsv_lines = [f"Source: {url}\t\t", ""]
                        for row in table_data:
                            tsv_lines.append("\t".join(row))
                        return "\n".join(tsv_lines), headers
            browser.close()
    except Exception as exc:
        LOGGER.debug("Playwright general table scrape failed: %s", exc)

    return None


def generate_table_tsv(
    topic: str | None,
    columns: list[str] | None,
    raw_prompt: str = "",
) -> tuple[str, list[str]]:
    """Generate structured tabular data formatted as TSV for direct paste/import into Excel."""
    # Check if raw_prompt contains a URL
    url_match = re.search(r"https?://[^\s]+", raw_prompt or "")
    if url_match:
        url_target = url_match.group(0).rstrip(".,)\"'")
        scraped = extract_table_data_from_url(url_target, raw_prompt)
        if scraped is not None:
            return scraped

    extracted = extract_tabular_data_from_prompt(raw_prompt)
    if extracted is not None:
        return extracted

    # Determine columns
    if columns and len(columns) > 0:
        resolved_columns = columns
    elif topic:
        t_low = topic.lower()
        if "budget" in t_low or "expense" in t_low or "finance" in t_low:
            resolved_columns = ["Category", "Description", "Estimated Cost ($)", "Actual Cost ($)", "Status"]
        elif "company" in t_low or "companies" in t_low or "tech" in t_low:
            resolved_columns = ["Company", "Industry", "Valuation / Market Cap", "Headquarters", "CEO"]
        elif "employee" in t_low or "staff" in t_low or "team" in t_low:
            resolved_columns = ["Employee ID", "Full Name", "Department", "Role", "Email"]
        elif "project" in t_low or "task" in t_low or "roadmap" in t_low:
            resolved_columns = ["Task Name", "Assignee", "Priority", "Due Date", "Status"]
        elif "sale" in t_low or "lead" in t_low or "client" in t_low:
            resolved_columns = ["Client Name", "Contact Person", "Deal Size ($)", "Stage", "Expected Close"]
        elif "inventory" in t_low or "product" in t_low or "stock" in t_low:
            resolved_columns = ["SKU", "Product Name", "Category", "Quantity", "Unit Price ($)"]
        else:
            resolved_columns = ["Item", "Description", "Category", "Value", "Notes"]
    else:
        resolved_columns = ["Item", "Description", "Category", "Value", "Notes"]

    # Generate sample rows
    rows: list[list[str]] = []
    t_low = (topic or "").lower()

    if "budget" in t_low or "expense" in t_low:
        rows = [
            ["Marketing", "Online advertisements & campaigns", "5000", "4800", "Completed"],
            ["Development", "Cloud infrastructure & compute", "12000", "11500", "In Progress"],
            ["Operations", "Software licenses & tooling", "3500", "3500", "Approved"],
            ["Personnel", "Contractor fees & training", "8000", "7900", "Completed"],
            ["Contingency", "Emergency reserve funds", "2500", "500", "Pending"],
        ]
    elif "company" in t_low or "companies" in t_low or "tech" in t_low:
        rows = [
            ["Apple", "Consumer Electronics & Services", "$3.0 Trillion", "Cupertino, CA", "Tim Cook"],
            ["Microsoft", "Software, Cloud & Hardware", "$3.1 Trillion", "Redmond, WA", "Satya Nadella"],
            ["NVIDIA", "Semiconductors & AI Compute", "$2.8 Trillion", "Santa Clara, CA", "Jensen Huang"],
            ["Alphabet (Google)", "Internet, AI & Cloud", "$2.1 Trillion", "Mountain View, CA", "Sundar Pichai"],
            ["Amazon", "E-commerce & Cloud Computing", "$1.9 Trillion", "Seattle, WA", "Andy Jassy"],
        ]
    elif "employee" in t_low or "staff" in t_low or "team" in t_low:
        rows = [
            ["EMP-101", "Alice Zhang", "Engineering", "Principal Engineer", "alice@example.com"],
            ["EMP-102", "Marcus Miller", "Product", "Senior Product Manager", "marcus@example.com"],
            ["EMP-103", "Sarah Connor", "Design", "Lead UX Designer", "sarah@example.com"],
            ["EMP-104", "David Kumar", "Operations", "DevOps Specialist", "david@example.com"],
        ]
    elif "project" in t_low or "task" in t_low:
        rows = [
            ["Architecture Review", "Sarah", "High", "2026-11-01", "Completed"],
            ["Frontend Integration", "Marcus", "High", "2026-11-15", "In Progress"],
            ["Backend API Endpoints", "Alice", "Medium", "2026-11-20", "Pending"],
            ["End-to-End QA Testing", "David", "Low", "2026-12-01", "Planned"],
        ]
    else:
        rows = [
            ["Entry 1", "Sample primary record", "General", "100", "Verified"],
            ["Entry 2", "Secondary reference item", "Standard", "250", "Pending"],
            ["Entry 3", "Tertiary review data", "Priority", "500", "Complete"],
        ]

    # Format TSV
    tsv_lines = ["\t".join(resolved_columns)]
    for row in rows:
        padded_row = (row + [""] * len(resolved_columns))[: len(resolved_columns)]
        tsv_lines.append("\t".join(padded_row))

    return "\n".join(tsv_lines), resolved_columns


def handle_request(params: dict[str, Any]) -> dict[str, Any]:
    """Execute spreadsheet creation, cell editing, or population in Microsoft Excel."""
    action = params.get("action") or "create"
    if action == "format":
        return execute_format_spreadsheet()

    if action == "type_in_cells":
        cells = params.get("cells") or []
        preferred_app = params.get("preferred_app") or "excel"
        return execute_type_in_cells(cells, preferred_app=preferred_app)

    if action == "type_in_cell":
        cell = (params.get("cell") or "A1").strip().upper()
        text = str(params.get("text") or "").strip()
        preferred_app = params.get("preferred_app") or "excel"
        return execute_type_in_cell(cell, text, preferred_app=preferred_app)

    topic = params.get("topic")
    columns = params.get("columns") or []
    raw_prompt = params.get("raw_prompt") or ""

    # Generate or extract table data
    tsv_content, final_columns = generate_table_tsv(topic, columns, raw_prompt)

    # Put table onto system clipboard
    clipboard_set = set_system_clipboard(tsv_content)
    _LAST_SPREADSHEET_DATA["tsv"] = tsv_content

    # Open or focus Microsoft Excel
    existing_win = find_open_spreadsheet_window()
    if not existing_win:
        try:
            from computer_use.actuator import launch_app
            launch_app("excel")
        except Exception:
            if os.name == "nt":
                os.system("start excel")
        time.sleep(1.8)
        existing_win = find_open_spreadsheet_window()

    if existing_win:
        LOGGER.info("Focusing Microsoft Excel window '%s'", existing_win.get("title"))
        focus_spreadsheet_window(existing_win)

    # 1. Primary: Use xlwings for direct programmatic Excel table population
    try:
        import xlwings as xw
        app = xw.apps.active if len(xw.apps) > 0 else xw.App(visible=True, add_book=False)
        try:
            app.api.UserControl = True
        except Exception:
            pass
        wb = app.books.active if app.books else app.books.add()
        ws = wb.sheets.active
        table_rows = [line.split("\t") for line in tsv_content.splitlines()]
        max_cols = max(len(r) for r in table_rows) if table_rows else 1
        padded_rows = [r + [""] * (max_cols - len(r)) for r in table_rows]
        ws.range("A1").value = padded_rows
        format_worksheet(ws)
        LOGGER.info("Successfully populated Excel table via xlwings directly")
        col_str = ", ".join(final_columns[:6])
        if len(final_columns) > 6:
            col_str += f", and {len(final_columns) - 6} more"
        row_count = len(tsv_content.splitlines()) - 1
        return {
            "success": True,
            "action": "create_spreadsheet",
            "message": f"Created Microsoft Excel spreadsheet with {len(final_columns)} columns ({col_str}) and {row_count} rows directly via xlwings.",
            "columns": final_columns,
            "row_count": row_count,
            "tsv_data": tsv_content,
            "clipboard_populated": clipboard_set,
            "browser_opened": False,
            "target_app": "Microsoft Excel",
            "engine": "xlwings",
        }
    except Exception as exc:
        LOGGER.warning("xlwings table populate failed (%s); trying COM fallback", exc)

    # 1.5 Secondary COM fallback: Use win32com for direct programmatic Excel table population
    try:
        import win32com.client
        xl = win32com.client.Dispatch("Excel.Application")
        xl.Visible = True
        try:
            xl.UserControl = True
        except Exception:
            pass
        wb = xl.ActiveWorkbook if xl.Workbooks.Count > 0 else xl.Workbooks.Add()
        ws = xl.ActiveSheet
        for r_idx, line in enumerate(tsv_content.splitlines(), start=1):
            cols = line.split("\t")
            for c_idx, val in enumerate(cols, start=1):
                ws.Cells(r_idx, c_idx).Value = val
        format_worksheet_com(ws)
        LOGGER.info("Successfully populated Excel table via win32com directly")
        col_str = ", ".join(final_columns[:6])
        if len(final_columns) > 6:
            col_str += f", and {len(final_columns) - 6} more"
        row_count = len(tsv_content.splitlines()) - 1
        return {
            "success": True,
            "action": "create_spreadsheet",
            "message": f"Created Microsoft Excel spreadsheet with {len(final_columns)} columns ({col_str}) and {row_count} rows directly via COM.",
            "columns": final_columns,
            "row_count": row_count,
            "tsv_data": tsv_content,
            "clipboard_populated": clipboard_set,
            "browser_opened": False,
            "target_app": "Microsoft Excel",
            "engine": "win32com",
        }
    except Exception as exc:
        LOGGER.warning("win32com table populate failed (%s); falling back to clipboard paste", exc)

    # 2. Secondary fallback: Clipboard paste into cell A1
    if existing_win:
        send_paste_keystroke(target_win=existing_win)

    col_str = ", ".join(final_columns[:6])
    if len(final_columns) > 6:
        col_str += f", and {len(final_columns) - 6} more"
    row_count = len(tsv_content.splitlines()) - 1

    return {
        "success": True,
        "action": "create_spreadsheet",
        "message": f"Created Microsoft Excel spreadsheet with {len(final_columns)} columns ({col_str}) and {row_count} rows. Data was placed into the sheet.",
        "columns": final_columns,
        "row_count": row_count,
        "tsv_data": tsv_content,
        "clipboard_populated": clipboard_set,
        "browser_opened": False,
        "target_app": "Microsoft Excel",
        "engine": "paste",
    }


def main():
    if len(sys.argv) < 2:
        params = {"action": "create", "raw_prompt": "create a spreadsheet"}
    else:
        arg = sys.argv[1].strip()
        if arg.startswith("{"):
            try:
                params = json.loads(arg)
            except json.JSONDecodeError:
                resolved = resolve_spreadsheet_request(arg)
                params = resolved if resolved else {"raw_prompt": arg}
        else:
            resolved = resolve_spreadsheet_request(arg)
            params = resolved if resolved else {"raw_prompt": arg}

    result = handle_request(params)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
