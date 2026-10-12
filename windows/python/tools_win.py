from __future__ import annotations

import json
import os
import re
import subprocess
import time
from typing import Any

from utils.logging import get_logger

LOGGER = get_logger("blinky.computer_use")

from computer_use.tools import (
    ToolResult, normalize_app_name, display_app_name, SAFE_PROCESS_ALIASES,
    APP_PROTOCOLS, KNOWN_EXECUTABLE_PATHS,
)


def open_app_tool_impl(app_name: str) -> ToolResult:
    """Fast app launcher with pre-cached registry and parallel search.

    This is 3-5x faster than the old implementation:
    - Pre-scans Start Apps registry on module load (runs once in background)
    - No PowerShell subprocess per launch
    - Minimal sleep delays
    - Strategies tried in priority order (fastest first)
    """
    start_time = time.perf_counter()

    app = normalize_app_name(app_name)
    if not app:
        return ToolResult(False, "open_app", "I need an app name to open.", {})

    if os.name != "nt":
        return ToolResult(False, "open_app", "Opening desktop apps is currently supported on Windows only.", {"app_name": app})

    is_store = app == "store"

    # Store is a packaged app. Activate it through Windows' app activation API
    # and verify its visible window; do not type its name into Windows Search.
    if is_store:
        app_id = "Microsoft.WindowsStore_8wekyb3d8bbwe!App"
        try:
            process_id = _activate_app_user_model_id(app_id)
        except Exception as exc:
            LOGGER.warning("Microsoft Store activation API failed: %s", exc)
            return ToolResult(
                False,
                "open_app",
                "Microsoft Store could not be activated through Windows.",
                {"app_name": "store", "app_id": app_id, "error": str(exc)},
            )

        if not _wait_for_visible_store_window(timeout=8.0):
            return ToolResult(
                False,
                "open_app",
                "Windows accepted the Microsoft Store activation, but no visible Store window appeared.",
                {
                    "app_name": "store",
                    "app_id": app_id,
                    "process_id": process_id,
                    "launch_dispatched": True,
                    "visible_window": False,
                    "elapsed_ms": round((time.perf_counter() - start_time) * 1000, 1),
                },
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return ToolResult(
            True,
            "open_app",
            "Opened Microsoft Store.",
            {
                "app_name": "store",
                "app_id": app_id,
                "process_id": process_id,
                "method": "windows_app_activation_manager",
                "elapsed_ms": round(elapsed_ms, 1),
                "visible_window": True,
            },
        )

    # Generic apps use the fast launcher, then Windows Search as a fallback.
    try:
        from fast_app_launcher import launch_app_fast
        success, message, metadata = launch_app_fast(app, timeout=0.5)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        if success:
            # Add timing info for performance monitoring
            metadata["elapsed_ms"] = round(elapsed_ms, 1)
            LOGGER.info("Fast launcher: opened %s in %.1fms via %s", app, elapsed_ms, metadata.get("method", "unknown"))
            return ToolResult(True, "open_app", message, metadata)
        else:
            # Fast path failed, fall back to Windows Search
            LOGGER.debug("Fast launcher failed for %s after %.1fms, trying Windows Search", app, elapsed_ms)
    except Exception as exc:
        LOGGER.warning("Fast launcher threw exception for %s: %s, falling back", app, exc)

    # Fallback: Windows Search (slower but more comprehensive)
    from computer_use.tools import open_app_via_windows_search
    search_result = open_app_via_windows_search(app)
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    if search_result.success:
        search_result.details["elapsed_ms"] = round(elapsed_ms, 1)
        search_result.details["fast_launcher_failed"] = True
        LOGGER.info("Windows Search fallback: opened %s in %.1fms", app, elapsed_ms)
        return search_result

    return ToolResult(
        False,
        "open_app",
        f"I couldn't find {display_app_name(app_name, app)} installed.",
        {
            "app_name": app,
            "elapsed_ms": round(elapsed_ms, 1),
            "all_methods_failed": True
        }
    )


def _activate_app_user_model_id(app_id: str) -> int:
    """Activate a packaged Windows app without typing into Windows Search."""
    from ctypes import POINTER, c_ulong, c_wchar_p

    from comtypes import COMMETHOD, GUID, HRESULT, IUnknown
    from comtypes.client import CreateObject

    class IApplicationActivationManager(IUnknown):
        _iid_ = GUID("{2E941141-7F97-4756-BA1D-9DECDE894A3D}")
        _methods_ = [
            COMMETHOD(
                [],
                HRESULT,
                "ActivateApplication",
                (["in"], c_wchar_p, "appUserModelId"),
                (["in"], c_wchar_p, "arguments"),
                (['in'], c_ulong, "options"),
                (["out"], POINTER(c_ulong), "processId"),
            )
        ]

    manager = CreateObject(
        GUID("{45BA127D-10A8-46EA-8AB7-56EA9078943C}"),
        interface=IApplicationActivationManager,
        clsctx=4,  # CLSCTX_LOCAL_SERVER
    )
    result = manager.ActivateApplication(app_id, "", 0)
    if isinstance(result, tuple):
        result = result[-1]
    return int(result or 0)


def _wait_for_visible_store_window(timeout: float) -> bool:
    """Wait until Store has a restored, foreground, usable window."""
    deadline = time.monotonic() + max(0.0, timeout)
    while time.monotonic() < deadline:
        try:
            from computer_use.actuator import _cua_backend

            backend = _cua_backend()
            if backend is not None:
                windows = backend.list_windows()
                store_windows = [
                    window
                    for window in windows
                    if "store" in (window.title or "").lower()
                    or "store" in (window.process or "").lower()
                ]
                for window in sorted(store_windows, key=lambda item: item.width * item.height, reverse=True):
                    if not _restore_store_window(window):
                        continue
                    invalidate = getattr(backend, "_invalidate_windows_cache", None)
                    if callable(invalidate):
                        invalidate()
                    refreshed = backend.list_windows()
                    if any(
                        current.supported
                        and current.width >= 800
                        and current.height >= 500
                        and "store" in (current.title or "").lower()
                        for current in refreshed
                    ):
                        return True
        except Exception as exc:
            LOGGER.debug("Store window visibility check failed: %s", exc)
        time.sleep(0.25)
    return False


def _restore_store_window(window: Any) -> bool:
    """Restore a minimized ApplicationFrameHost HWND and confirm it is foreground."""
    try:
        import win32gui
        import win32process

        hwnd = int(window.window_id)
        if not win32gui.IsWindow(hwnd):
            return False
        win32gui.ShowWindow(hwnd, 9)  # SW_RESTORE
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.1)
        if not win32gui.IsWindowVisible(hwnd):
            return False
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        if right - left < 800 or bottom - top < 500:
            return False
        foreground = win32gui.GetForegroundWindow()
        _, foreground_pid = win32process.GetWindowThreadProcessId(foreground)
        _, target_pid = win32process.GetWindowThreadProcessId(hwnd)
        return foreground == hwnd or foreground_pid == target_pid == window.pid
    except Exception as exc:
        LOGGER.debug("Could not restore Microsoft Store window: %s", exc)
        return False


def open_app_via_windows_search_impl(app_name: str) -> ToolResult:
    if os.name != "nt":
        return ToolResult(False, "open_app", "Windows Search fallback is only available on Windows.", {"app_name": app_name})

    try:
        from pywinauto.keyboard import send_keys

        # Security: pywinauto's send_keys interprets `{...}`, `^`, `%`, `+`, `~`
        # as key/modifier syntax. Typing a raw app name could inject keystrokes.
        # Strip those metacharacters — a search query is only used for matching.
        safe_query = re.sub(r"[{}\^%~]", "", app_name).strip()
        if not safe_query:
            return ToolResult(False, "open_app", "App name contains only characters that cannot be typed safely.", {"app_name": app_name})

        send_keys("{VK_LWIN down}s{VK_LWIN up}")
        time.sleep(0.4)
        send_keys(safe_query, with_spaces=True)
        time.sleep(0.8)
        from computer_use.tools import find_windows_search_result, click_item_center
        match = find_windows_search_result(app_name)
        if match:
            click_item_center(match)
            time.sleep(1.0)
            return ToolResult(
                True,
                "open_app",
                f"Found {display_app_name(app_name, app_name)} in Windows Search and opened it.",
                {"app_name": app_name, "method": "windows_search_screen_match", "matched_text": match.get("text", "")},
            )
        send_keys("{ENTER}")
        time.sleep(1.2)
        return ToolResult(True, "open_app", f"Searched Windows and opened {display_app_name(app_name, app_name)}.", {"app_name": app_name, "method": "windows_search_enter"})
    except Exception as exc:
        LOGGER.warning("Windows Search launch failed for %s: %s", app_name, exc)
        return ToolResult(False, "open_app", f"I could not open {display_app_name(app_name, app_name)} from Windows Search.", {"app_name": app_name, "method": "windows_search_enter", "error": str(exc)})


def find_windows_search_result_impl(app_name: str) -> dict[str, Any] | None:
    try:
        from utils.matching import find_best_match
        from uia import get_visible_ui_text

        items = get_visible_ui_text(include_unlabeled=False)
        return find_best_match(app_name, items, f"Open {app_name} from the Windows Search results.")
    except Exception as exc:
        LOGGER.warning("Could not inspect Windows Search results for %s: %s", app_name, exc)
        return None


def find_start_app_impl(app_name: str) -> dict[str, Any] | None:
    safe_query = normalize_app_name(app_name)
    if not safe_query:
        return None

    command = "& { param($query); $apps = Get-StartApps | Where-Object { $_.Name -like \"*$query*\" } | Select-Object -First 1 Name,AppID; if ($apps) { $apps | ConvertTo-Json -Compress } }"
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command, f'"{safe_query}"'],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception as exc:
        LOGGER.warning("Get-StartApps lookup failed: %s", exc)
        return None

    if completed.returncode != 0 or not completed.stdout.strip():
        return None
    try:
        parsed = json.loads(completed.stdout)
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) and parsed.get("AppID") else None


def shortcut_tool_impl(shortcut: str) -> ToolResult:
    from computer_use.tools import normalize_shortcut

    normalized = normalize_shortcut(shortcut)
    if not normalized:
        return ToolResult(False, "shortcut", "I could not understand that shortcut.", {"shortcut": shortcut})
    if os.name != "nt":
        return ToolResult(False, "shortcut", "Keyboard shortcuts are currently supported on Windows only.", {"shortcut": shortcut})

    try:
        from pywinauto.keyboard import CODES, send_keys

        # Register standard virtual media keys dynamically in pywinauto
        if "VK_MEDIA_PLAY_PAUSE" not in CODES:
            CODES["VK_MEDIA_PLAY_PAUSE"] = 0xB3
        if "VK_MEDIA_STOP" not in CODES:
            CODES["VK_MEDIA_STOP"] = 0xB2
        if "VK_MEDIA_NEXT_TRACK" not in CODES:
            CODES["VK_MEDIA_NEXT_TRACK"] = 0xB0
        if "VK_MEDIA_PREV_TRACK" not in CODES:
            CODES["VK_MEDIA_PREV_TRACK"] = 0xB1

        send_keys(normalized)
        time.sleep(0.5)
        return ToolResult(True, "shortcut", f"Pressed {shortcut}.", {"shortcut": shortcut, "pywinauto_keys": normalized})
    except Exception as exc:
        return ToolResult(False, "shortcut", f"I couldn't press {shortcut}: {exc}", {"shortcut": shortcut})
