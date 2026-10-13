"""Open-source icon detector for Blinky screen grounding.

Uses the Microsoft OmniParser icon-detection weights
(`weights/omniparser/icon_detect/model.onnx`, YOLO11m exported to ONNX)
at runtime via `onnxruntime` only — no `ultralytics`/`torch` needed.

The detector returns generic icon boxes (no text). Callers merge these
with nearby OCR text (see :mod:`utils.icon_text_merge`) so highlights
cover the full icon + its label, e.g. desktop `Steam` or taskbar `Edge`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from utils.logging import get_logger

LOGGER = get_logger("blinky.ocr.icon_detect")

# NOTE: onnxruntime MUST be imported eagerly here (not lazily inside a
# function). Its native DLL fails to initialize if WinRT OCR's native
# libraries are loaded first ("DLL initialization routine failed"), so the
# import has to win the race at process startup, long before any OCR call.
try:
    import onnxruntime  # noqa: F401
    _ORT_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - environment dependent
    onnxruntime = None  # type: ignore[assignment]
    _ORT_IMPORT_ERROR = exc

_SESSION = None
_SESSION_PATH: str | None = None

# Default tunable thresholds (env-overridable for low-end machines).
_DEFAULT_CONF = 0.30
_DEFAULT_IOU = 0.45
_INPUT_SIZE = 640


def model_path() -> Path:
    override = os.environ.get("BLINKY_ICON_MODEL_PATH", "").strip()
    if override:
        return Path(override)
    here = Path(__file__).resolve()
    # common/python/ocr/icon_detect.py -> repo root = parents[3]
    root = here.parents[3]
    return root / "weights" / "omniparser" / "icon_detect" / "model.onnx"


def is_available() -> bool:
    if onnxruntime is None:
        return False
    return model_path().exists()


def _get_session():
    global _SESSION, _SESSION_PATH
    if onnxruntime is None:
        raise RuntimeError(f"onnxruntime unavailable: {_ORT_IMPORT_ERROR}")
    path = str(model_path())
    if _SESSION is not None and _SESSION_PATH == path:
        return _SESSION

    _SESSION = onnxruntime.InferenceSession(path, providers=["CPUExecutionProvider"])
    _SESSION_PATH = path
    LOGGER.info("Icon detector loaded: %s", path)
    return _SESSION


def _letterbox(img, size: int = _INPUT_SIZE):
    """Resize with aspect preserved + gray padding. Returns (batch, ratio, (dw, dh))."""
    import cv2
    import numpy as np

    h, w = img.shape[:2]
    ratio = min(size / w, size / h)
    nw, nh = int(round(w * ratio)), int(round(h * ratio))
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
    canvas = np.full((size, size, 3), 114, dtype=np.uint8)
    dw, dh = (size - nw) // 2, (size - nh) // 2
    canvas[dh : dh + nh, dw : dw + nw] = resized
    rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
    batch = rgb.astype("float32") / 255.0
    batch = batch.transpose(2, 0, 1)[None]
    return batch, ratio, (dw, dh)


def _nms(boxes, scores, iou_thresh: float):
    """Greedy NMS in numpy. boxes: (N,4) xyxy. Returns kept indices."""
    import numpy as np

    if len(boxes) == 0:
        return []
    order = scores.argsort()[::-1]
    kept: list[int] = []
    while len(order) > 0:
        i = int(order[0])
        kept.append(i)
        if len(order) == 1:
            break
        xx1 = np.maximum(boxes[i, 0], boxes[order[1:], 0])
        yy1 = np.maximum(boxes[i, 1], boxes[order[1:], 1])
        xx2 = np.minimum(boxes[i, 2], boxes[order[1:], 2])
        yy2 = np.minimum(boxes[i, 3], boxes[order[1:], 3])
        inter = np.maximum(0.0, xx2 - xx1) * np.maximum(0.0, yy2 - yy1)
        area_i = (boxes[i, 2] - boxes[i, 0]) * (boxes[i, 3] - boxes[i, 1])
        area_rest = (boxes[order[1:], 2] - boxes[order[1:], 0]) * (
            boxes[order[1:], 3] - boxes[order[1:], 1]
        )
        union = area_i + area_rest - inter
        iou = inter / np.maximum(union, 1e-9)
        order = order[1:][iou <= iou_thresh]
    return kept


def detect_icons(
    image_path: str | Path,
    conf_thresh: float | None = None,
    iou_thresh: float | None = None,
) -> list[dict[str, Any]]:
    """Detect generic UI icon boxes on a screenshot.

    Returns items in screenshot pixel space:
    ``{"text": "", "x":..,"y":..,"width":..,"height":..,
    "confidence":..,"source":"icon","control_type":"Image","clickable":True}``.
    """
    import numpy as np

    if conf_thresh is None:
        try:
            conf_thresh = float(os.environ.get("BLINKY_ICON_CONF", str(_DEFAULT_CONF)))
        except ValueError:
            conf_thresh = _DEFAULT_CONF
    if iou_thresh is None:
        try:
            iou_thresh = float(os.environ.get("BLINKY_ICON_IOU", str(_DEFAULT_IOU)))
        except ValueError:
            iou_thresh = _DEFAULT_IOU

    path = Path(image_path)
    if not path.exists():
        return []
    if not is_available():
        LOGGER.debug("Icon detector unavailable (missing onnxruntime or model file)")
        return []

    try:
        import cv2
    except Exception as exc:
        LOGGER.warning("Icon detection skipped (no cv2): %s", exc)
        return []

    img = cv2.imread(str(path))
    if img is None:
        return []
    orig_h, orig_w = img.shape[:2]

    try:
        session = _get_session()
        batch, ratio, (dw, dh) = _letterbox(img)
        input_name = session.get_inputs()[0].name
        out = session.run(None, {input_name: batch})[0]  # (1,5,8400)
    except Exception as exc:
        LOGGER.warning("Icon inference failed: %s", exc)
        return []

    preds = np.asarray(out[0]).T  # (8400,5): xc,yc,w,h,conf (640-space)
    scores = preds[:, 4]
    keep = scores >= conf_thresh
    preds = preds[keep]
    scores = scores[keep]
    if len(preds) == 0:
        return []

    # xywh (padded 640) -> xyxy (original pixels)
    boxes = np.zeros((len(preds), 4), dtype=np.float64)
    boxes[:, 0] = (preds[:, 0] - preds[:, 2] / 2 - dw) / ratio
    boxes[:, 1] = (preds[:, 1] - preds[:, 3] / 2 - dh) / ratio
    boxes[:, 2] = (preds[:, 0] + preds[:, 2] / 2 - dw) / ratio
    boxes[:, 3] = (preds[:, 1] + preds[:, 3] / 2 - dh) / ratio
    boxes[:, [0, 2]] = boxes[:, [0, 2]].clip(0, orig_w)
    boxes[:, [1, 3]] = boxes[:, [1, 3]].clip(0, orig_h)

    # Drop degenerate boxes
    valid = (boxes[:, 2] - boxes[:, 0] >= 6) & (boxes[:, 3] - boxes[:, 1] >= 6)
    boxes, scores = boxes[valid], scores[valid]
    if len(boxes) == 0:
        return []

    kept = _nms(boxes, scores, iou_thresh)
    items: list[dict[str, Any]] = []
    for i in kept:
        x1, y1, x2, y2 = (int(round(v)) for v in boxes[i])
        items.append(
            {
                "text": "",
                "x": x1,
                "y": y1,
                "width": max(1, x2 - x1),
                "height": max(1, y2 - y1),
                "confidence": float(scores[i]),
                "source": "icon",
                "control_type": "Image",
                "clickable": True,
            }
        )
    LOGGER.info("Icon detector found %d icon boxes", len(items))
    return items
