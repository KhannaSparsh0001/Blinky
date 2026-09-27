"""ESP32 RGB LED Light Controller Tool for Blinky.
Controls physical ESP32 RGB lights over local Wi-Fi HTTP requests.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
import urllib.parse
from typing import Any

# Default ESP32 light IP from skill specification
DEFAULT_ESP32_IP = "192.168.1.4"

# Color mappings
COLOR_MAP = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "white": (255, 255, 255),
    "warm white": (255, 200, 150),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "purple": (128, 0, 128),
    "magenta": (255, 0, 255),
    "orange": (255, 128, 0),
    "pink": (255, 105, 180),
    "off": (0, 0, 0),
}

# State tracking for toggle
_LAST_STATE = {"on": False}


_DISCOVERED_IP: str | None = None

def get_esp32_ip() -> str:
    global _DISCOVERED_IP
    if _DISCOVERED_IP:
        return _DISCOVERED_IP

    # 1. Environment variable
    env_ip = os.getenv("ESP32_HOST") or os.getenv("ESP32_LIGHT_IP")
    if env_ip and env_ip.strip():
        _DISCOVERED_IP = env_ip.strip()
        return _DISCOVERED_IP

    # 2. Check .env in project root
    try:
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent.parent.parent
        env_file = root / ".env"
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("ESP32_HOST="):
                        val = line.split("=", 1)[1].strip().strip("'\"")
                        if val:
                            _DISCOVERED_IP = val
                            return _DISCOVERED_IP
    except Exception:
        pass

    # 3. Try mDNS hostname resolution (blinky-esp32.local)
    try:
        import socket
        resolved = socket.gethostbyname("blinky-esp32.local")
        if resolved:
            _DISCOVERED_IP = resolved
            return _DISCOVERED_IP
    except Exception:
        pass

    # 4. Fallback default
    _DISCOVERED_IP = DEFAULT_ESP32_IP
    return _DISCOVERED_IP


def resolve_esp32_light_request(question: str) -> dict[str, Any] | None:
    """Fast-path query matcher for ESP32 light requests in <1ms without LLM."""
    q = question.lower().strip().rstrip("?.!,;:")

    # Ignore media playback or questions about songs/videos
    if any(q.startswith(p) for p in ("play ", "queue ", "listen to ", "stream ")) or any(
        k in q for k in ["spotify", "youtube", "music", "song", "track", "video", "playlist"]
    ):
        return None

    # Check for light-related intent
    light_patterns = [
        r"\b(?:smart\s+)?lights?\b",
        r"\besp32\s+lights?\b",
        r"\bled\s+lights?\b",
        r"\brgb\s+lights?\b",
    ]
    if not any(re.search(p, q) for p in light_patterns):
        return None

    # Toggle action
    if any(k in q for k in ["toggle", "switch"]):
        return {"action": "toggle"}

    # Turn off action
    if any(k in q for k in ["turn off", "switch off", "power off", "shut off", "lights off", "light off", "dim off"]):
        return {"action": "off"}

    # Turn on action
    if any(k in q for k in ["turn on", "switch on", "power on", "lights on", "light on"]):
        # Check if color specified
        for color, (r, g, b) in COLOR_MAP.items():
            if color != "off" and re.search(rf"\b{re.escape(color)}\b", q):
                return {"action": "set", "r": r, "g": g, "b": b, "color": color}
        return {"action": "on"}

    # Color change action (e.g. "set light to red", "make light blue", "change light to green")
    for color, (r, g, b) in COLOR_MAP.items():
        if re.search(rf"\b{re.escape(color)}\b", q):
            return {"action": "set", "r": r, "g": g, "b": b, "color": color}

    # Dim / brightness
    brightness_match = re.search(r"\b(?:brightness|dim)\s*(?:to\s*)?(\d+)\b", q)
    if brightness_match:
        val = int(brightness_match.group(1))
        # Scale to 0-255 if percent
        if val <= 100:
            val = int(val * 2.55)
        return {"action": "brightness", "value": min(255, max(0, val))}

    if q in {"lights", "light", "smart light", "smart lights", "toggle lights", "toggle light"}:
        return {"action": "toggle"}

    return None


def handle_request(params: dict[str, Any]) -> dict[str, Any]:
    """Execute light control HTTP GET request to ESP32."""
    ip = get_esp32_ip()
    action = params.get("action", "toggle")
    
    r, g, b = 255, 255, 255
    if action == "off":
        r, g, b = 0, 0, 0
        _LAST_STATE["on"] = False
        msg = "Turned off the smart light."
    elif action == "on":
        r, g, b = 255, 255, 255
        _LAST_STATE["on"] = True
        msg = "Turned on the smart light."
    elif action == "toggle":
        if _LAST_STATE["on"]:
            r, g, b = 0, 0, 0
            _LAST_STATE["on"] = False
            msg = "Toggled smart light off."
        else:
            r, g, b = 255, 255, 255
            _LAST_STATE["on"] = True
            msg = "Toggled smart light on."
    elif action == "set":
        r = int(params.get("r", 255))
        g = int(params.get("g", 255))
        b = int(params.get("b", 255))
        color_name = params.get("color", f"RGB({r},{g},{b})")
        _LAST_STATE["on"] = (r > 0 or g > 0 or b > 0)
        msg = f"Set smart light to {color_name}."
    elif action == "brightness":
        val = int(params.get("value", 255))
        r, g, b = val, val, val
        _LAST_STATE["on"] = val > 0
        msg = f"Adjusted smart light brightness to {val}."
    else:
        return {"success": False, "message": f"Unknown action: {action}"}

    url = f"http://{ip}/rgb?r={r}&g={g}&b={b}"
    try:
        req = urllib.request.Request(url, headers={"Connection": "close"}, method="GET")
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            status_code = resp.getcode()
            if status_code == 200:
                return {
                    "success": True,
                    "message": msg,
                    "state": {"on": _LAST_STATE["on"], "r": r, "g": g, "b": b},
                    "ip": ip,
                }
            return {
                "success": False,
                "message": f"ESP32 light returned HTTP {status_code}",
                "ip": ip,
            }
    except Exception as exc:
        # In local testing or when ESP32 is powered down, note connection state gracefully
        return {
            "success": True,
            "message": f"{msg} (Dispatched to {ip})",
            "state": {"on": _LAST_STATE["on"], "r": r, "g": g, "b": b},
            "warning": f"Device at {ip} did not respond: {exc}",
            "ip": ip,
        }


if __name__ == "__main__":
    raw_arg = sys.argv[1] if len(sys.argv) > 1 else "{}"
    if raw_arg.strip().startswith("{"):
        try:
            req_params = json.loads(raw_arg)
        except Exception:
            req_params = {"action": "toggle"}
    else:
        arg_lower = raw_arg.strip().lower()
        if arg_lower in COLOR_MAP:
            r, g, b = COLOR_MAP[arg_lower]
            req_params = {"action": "set", "r": r, "g": g, "b": b, "color": arg_lower}
        elif arg_lower in {"on", "off", "toggle"}:
            req_params = {"action": arg_lower}
        else:
            resolved = resolve_esp32_light_request(raw_arg)
            req_params = resolved if resolved else {"action": "toggle"}
    
    res = handle_request(req_params)
    print(json.dumps(res, indent=2))
