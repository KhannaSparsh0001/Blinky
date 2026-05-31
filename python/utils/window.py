from __future__ import annotations

import psutil

from utils.logging import get_logger

LOGGER = get_logger("clicky.window")

SUPPORTED_PROCESSES = {
    "code.exe",
    "chrome.exe",
    "mspaint.exe",
    "explorer.exe",
    "antigravity ide.exe",
    "antigravity-ide.exe",
}



def get_target_window_element(window=None, target_pid: int | None = None):
    """Retrieve the first visible top-level window in Z-order that is NOT Slicky itself
    or a Windows system shell.

    *window* — pass a pre-resolved pywinauto element to skip Z-order scanning entirely.
    *target_pid* — pass a process ID to restrict the Z-order scan to that process.
               This is preferred over *window* for long-lived calls because a
               pywinauto COM element can go stale after ~15 s while the PID stays
               valid as long as the process is alive.
    """
    if window is not None:
        return window

    try:
        from pywinauto import Desktop
        
        windows = Desktop(backend="uia").windows()
        for w in windows:
            try:
                if not w.is_visible():
                    continue
                title = w.window_text()
                if not title or not title.strip():
                    continue
                
                # Fetch process info
                process_id = w.process_id()

                # If caller locked a specific PID, only match that process
                if target_pid is not None and process_id != target_pid:
                    continue

                process_name = psutil.Process(process_id).name().lower()
                
                # Exclude Slicky, Tauri, or prompt bars
                if "clicky" in process_name or "tauri" in process_name or "slicky" in title.lower():
                    continue
                
                # Exclude Windows system shells and background services
                if process_name in {
                    "searchhost.exe",
                    "shellexperiencehost.exe",
                    "startmenuexperiencehost.exe",
                    "lockapp.exe",
                    "systemsettings.exe"
                }:
                    continue
                
                # Exclude Taskbar, desktop manager, and OS settings screens
                if title in {"Taskbar", "Program Manager", "Settings", "Action Center"}:
                    continue
                    
                if process_name == "explorer.exe" and title in {"Taskbar", "Program Manager", "FolderView"}:
                    continue
                    
                LOGGER.info("Detected target application window: %s (%s)", title, process_name)
                return w
            except Exception:
                continue
    except Exception as exc:
        LOGGER.warning("Failed to scan Z-order windows: %s", exc)
        
    # Fallback to standard get_active() if custom resolution fails
    try:
        from pywinauto import Desktop
        return Desktop(backend="uia").get_active()
    except Exception:
        return None



def get_active_window(window=None, target_pid: int | None = None) -> dict:
    try:
        w = get_target_window_element(window=window, target_pid=target_pid)
        if not w:
            raise RuntimeError("No active target window resolved.")

        process_id = w.process_id()
        process_name = psutil.Process(process_id).name()
        title = w.window_text()
        return {
            "title": title,
            "process": process_name,
            "supported": process_name.lower() in SUPPORTED_PROCESSES,
        }
    except Exception as exc:
        LOGGER.warning("Could not inspect active window: %s", exc)
        return {"title": "Unknown window", "process": "unknown", "supported": False}

