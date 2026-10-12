from __future__ import annotations

import os
import psutil
from utils.logging import get_logger

LOGGER = get_logger("blinky.window")

SUPPORTED_PROCESSES = {
    "code.exe",
    "code",
    "chrome.exe",
    "chrome",
    "google-chrome",
    "google-chrome.exe",
    "mspaint.exe",
    "mspaint",
    "explorer.exe",
    "explorer",
    "antigravity ide.exe",
    "antigravity-ide.exe",
    "antigravity ide",
    "antigravity-ide",
    "systemsettings.exe",
    "systemsettings",
    "settings.exe",
    "settings",
}

IGNORED_OVERLAY_PROCESSES = {
    "snippingtool.exe",
    "nvidia overlay.exe",
    "nvidiaoverlay.exe",
    "trae.exe",
    "blinky.exe",
    "nvsphelper64.exe",
    "nvcontainer.exe",
    "wispr flow.exe",
    "wisprflow.exe",
    "wispr.exe",
    "whisper flow.exe",
    "whisperflow.exe",
    "whisper.exe",
    "raycast.exe",
    "raycast",
}

IGNORED_OVERLAY_TITLE_HINTS = {
    "recording toolbar",
    "blinky highlight overlay",
    "status",
    "raycast",
    "wispr flow",
    "whisper flow",
}


def is_process_supported(process_name: str) -> bool:
    name_lower = process_name.lower()
    if name_lower in SUPPORTED_PROCESSES:
        return True
    base_name = name_lower.rsplit('.', 1)[0]
    if base_name in SUPPORTED_PROCESSES:
        return True
    return False


def is_ignored_overlay_window(process_name: str, title: str) -> bool:
    name_lower = process_name.lower().strip()
    title_lower = title.lower().strip()

    # Known desktop applications (IDEs, editors, browsers, terminals) are never overlays
    if any(app in name_lower for app in ["antigravity", "code", "chrome", "msedge", "firefox", "brave", "opera", "notepad", "terminal"]):
        return False

    if name_lower in IGNORED_OVERLAY_PROCESSES:
        return True
    if any(p in name_lower for p in ["wispr", "whisper", "raycast", "blinky", "tauri"]):
        return True
    if name_lower in {"flow.exe"} and ("status" in title_lower or "wispr" in title_lower or not title_lower):
        return True
    if title_lower in {"recording toolbar", "blinky highlight overlay", "status", "raycast"}:
        return True
    return any(hint in title_lower for hint in ["wispr flow", "whisper flow"])


_local_ignored_rects: list[dict[str, int]] = []


def set_ignored_overlay_rects(rects: list[dict]) -> None:
    global _local_ignored_rects
    _local_ignored_rects = []
    if not rects:
        return
    for r in rects:
        if not isinstance(r, dict):
            continue
        x = r.get("x")
        y = r.get("y")
        w = r.get("width")
        h = r.get("height")
        if x is not None and y is not None and w is not None and h is not None:
            _local_ignored_rects.append({
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h),
            })


def get_ignored_overlay_rects() -> list[dict[str, int]]:
    if os.name != "nt":
        return _local_ignored_rects

    rects: list[dict[str, int]] = []
    try:
        from pywinauto import Desktop
        import ctypes
        user32 = ctypes.windll.user32
        screen_w = user32.GetSystemMetrics(0) or 1920
        screen_h = user32.GetSystemMetrics(1) or 1080

        for w in Desktop(backend="uia").windows():
            try:
                if not w.is_visible():
                    continue
                title = w.window_text()
                # Skip fullscreen or transparent overlay windows to prevent filtering out all elements on the screen
                if "highlight overlay" in title.lower() or "cursoroverlay" in title.lower():
                    continue
                process_name = psutil.Process(w.process_id()).name().lower()
                if not is_ignored_overlay_window(process_name, title):
                    continue
                rect = w.rectangle()
                rw = max(0, int(rect.width()))
                rh = max(0, int(rect.height()))

                # CRITICAL GUARD: Never include fullscreen or large overlays as ignored rects!
                # Fullscreen overlays (NVIDIA overlay, CUA cursor overlay, Blinky highlight overlay)
                # are transparent click-through layers. If added to ignored rects, they mask out 100%
                # of all UI elements on the entire screen!
                if rw >= int(screen_w * 0.7) and rh >= int(screen_h * 0.7):
                    continue
                if rw * rh >= int(screen_w * screen_h * 0.5):
                    continue
                # Skip tiny zero/dummy windows (e.g. 1x1 hook windows)
                if rw < 10 or rh < 10:
                    continue

                rects.append(
                    {
                        "x": int(rect.left),
                        "y": int(rect.top),
                        "width": rw,
                        "height": rh,
                    }
                )
            except Exception:
                continue
    except Exception as exc:
        LOGGER.warning("Failed to scan ignored overlay windows: %s", exc)
    return rects


def get_target_window_element(window=None, target_pid: int | None = None):
    if os.name != "nt":
        # Linux: return a lightweight window descriptor (hyprctl-backed).
        # Keeps the same call contract (`.process_id()` used by main.py) via a
        # tiny adapter; window/target_pid args are ignored on Linux.
        try:
            from backend.window import get_active_window

            info = get_active_window()
            if info is not None:
                return _LinuxWindowAdapter(info)
        except ImportError:
            pass
        return None
    try:
        from window import _get_target_window_element_impl
        return _get_target_window_element_impl(window, target_pid)
    except ImportError:
        return None


class _LinuxWindowAdapter:
    """Minimal adapter exposing process_id() over backend WindowInfo."""

    def __init__(self, info):
        self._info = info

    def process_id(self):
        return self._info.pid or 0


def get_active_window(window=None, target_pid: int | None = None) -> dict:
    if os.name == "nt":
        return _get_active_window_win(window, target_pid)
    else:
        return _get_active_window_linux()


def _get_active_window_win(window=None, target_pid: int | None = None) -> dict:
    try:
        from window import _get_target_window_element_impl
        w = _get_target_window_element_impl(window=window, target_pid=target_pid)
        if not w:
            raise RuntimeError("No active target window resolved.")

        process_id = w.process_id()
        process_name = psutil.Process(process_id).name()
        title = w.window_text()
        return {
            "title": title,
            "process": process_name,
            "supported": is_process_supported(process_name),
        }
    except Exception as exc:
        LOGGER.warning("Could not inspect active window on Windows: %s", exc)
        return {"title": "Unknown window", "process": "unknown", "supported": False}


def _get_active_window_linux() -> dict:
    # New compositor backend (Hyprland-first; GNOME/KDE land in phase 8)
    try:
        from backend.window import get_active_window

        info = get_active_window()
        if info is not None:
            return {
                "title": info.title,
                "process": info.process,
                "supported": info.supported,
            }
    except ImportError:
        pass

    # Fallback: legacy KWin/xdotool/xprop chain (kept until phase 7 cleanup)
    try:
        from backend.vision import get_active_window_bounds

        bounds = get_active_window_bounds()
        if bounds:
            return {
                "title": bounds.get("title", ""),
                "process": str(bounds.get("app_id", "")).split(".")[-1],
                "supported": True,
            }
    except ImportError:
        pass

    session = os.environ.get("XDG_SESSION_TYPE", "wayland").lower()
    return {
        "title": "Linux Desktop",
        "process": session,
        "supported": False,
    }
