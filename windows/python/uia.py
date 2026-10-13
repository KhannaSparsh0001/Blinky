from __future__ import annotations

import time

from utils.logging import get_logger

LOGGER = get_logger("blinky.uia")


def get_visible_ui_text(window=None, target_pid: int | None = None, include_unlabeled: bool = False) -> list[dict]:
    """Read visible UI Automation text from the active window.

    *window* — optional pre-resolved pywinauto element (skips Z-order scan).
    *target_pid* — preferred: restrict the Z-order scan to this process ID so
               that focus changes during the OCR phase don't affect which window
               is scanned. A fresh COM element is resolved each call, avoiding
               the stale-descriptor bug that occurs when an element is cached
               for > ~15 s.

    Windows UI Automation returns element bounding rectangles in
    screen-absolute coordinates (logical pixels). These are in the same space
    as the overlay window and match the screenshot after the scaleX/scaleY
    transform applied in Overlay.tsx.
    """
    import os
    if os.name != "nt":
        return []

    try:
        from utils.window import get_target_window_element

        active = get_target_window_element(window=window, target_pid=target_pid)
        if not active:
            LOGGER.warning("No target window resolved for UIA query")
            return []

        active_y = 0
        try:
            active_y = active.rectangle().top
        except Exception as exc:
            LOGGER.warning("UIA: failed to resolve active window top coordinate: %s", exc)

        process_name = ""
        try:
            import psutil
            process_name = psutil.Process(active.process_id()).name().lower()
            LOGGER.info("UIA: active process = '%s'", process_name)
        except Exception as exc:
            LOGGER.warning("UIA: failed to resolve process name: %s", exc)

        active_title = ""
        try:
            active_title = (active.window_text() or "").lower().strip()
        except Exception:
            pass

        # Known desktop applications are never ignored overlays
        is_known_app = any(app in process_name for app in ["antigravity", "code", "chrome", "msedge", "firefox", "brave", "opera", "notepad", "terminal"])
        if not is_known_app:
            if any(p in process_name for p in ["wispr", "whisper", "raycast", "blinky", "tauri"]) or any(
                hint in active_title for hint in ["wispr flow", "whisper flow"]
            ) or active_title in {"status", "raycast", "recording toolbar", "blinky highlight overlay"}:
                LOGGER.info(
                    "UIA: Skipping scan for ignored overlay process/window '%s' (title: '%s')",
                    process_name,
                    active_title,
                )
                return []

        # Restrict traversal to interactive control types to prune layout panels
        # and wrappers. Speeds up UIA tree scanning ~50x.
        ALLOWED_CONTROL_TYPES = {
            "Button",
            "TabItem",
            "MenuItem",
            "TreeItem",
            "Edit",
            "Hyperlink",
            "ListItem",
            "HeaderItem",
            "Custom",
            "Image",
            "Pane",
        }

        items: list[dict] = []
        start_time = time.perf_counter()
        UIA_TIME_BUDGET_SECONDS = 2.0
        MAX_ITEMS = 250
        pid_cache: dict[int, str] = {}
        active_pid = None
        try:
            active_pid = active.process_id()
        except Exception:
            pass

        for element in active.descendants():
            if time.perf_counter() - start_time > UIA_TIME_BUDGET_SECONDS:
                LOGGER.info(
                    "UIA: Traversal time budget exceeded (%.1fs), stopping scan early to prevent window hang",
                    UIA_TIME_BUDGET_SECONDS,
                )
                break
            if len(items) >= MAX_ITEMS:
                LOGGER.info("UIA: Traversal capped at %d items to prevent massive tree scanning", MAX_ITEMS)
                break
                
            try:
                ctype = element.element_info.control_type
                if ctype not in ALLOWED_CONTROL_TYPES:
                    continue
            except Exception:
                continue

            try:
                elem_pid = element.element_info.process_id
                if elem_pid and active_pid and elem_pid != active_pid:
                    if elem_pid not in pid_cache:
                        import psutil
                        try:
                            pid_cache[elem_pid] = psutil.Process(elem_pid).name().lower()
                        except Exception:
                            pid_cache[elem_pid] = ""
                    elem_pname = pid_cache[elem_pid]
                    if not any(app in elem_pname for app in ["antigravity", "code", "chrome", "msedge", "firefox", "brave", "opera", "notepad", "terminal"]):
                        if any(p in elem_pname for p in ["wispr", "whisper", "raycast", "blinky", "tauri"]):
                            continue
            except Exception:
                pass

            text = _element_text(element, ctype)
            if not text and not (include_unlabeled and ctype in {"Button", "Image", "Hyperlink"}):
                continue

            try:
                if not element.is_visible():
                    continue
            except Exception:
                pass

            rect = element.rectangle()
            width = max(0, int(rect.width()))
            height = max(0, int(rect.height()))
            if width < 4 or height < 4:
                continue

            # Skip elements with clearly invalid coordinates (off-screen)
            x = int(rect.left)
            y = int(rect.top)
            if x < -1000 or y < -1000:
                continue

            auto_id = _element_metadata(element, "automation_id")
            
            # Check if this element is browser chrome (address/URL bar)
            is_address_bar = False
            if process_name and any(b in process_name for b in ["chrome", "msedge", "firefox", "browser", "brave", "opera"]):
                relative_y = y - active_y
                if relative_y < 130:
                    is_address_bar = True
            
            auto_id_lower = auto_id.lower()
            if "address" in auto_id_lower or "url" in auto_id_lower or "omnibox" in auto_id_lower or auto_id_lower in {"view_1021", "view_1020"}:
                is_address_bar = True

            items.append(
                _uia_item(
                    text=text,
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    source="uia",
                    control_type=ctype,
                    automation_id=auto_id,
                    is_address_bar=is_address_bar,
                )
            )

        # Capture Blinky's own settings button in its floating window header!
        try:
            from pywinauto import Desktop
            for w in Desktop(backend="uia").windows():
                pname = ""
                try:
                    import psutil
                    pname = psutil.Process(w.process_id()).name().lower()
                except Exception:
                    pass
                if "blinky" in pname or "blinky" in (w.window_text() or "").lower():
                    for el in w.descendants():
                        try:
                            if el.element_info.control_type not in {"Button", "Image", "Pane"}:
                                continue
                            text = _element_text(el, el.element_info.control_type)
                            if not text or "settings" not in text.lower():
                                continue
                            if not el.is_visible():
                                continue
                            rect = el.rectangle()
                            width = max(0, int(rect.width()))
                            height = max(0, int(rect.height()))
                            if width < 4 or height < 4:
                                continue
                            x = int(rect.left)
                            y = int(rect.top)
                            items.append(_uia_item(
                                text=text,
                                x=x,
                                y=y,
                                width=width,
                                height=height,
                                source="blinky",
                                control_type=el.element_info.control_type,
                                automation_id=_element_metadata(el, "automation_id"),
                            ))
                            LOGGER.info("UIA: Captured Blinky control element '%s' at (%d, %d)", text, x, y)
                            break
                        except Exception:
                            continue
                    break
        except Exception as exc:
            LOGGER.warning("UIA: failed to scan Blinky window controls: %s", exc)

        # Debug: log sidebar-region elements only when verbose logging is enabled.
        sidebar_items = [i for i in items if i["x"] <= 100]
        LOGGER.debug(
            "UIA: %d sidebar-region elements (x<=100) out of %d total",
            len(sidebar_items), len(items),
        )
        for si in sidebar_items[:15]:
            LOGGER.debug(
                "UIA sidebar: %-60s  x=%d y=%d w=%d h=%d",
                repr(si["text"][:55]), si["x"], si["y"], si["width"], si["height"],
            )

        LOGGER.info("UI Automation returned %d visible text items total", len(items))
        return _dedupe(items)

    except Exception as exc:
        LOGGER.warning("UI Automation text extraction failed: %s", exc)
        return []


def get_shell_ui_items() -> list[dict]:
    """Read taskbar buttons and desktop icon labels outside the active window.

    The active-window scan (:func:`get_visible_ui_text`) cannot see the
    Windows shell: taskbar pins (e.g. Edge) live under ``Shell_TrayWnd``
    and desktop icons (e.g. Steam) under the Progman/WorkerW FolderView.
    Items are tagged with ``shell_region`` = ``"taskbar"`` | ``"desktop"``
    and use screen-absolute coordinates like the main UIA scan, so callers
    must apply the same screenshot-space scaling.
    """
    import os
    if os.name != "nt":
        return []

    items: list[dict] = []
    try:
        from pywinauto import Desktop
    except Exception as exc:
        LOGGER.warning("Shell UIA scan skipped (no pywinauto): %s", exc)
        return []

    try:
        desktop = Desktop(backend="uia")
    except Exception as exc:
        LOGGER.warning("Shell UIA scan skipped (no desktop): %s", exc)
        return []

    for spec, region in _shell_scopes(desktop):
        if region == "desktop" and sum(1 for i in items if i.get("shell_region") == "desktop") >= 10:
            continue  # Progman already gave us the desktop icons; skip WorkerW.
        try:
            items.extend(_scan_shell_scope(spec, region))
        except Exception as exc:
            LOGGER.debug("Shell UIA scope '%s' failed: %s", region, exc)
    LOGGER.info("Shell UIA returned %d taskbar/desktop items", len(items))
    return _dedupe(items)


def _shell_scopes(desktop):
    scopes = []
    try:
        scopes.append((desktop.window(class_name="Shell_TrayWnd"), "taskbar"))
    except Exception:
        pass
    for cls in ("Progman", "WorkerW"):
        try:
            scopes.append((desktop.window(class_name=cls), "desktop"))
        except Exception:
            continue
    return scopes


def _scan_shell_scope(scope, region: str) -> list[dict]:
    items: list[dict] = []
    start_time = time.perf_counter()
    budget = 0.8
    count = 0
    try:
        roots = [scope] + list(scope.descendants())
    except Exception:
        return []
    for element in roots:
        if time.perf_counter() - start_time > budget or count >= 120:
            break
        try:
            ctype = element.element_info.control_type
        except Exception:
            continue
        if ctype not in {"Button", "ListItem", "TreeItem", "MenuItem", "Image", "Custom", "Hyperlink", "Pane"}:
            continue
        text = _element_text(element, ctype)
        if not text:
            continue
        try:
            rect = element.rectangle()
        except Exception:
            continue
        width = max(0, int(rect.width()))
        height = max(0, int(rect.height()))
        if width < 4 or height < 4:
            continue
        x, y = int(rect.left), int(rect.top)
        if x < -1000 or y < -1000:
            continue
        # Desktop FolderView exposes huge folder panes; keep icon-sized rows.
        if region == "desktop" and (width > 400 or height > 200):
            continue
        item = _uia_item(
            text=text,
            x=x,
            y=y,
            width=width,
            height=height,
            source="uia",
            control_type=ctype,
            automation_id=_element_metadata(element, "automation_id"),
        )
        item["shell_region"] = region
        items.append(item)
        count += 1
    return items


def _element_text(element, control_type: str = "") -> str:
    try:
        name = element.window_text() or element.element_info.name or ""
        help_text = ""
        try:
            help_text = element.element_info.help_text or ""
        except Exception:
            pass
        automation_id = _element_metadata(element, "automation_id")
        # Prefer help_text (tooltip/accessible description) when available.
        text = help_text if help_text.strip() else name
        if not str(text).strip() and control_type in {"Button", "MenuItem", "TabItem", "TreeItem", "Hyperlink", "Edit", "Image"}:
            text = automation_id
    except Exception:
        return ""
    return _readable_metadata_text(str(text))


def _uia_item(
    *,
    text: str,
    x: int,
    y: int,
    width: int,
    height: int,
    source: str,
    control_type: str,
    automation_id: str = "",
    is_address_bar: bool = False,
) -> dict:
    item = {
        "text": text,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "source": source,
        "control_type": control_type,
    }
    if automation_id:
        item["automation_id"] = automation_id
    if is_address_bar:
        item["is_address_bar"] = True
    return item


def _element_metadata(element, field: str) -> str:
    try:
        value = getattr(element.element_info, field, "") or ""
    except Exception:
        return ""
    return str(value).strip()


def _readable_metadata_text(value: str) -> str:
    import re

    text = re.sub(r"[_\-]+", " ", value)
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    return " ".join(text.strip().split())


def _dedupe(items: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    unique: list[dict] = []
    for item in items:
        key = (item["text"].lower(), item["x"], item["y"], item["width"], item["height"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique
