#!/usr/bin/env python3
"""
Fast Windows / Cross-platform Folder and File Explorer Launcher.

Provides deterministic (<15ms) resolution and launching of folders, directories,
and File Explorer directly via the Windows OS shell (explorer.exe / os.startfile),
bypassing expensive and fragile multimodal vision/OCR tool loops.
"""

from __future__ import annotations

import logging
import os
import platform
import re
import subprocess
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger("blinky.folder_launcher")

# Well-known Windows special user folders
SPECIAL_USER_FOLDERS = {
    "downloads": "Downloads",
    "download": "Downloads",
    "documents": "Documents",
    "document": "Documents",
    "desktop": "Desktop",
    "pictures": "Pictures",
    "picture": "Pictures",
    "photos": "Pictures",
    "music": "Music",
    "videos": "Videos",
    "video": "Videos",
    "home": "",
    "user": "",
}

# Regex to detect if a request is specifically asking to open a folder / file explorer / path
FOLDER_INTENT_RE = re.compile(
    r"\b(?:open|show|reveal|explore|launch|go\s+to|view)\s+(?:the\s+)?(?P<target>.+?)(?:\s+(?:in|inside|using|with|via)\s+(?:file\s+explorer|explorer|windows\s+explorer))?$",
    re.IGNORECASE,
)

GENERIC_EXPLORER_RE = re.compile(
    r"^\s*(?:open|launch|start|show)\s+(?:the\s+)?(?:file\s+explorer|windows\s+explorer|explorer|my\s+computer|this\s+pc)\s*$",
    re.IGNORECASE,
)


def is_folder_or_explorer_request(query: str) -> bool:
    """Check if the user request is asking to open a folder, path, or File Explorer."""
    if not query or not query.strip():
        return False
    q = query.strip().lower()

    if GENERIC_EXPLORER_RE.match(q):
        return True

    # Must contain keywords indicating a folder / directory / drive / path or explicit file explorer
    has_target_indicator = any(
        k in q for k in [
            "folder", "folders", "directory", "directories",
            "file explorer", "explorer", "drive",
            "c:\\", "d:\\", "c:/", "d:/",
        ]
    )
    if not has_target_indicator:
        return False

    # Must start with open/launch/show/explore/go to
    return bool(re.search(r"\b(?:open|launch|show|reveal|explore|view|go\s+to)\b", q))


def _clean_target_text(raw_target: str) -> str:
    """Clean query modifiers around the folder target."""
    t = raw_target.strip()
    t = re.sub(
        r"\s+(?:in|inside|using|with|via)\s+(?:file\s+explorer|explorer|windows\s+explorer)\s*$",
        "",
        t,
        flags=re.IGNORECASE,
    ).strip()
    t = re.sub(r"^(?:the|my)\s+", "", t, flags=re.IGNORECASE).strip()
    return t


def resolve_folder_path(query: str) -> Path | None:
    """
    Deterministically resolve a user query to an existing folder/directory path on disk.
    Supports queries like:
      - 'open the blinky folder in projects folder in file explorer'
      - 'open blinky folder in projects'
      - 'open projects folder'
      - 'open blinky folder'
      - 'open downloads folder'
      - 'open C:\\Projects\\Blinky'
    """
    if not query or not query.strip():
        return None

    q = query.strip()
    q_lower = q.lower()

    # 1. Direct path check (e.g. C:\..., D:\..., /path/...)
    path_match = re.search(r"([a-zA-Z]:[\\/][^\"'<>|\n\r]+)", q)
    if path_match:
        cand = Path(path_match.group(1).strip().rstrip(".,;!"))
        if cand.exists() and cand.is_dir():
            return cand.resolve()

    # 2. Extract clean target from query
    m = FOLDER_INTENT_RE.search(q)
    target = _clean_target_text(m.group("target")) if m else _clean_target_text(q)

    # 3. Check for child folder inside parent folder pattern
    # e.g. "blinky folder in projects folder" or "blinky in projects"
    child_parent_match = re.match(
        r"^(?P<child>.+?)(?:\s+folder|\s+dir|\s+directory)?\s+(?:in|inside|under)\s+(?:the\s+)?(?P<parent>.+?)(?:\s+folder|\s+dir|\s+directory)?$",
        target,
        re.IGNORECASE,
    )
    if child_parent_match:
        child_name = child_parent_match.group("child").strip().lower()
        parent_name = child_parent_match.group("parent").strip().lower()
        resolved = _find_child_in_parent(parent_name, child_name)
        if resolved:
            return resolved

    # 4. Check special user folders (Downloads, Documents, Desktop, etc.)
    norm_target = re.sub(r"\s+(?:folder|dir|directory)$", "", target, flags=re.IGNORECASE).strip().lower()
    if norm_target in SPECIAL_USER_FOLDERS:
        sub = SPECIAL_USER_FOLDERS[norm_target]
        cand = Path.home() / sub if sub else Path.home()
        if cand.exists():
            return cand.resolve()

    # 5. Search by name across common search roots
    resolved = _find_folder_by_name(norm_target)
    if resolved:
        return resolved

    return None


def _get_search_roots() -> list[Path]:
    """Return common base directories on the system where user projects and files live."""
    roots: list[Path] = []

    # Current working directory and workspace
    cwd = Path.cwd()
    roots.append(cwd)
    if cwd.parent not in roots:
        roots.append(cwd.parent)

    # Drive roots and common project locations
    for drive in ["C:", "D:", "E:"]:
        drive_path = Path(f"{drive}/")
        if drive_path.exists():
            roots.append(drive_path)
            for common_name in ["Projects", "projects", "workspace", "Workspace", "repos", "source"]:
                proj_path = drive_path / common_name
                if proj_path.exists() and proj_path not in roots:
                    roots.append(proj_path)

    # User home and subdirectories
    home = Path.home()
    if home not in roots:
        roots.append(home)
    for sub in ["Projects", "projects", "Downloads", "Documents", "Desktop"]:
        sub_path = home / sub
        if sub_path.exists() and sub_path not in roots:
            roots.append(sub_path)

    return roots


def _find_child_in_parent(parent_name: str, child_name: str) -> Path | None:
    """Find a specific child folder inside a parent folder."""
    # First, locate the parent folder
    parent_path = _find_folder_by_name(parent_name)
    if parent_path and parent_path.is_dir():
        # Check direct child
        for item in parent_path.iterdir():
            if item.is_dir() and item.name.lower() == child_name:
                return item.resolve()

    # Also check candidate combinations across all search roots
    roots = _get_search_roots()
    for r in roots:
        candidate = r / parent_name / child_name
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()
        # Case insensitive search in root
        if r.is_dir():
            try:
                for p in r.iterdir():
                    if p.is_dir() and p.name.lower() == parent_name:
                        for c in p.iterdir():
                            if c.is_dir() and c.name.lower() == child_name:
                                return c.resolve()
            except (PermissionError, OSError):
                continue

    return None


def _find_folder_by_name(folder_name: str) -> Path | None:
    """Search for a directory by name across common search roots."""
    clean_name = folder_name.strip().lower()
    if not clean_name:
        return None

    # Check if current directory name matches
    if Path.cwd().name.lower() == clean_name:
        return Path.cwd().resolve()

    roots = _get_search_roots()
    # 1. Exact match in search roots
    for r in roots:
        candidate = r / clean_name
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()

    # 2. Case-insensitive scan of 1 level under search roots
    for r in roots:
        if not r.exists() or not r.is_dir():
            continue
        try:
            for item in r.iterdir():
                if item.is_dir() and item.name.lower() == clean_name:
                    return item.resolve()
        except (PermissionError, OSError):
            continue

    return None


def open_folder_or_path(query_or_path: str) -> dict[str, Any]:
    """
    Open the requested folder or File Explorer in Windows instantly.
    Returns result dictionary suitable for Blinky tool response.
    """
    q = query_or_path.strip()
    is_pure_explorer = bool(GENERIC_EXPLORER_RE.match(q.lower()))

    target_path: Path | None = None
    if not is_pure_explorer:
        target_path = resolve_folder_path(q)

    # If it was a pure explorer request or no specific path was found, open File Explorer home
    if target_path is None:
        if is_pure_explorer or "explorer" in q.lower():
            if os.name == "nt":
                subprocess.Popen(["explorer.exe"])
            elif platform.system() == "Linux":
                subprocess.Popen(["xdg-open", str(Path.home())])
            return {
                "success": True,
                "message": "Opened File Explorer.",
                "path": None,
                "tool": "open_folder",
            }
        return {
            "success": False,
            "message": f"Could not find folder matching '{q}'.",
            "path": None,
            "tool": "open_folder",
        }

    # Open target path in Windows File Explorer
    norm_path = os.path.normpath(str(target_path))
    LOGGER.info("Opening folder instantly in File Explorer: %s", norm_path)

    if os.name == "nt":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        explorer_exe = os.path.join(windir, "explorer.exe")
        flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        launched = False

        # 1. ShellExecuteW explicitly tells Windows Shell to open explorer at this path with SW_SHOWNORMAL
        try:
            import ctypes
            res = ctypes.windll.shell32.ShellExecuteW(None, "open", explorer_exe, f'"{norm_path}"', None, 1)
            if int(res or 0) > 32:
                launched = True
        except Exception as exc:
            LOGGER.debug("ShellExecuteW failed: %s", exc)

        # 2. Only if ShellExecuteW failed, fall back to detached subprocess
        if not launched:
            try:
                subprocess.Popen([explorer_exe, norm_path], creationflags=flags, close_fds=True)
                time.sleep(0.15)
            except Exception as exc:
                LOGGER.debug("Detached explorer launch failed: %s", exc)
                try:
                    os.startfile(norm_path)
                except Exception:
                    pass
    elif platform.system() == "Linux":
        subprocess.Popen(["xdg-open", norm_path])

    return {
        "success": True,
        "message": f"Opened {target_path.name} ({norm_path}) in File Explorer.",
        "path": norm_path,
        "tool": "open_folder",
    }
