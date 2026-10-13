"""Merge generic icon-detector boxes with nearby OCR text.

The open-source icon model (see :mod:`ocr.icon_detect`) finds the picture
part of an icon but has no text. Desktop icons carry their label *below*
the picture ("Steam" under the Steam logo); taskbar / sidebar icons usually
have no visible label at all.

``merge_icon_boxes()`` produces highlight-ready items:

* icon + nearby label  -> single item covering the **full icon + text**
  (``text`` = label, ``source`` = ``"icon"``), consuming the standalone
  OCR label so the matcher does not see duplicates;
* icon without a label -> kept as a textless icon item (gets a
  ``"Visible Image N"`` handle later in
  :func:`utils.screen_elements.assign_screen_element_refs`, which the
  vision model can identify from the screenshot).
"""

from __future__ import annotations

from typing import Any


def desktop_grid_bounds(screenshot) -> tuple[int, int, int] | None:
    """(right_edge, bottom_edge, max_icon_px) of the desktop icon grid."""
    try:
        width = int(screenshot.width or 0)
        height = int(screenshot.height or 0)
    except (TypeError, ValueError):
        return None
    if width <= 0 or height <= 0:
        return None
    return (max(int(width * 0.35), 420), int(height * 0.92), 120)


def _in_desktop_grid(icon: dict[str, Any], bounds: tuple[int, int, int] | None) -> bool:
    if bounds is None:
        return True
    right_edge, bottom_edge, max_px = bounds
    try:
        width = int(icon.get("width", 0))
        height = int(icon.get("height", 0))
    except (TypeError, ValueError):
        return False
    return (
        int(icon.get("x", 0)) <= right_edge
        and int(icon.get("y", 0)) + height <= bottom_edge
        and 24 <= width <= max_px
        and 24 <= height <= max_px
    )


def merge_icon_boxes(
    visible_items: list[dict[str, Any]],
    icon_boxes: list[dict[str, Any]],
    screenshot=None,
) -> list[dict[str, Any]]:
    """Fuse icon boxes with OCR labels; keep labelless icons as-is.

    Fusing only happens inside the desktop icon grid (when *screenshot*
    dimensions are given): the open-source detector also fires on web-page
    thumbnails and video controls, and joining those with nearby page text
    produces nonsense items. Outside the grid, icons stay textless and are
    matched via shell UIA text or vision fallback instead.
    """
    if not icon_boxes:
        return list(visible_items)

    bounds = desktop_grid_bounds(screenshot) if screenshot is not None else None
    ocr_candidates = [
        item for item in visible_items if str(item.get("source", "")).lower() in {"ocr", "winrt"}
    ]
    consumed: set[int] = set()
    merged: list[dict[str, Any]] = []

    for icon in icon_boxes:
        label_idx = None
        if _in_desktop_grid(icon, bounds):
            label_idx = _find_label_below(icon, ocr_candidates, consumed)
            if label_idx is None:
                label_idx = _find_label_overlapping(icon, ocr_candidates, consumed)
        if label_idx is not None:
            consumed.add(label_idx)
            label = ocr_candidates[label_idx]
            merged.append(_fuse(icon, label))
        else:
            merged.append({**icon, "control_type": icon.get("control_type") or "Image"})

    kept = [item for idx, item in enumerate(visible_items) if idx not in _consumed_visible_ids(visible_items, ocr_candidates, consumed)]
    return [*kept, *merged]


def _consumed_visible_ids(
    visible_items: list[dict[str, Any]],
    ocr_candidates: list[dict[str, Any]],
    consumed: set[int],
) -> set[int]:
    ids: set[int] = set()
    for cand_idx in consumed:
        target = ocr_candidates[cand_idx]
        for vis_idx, item in enumerate(visible_items):
            if item is target:
                ids.add(vis_idx)
                break
    return ids


def _find_label_below(
    icon: dict[str, Any],
    ocr_candidates: list[dict[str, Any]],
    consumed: set[int],
) -> int | None:
    """Desktop pattern: label line sits just below the icon picture."""
    ix = float(icon.get("x") or 0)
    iy = float(icon.get("y") or 0)
    iw = float(icon.get("width") or 0)
    ih = float(icon.get("height") or 0)
    if iw <= 0 or ih <= 0:
        return None
    icon_cx = ix + iw / 2
    icon_bottom = iy + ih

    best_idx: int | None = None
    best_score = 0.0
    for idx, cand in enumerate(ocr_candidates):
        if idx in consumed:
            continue
        text = str(cand.get("text", "")).strip()
        if not text or len(text) > 20:
            continue
        cx = float(cand.get("x") or 0)
        cy = float(cand.get("y") or 0)
        cw = float(cand.get("width") or 0)
        ch = float(cand.get("height") or 0)
        if cw <= 0 or ch <= 0:
            continue
        gap = cy - icon_bottom
        # Label must belong to THIS icon's row: desktop rows sit ~100px
        # apart, so a wide window would steal the next row's label when
        # the icon's own label is missing from OCR (e.g. Steam <- Human).
        # The label may start slightly inside tall picture boxes, so allow
        # modest overlap proportional to the icon height.
        if gap < -(ch + ih * 0.15) or gap > max(28.0, ih * 0.4):
            continue
        cand_cx = cx + cw / 2
        # Horizontally centered under the icon (desktop grid tolerance).
        if abs(cand_cx - icon_cx) > max(iw * 0.9, 40):
            continue
        # Prefer the closest line; slight preference for wider (full) labels.
        score = 1.0 / (1.0 + abs(gap)) + min(cw / 200.0, 0.2)
        if score > best_score:
            best_score = score
            best_idx = idx
    return best_idx


def _find_label_overlapping(
    icon: dict[str, Any],
    ocr_candidates: list[dict[str, Any]],
    consumed: set[int],
) -> int | None:
    """Fallback: OCR text whose center falls inside the icon box."""
    ix = float(icon.get("x") or 0)
    iy = float(icon.get("y") or 0)
    iw = float(icon.get("width") or 0)
    ih = float(icon.get("height") or 0)
    best_idx: int | None = None
    best_area = -1.0
    for idx, cand in enumerate(ocr_candidates):
        if idx in consumed:
            continue
        text = str(cand.get("text", "")).strip()
        if not text:
            continue
        cx = float(cand.get("x") or 0) + float(cand.get("width") or 0) / 2
        cy = float(cand.get("y") or 0) + float(cand.get("height") or 0) / 2
        if ix <= cx <= ix + iw and iy <= cy <= iy + ih:
            area = float(cand.get("width") or 0) * float(cand.get("height") or 0)
            if area > best_area:
                best_area = area
                best_idx = idx
    return best_idx


def _fuse(icon: dict[str, Any], label: dict[str, Any]) -> dict[str, Any]:
    """Union box of icon picture + text label, keyed by the label text."""
    x1 = min(int(icon.get("x") or 0), int(label.get("x") or 0))
    y1 = min(int(icon.get("y") or 0), int(label.get("y") or 0))
    x2 = max(
        int(icon.get("x") or 0) + int(icon.get("width") or 0),
        int(label.get("x") or 0) + int(label.get("width") or 0),
    )
    y2 = max(
        int(icon.get("y") or 0) + int(icon.get("height") or 0),
        int(label.get("y") or 0) + int(label.get("height") or 0),
    )
    confidence = max(float(icon.get("confidence") or 0), float(label.get("confidence") or 0))
    return {
        "text": str(label.get("text", "")).strip(),
        "x": x1,
        "y": y1,
        "width": max(1, x2 - x1),
        "height": max(1, y2 - y1),
        "confidence": confidence,
        "source": "icon",
        "control_type": "Image",
        "clickable": True,
        "icon_box": {
            "x": icon.get("x"),
            "y": icon.get("y"),
            "width": icon.get("width"),
            "height": icon.get("height"),
        },
    }
