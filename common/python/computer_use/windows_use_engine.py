"""
Windows-Use Engine for Blinky.

Integrates Jeomon/Windows-Use UI Automation and agentic capabilities into Blinky.
Provides:
1. Sub-second deterministic fast paths for common compound desktop operations
   (e.g. "open notepad and create new tab and type hello world").
2. Ultra-fast LLM agent loop backed by Groq (qwen/qwen3.8-27b) or Gemini (gemini-3.8-flash)
   using native Windows UIA tree parsing with zero vision overhead.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import time
from typing import Any

LOGGER = logging.getLogger("blinky.computer_use.windows_use")

# Separator helpers
SEP_OPT = r"(?:\s*(?:and\s+then|and|then|,)\s*|\s)*"

# Keyword atoms
_NP        = r"(?:open|launch|start)\s+(?:the\s+)?notepad"   # 'open notepad'
_NP_BARE   = r"(?:the\s+)?notepad"                            # bare 'notepad'
_NP_SUFFIX = r"(?:\s+(?:app|application))?"                   # optional ' app'
_TAB       = r"(?:create|open|add)\s+(?:a\s+)?(?:new\s+)?tab" # 'create a new tab'
_WRITE     = r"(?:type|write|enter|input|put)"                 # typing verb
_TXT_SKIP  = r"(?:(?:the|some|a)\s+)?(?:text\s+|words?\s+)?"  # filler before text
_END_IT    = r"(?:\s+(?:in|into|on)\s+it)?"                   # optional 'in it'

# 1. Compound Notepad: new tab + type
# Covers: "open notepad and create a new tab and type X"
#         "notepad create new tab and write X"
#         "in notepad create a new tab then type X"
#         "create a new tab in notepad and type X"
NOTEPAD_TAB_TYPE_RES = [
    # "open notepad [sep] create [a] [new] tab [sep] type TEXT"
    re.compile(
        rf"^{_NP}{_NP_SUFFIX}{SEP_OPT}{_TAB}(?:\s+in\s+notepad)?{SEP_OPT}{_WRITE}\s+{_TXT_SKIP}(?P<text>.+?){_END_IT}$",
        re.IGNORECASE,
    ),
    # "notepad [sep] create [a] [new] tab [sep] type TEXT"
    re.compile(
        rf"^{_NP_BARE}{_NP_SUFFIX}{SEP_OPT}{_TAB}(?:\s+in\s+notepad)?{SEP_OPT}{_WRITE}\s+{_TXT_SKIP}(?P<text>.+?){_END_IT}$",
        re.IGNORECASE,
    ),
    # "in/on notepad create [a] [new] tab [sep] type TEXT"
    re.compile(
        rf"^(?:in|on)\s+notepad\s*,?\s*{_TAB}{SEP_OPT}{_WRITE}\s+{_TXT_SKIP}(?P<text>.+?){_END_IT}$",
        re.IGNORECASE,
    ),
    # "create [a] [new] tab in notepad [sep] type TEXT"
    re.compile(
        rf"^{_TAB}\s+in\s+notepad{SEP_OPT}{_WRITE}\s+{_TXT_SKIP}(?P<text>.+?){_END_IT}$",
        re.IGNORECASE,
    ),
    # "type TEXT in [a] [new] tab in notepad"
    re.compile(
        rf"^{_WRITE}\s+{_TXT_SKIP}(?P<text>.+?)\s+in\s+(?:a\s+)?(?:new\s+)?tab\s+in\s+notepad$",
        re.IGNORECASE,
    ),
    # "in notepad type TEXT in [a] [new] tab"
    re.compile(
        rf"^in\s+notepad\s*,?\s*{_WRITE}\s+{_TXT_SKIP}(?P<text>.+?)\s+in\s+(?:a\s+)?(?:new\s+)?tab$",
        re.IGNORECASE,
    ),
]

# 2. Compound Notepad: open & type directly (no new tab)
# Covers: "open notepad and type X", "in notepad type X"
NOTEPAD_TYPE_DIRECT_RES = [
    re.compile(
        rf"^{_NP}{_NP_SUFFIX}{SEP_OPT}{_WRITE}\s+{_TXT_SKIP}(?P<text>.+?){_END_IT}$",
        re.IGNORECASE,
    ),
    re.compile(
        rf"^(?:in|into)\s+notepad\s*,?\s*{_WRITE}\s+{_TXT_SKIP}(?P<text>.+?)$",
        re.IGNORECASE,
    ),
]

# 3. Notepad: open + new tab only (no typing)
# Covers: "open notepad and create a new tab", "create a new tab in notepad"
NOTEPAD_TAB_ONLY_RES = [
    re.compile(
        rf"^{_NP}{_NP_SUFFIX}{SEP_OPT}{_TAB}(?:\s+in\s+notepad)?\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        rf"^{_NP_BARE}{_NP_SUFFIX}{SEP_OPT}{_TAB}(?:\s+in\s+notepad)?\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        rf"^(?:in|on)\s+notepad\s*,?\s*{_TAB}\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        rf"^{_TAB}\s+(?:in|on)\s+notepad\s*$",
        re.IGNORECASE,
    ),
]

# 4. Open Notepad only
NOTEPAD_OPEN_ONLY_RES = [
    re.compile(rf"^{_NP}{_NP_SUFFIX}\s*$", re.IGNORECASE),
    re.compile(r"^notepad\s*$", re.IGNORECASE),
]

# 5. Generic App: new tab and type
GENERIC_APP_TAB_TYPE_RE = re.compile(
    r"^(?:open|launch|start)\s+(?:the\s+)?(?P<app>[a-zA-Z0-9 .+_-]{2,40}?)\s*(?:app|application)?"
    + SEP_OPT
    + r"(?:create|open|add)\s+(?:a\s+)?(?:new\s+)?tab"
    + SEP_OPT
    + r"(?:type|write|enter|input|put)\s+(?:(?:the|some|a)\s+)?(?:text\s+|words?\s+)?(?P<text>.+?)(?:\s+(?:in|into|on)\s+it)?$",
    re.IGNORECASE,
)


def resolve_windows_use_request(query: str) -> dict[str, Any] | None:
    """
    Fast (<1ms) query matcher to extract Windows compound desktop tasks
    without requiring LLM round-trips.
    """
    if not query or not query.strip():
        return None
    q = query.strip().rstrip("?.!,;:")

    # 1. Notepad: new tab and type
    for r in NOTEPAD_TAB_TYPE_RES:
        m = r.match(q)
        if m:
            text = m.group("text").strip().strip("'\"")
            return {
                "action": "notepad_new_tab_and_type",
                "app": "notepad",
                "text": text,
                "raw_query": query,
            }

    # 2. Notepad: open and type directly
    for r in NOTEPAD_TYPE_DIRECT_RES:
        m = r.match(q)
        if m:
            text = m.group("text").strip().strip("'\"")
            return {
                "action": "notepad_type",
                "app": "notepad",
                "text": text,
                "raw_query": query,
            }

    # 3. Notepad: new tab only
    for r in NOTEPAD_TAB_ONLY_RES:
        m = r.match(q)
        if m:
            return {
                "action": "notepad_new_tab",
                "app": "notepad",
                "text": "",
                "raw_query": query,
            }

    # 4. Notepad: open only
    for r in NOTEPAD_OPEN_ONLY_RES:
        m = r.match(q)
        if m:
            return {
                "action": "notepad_open",
                "app": "notepad",
                "text": "",
                "raw_query": query,
            }

    # 5. Generic app: new tab and type
    m5 = GENERIC_APP_TAB_TYPE_RE.match(q)
    if m5:
        app = m5.group("app").strip().lower()
        text = m5.group("text").strip().strip("'\"")
        return {
            "action": "app_new_tab_and_type",
            "app": app,
            "text": text,
            "raw_query": query,
        }

    return None


def execute_notepad_new_tab_and_type(text: str = "", new_tab: bool = True) -> dict[str, Any]:
    """
    Sub-second execution using native Windows-Use UIA:
    1. Ensures Notepad is open and brought to the foreground.
    2. Clicks the '+' New Tab button or presses Ctrl+N/Ctrl+T if requested.
    3. Finds the active text editor control (DocumentControl or EditControl).
    4. Focuses and types text directly with zero unnecessary waits.
    """
    t0 = time.perf_counter()
    import win32gui
    import windows_use.uia as uia
    from windows_use.agent.desktop.utils import escape_text_for_sendkeys

    # 1. Ensure Notepad is running and in foreground
    notepad_win = uia.WindowControl(RegexName=r"(?i).*notepad.*")
    if not notepad_win.Exists(maxSearchSeconds=0.2):
        subprocess.Popen(["notepad.exe"])
        notepad_win.Exists(maxSearchSeconds=2.5)

    if not notepad_win.Exists(maxSearchSeconds=0.8):
        return {
            "success": False,
            "message": "Could not find or launch Notepad.",
            "elapsed_ms": int((time.perf_counter() - t0) * 1000),
        }

    try:
        win32gui.SetForegroundWindow(notepad_win.NativeWindowHandle)
    except Exception:
        notepad_win.SetActive()

    # 2. Open new tab if requested: Look for '+' / 'New tab' button via UIA, fallback to Ctrl+T
    if new_tab:
        new_tab_btn = notepad_win.ButtonControl(RegexName=r"(?i).*(new tab|add tab|\+).*")
        if new_tab_btn.Exists(maxSearchSeconds=0.3):
            try:
                pattern = new_tab_btn.GetInvokePattern()
                if pattern:
                    pattern.Invoke()
                else:
                    new_tab_btn.Click(simulateMove=False, waitTime=0.05)
            except Exception:
                new_tab_btn.Click(simulateMove=False, waitTime=0.05)
        else:
            uia.SendKeys("{Ctrl}t", waitTime=0.05)

    # 3. Locate DocumentControl or EditControl
    doc = notepad_win.DocumentControl()
    if not doc.Exists(maxSearchSeconds=0.3):
        doc = notepad_win.EditControl()

    if doc.Exists(maxSearchSeconds=0.5):
        try:
            doc.SetFocus()
        except Exception:
            pass
        rect = doc.BoundingRectangle
        center = (rect.left + rect.width() // 2, rect.top + rect.height() // 2)
        if text:
            uia.Click(center[0], center[1], waitTime=0.05)
            # Send Escape first to dismiss any active Alt/AccessKey ribbon hints before typing
            uia.SendKeys("{Escape}" + escape_text_for_sendkeys(text), interval=0.005, waitTime=0.05)
    else:
        # Fallback to center of Notepad window
        rect = notepad_win.BoundingRectangle
        center = (rect.left + rect.width() // 2, rect.top + rect.height() // 2)
        if text:
            uia.Click(center[0], center[1], waitTime=0.05)
            uia.SendKeys("{Escape}" + escape_text_for_sendkeys(text), interval=0.005, waitTime=0.05)

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    if new_tab and text:
        msg = f"Opened Notepad, created a new tab, and typed '{text}'."
    elif new_tab:
        msg = "Opened Notepad and created a new tab."
    elif text:
        msg = f"Opened Notepad and typed '{text}'."
    else:
        msg = "Opened Notepad."

    LOGGER.info("%s (completed in %d ms)", msg, elapsed_ms)

    return {
        "success": True,
        "message": msg,
        "app": "notepad",
        "text": text,
        "elapsed_ms": elapsed_ms,
    }


def execute_notepad_open() -> dict[str, Any]:
    """Open Notepad and bring it to the foreground."""
    t0 = time.perf_counter()
    import win32gui
    import windows_use.uia as uia

    notepad_win = uia.WindowControl(RegexName=r"(?i).*notepad.*")
    if not notepad_win.Exists(maxSearchSeconds=0.2):
        subprocess.Popen(["notepad.exe"])
        notepad_win.Exists(maxSearchSeconds=2.5)

    if notepad_win.Exists(maxSearchSeconds=0.5):
        try:
            win32gui.SetForegroundWindow(notepad_win.NativeWindowHandle)
        except Exception:
            notepad_win.SetActive()

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    LOGGER.info("Opened Notepad. (completed in %d ms)", elapsed_ms)
    return {
        "success": True,
        "message": "Opened Notepad.",
        "app": "notepad",
        "text": "",
        "elapsed_ms": elapsed_ms,
    }


def handle_windows_use_request(params: dict[str, Any]) -> dict[str, Any]:
    """Main execution dispatcher for resolved Windows-Use requests."""
    action = params.get("action")

    if action == "notepad_new_tab_and_type":
        return execute_notepad_new_tab_and_type(params.get("text", ""), new_tab=True)

    if action == "notepad_new_tab":
        return execute_notepad_new_tab_and_type("", new_tab=True)

    if action == "notepad_type":
        return execute_notepad_new_tab_and_type(params.get("text", ""), new_tab=False)

    if action == "notepad_open":
        return execute_notepad_open()

    if action == "app_new_tab_and_type":
        app = params.get("app", "")
        if "notepad" in app:
            return execute_notepad_new_tab_and_type(params.get("text", ""), new_tab=True)

    # Generic agent fallback
    query = params.get("raw_query") or params.get("query")
    if query:
        return run_windows_use_agent_task(query)

    return {
        "success": False,
        "message": f"Unsupported Windows-Use action: {action}",
    }


def run_windows_use_agent_task(task: str) -> dict[str, Any]:
    """
    Autonomous multi-step Windows-Use Agent task loop backed by Groq or Gemini.
    """
    t0 = time.perf_counter()
    from windows_use import Agent

    llm = None
    # 1. Try Groq (fastest inference: ~300ms)
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            from windows_use.providers.groq import ChatGroq
            llm = ChatGroq(model="qwen/qwen3.8-27b", api_key=groq_key)
        except Exception as exc:
            LOGGER.debug("Could not initialize Groq for Windows-Use: %s", exc)

    # 2. Try Gemini
    if llm is None:
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if gemini_key:
            try:
                from windows_use.providers.google import ChatGoogle
                llm = ChatGoogle(model="gemini-3.8-flash", api_key=gemini_key)
            except Exception as exc:
                LOGGER.debug("Could not initialize Gemini for Windows-Use: %s", exc)

    if llm is None:
        return {
            "success": False,
            "message": "No valid LLM provider available for Windows-Use Agent.",
        }

    try:
        agent = Agent(llm=llm, max_steps=10, log_to_console=False)
        result = agent.invoke(task=task)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "success": True,
            "message": result.content or "Task completed.",
            "elapsed_ms": elapsed_ms,
        }
    except Exception as exc:
        LOGGER.exception("Windows-Use agent task failed")
        return {
            "success": False,
            "message": f"Windows-Use task failed: {exc}",
            "elapsed_ms": int((time.perf_counter() - t0) * 1000),
        }
