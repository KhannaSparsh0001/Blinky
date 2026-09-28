#!/usr/bin/env python3
"""ESP32 RGB Light Controller Tool for Blinky and Antigravity.
Controls physical ESP32 RGB LED lights over local Wi-Fi HTTP requests.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


def _get_default_ip() -> str:
    if "ESP32_HOST" in os.environ:
        return os.environ["ESP32_HOST"].strip()
    if "ESP32_LIGHT_IP" in os.environ:
        return os.environ["ESP32_LIGHT_IP"].strip()
    env_file = Path(__file__).resolve().parent.parent.parent.parent / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("ESP32_HOST=") or line.startswith("ESP32_LIGHT_IP="):
                        return line.split("=", 1)[1].strip().strip("'\"")
        except Exception:
            pass
    return "192.168.1.4"


DEFAULT_ESP32_IP = _get_default_ip()
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
        root = Path(__file__).resolve().parent.parent.parent.parent
        env_file = root / ".env"
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("ESP32_HOST=") or line.startswith("ESP32_LIGHT_IP="):
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

    _DISCOVERED_IP = DEFAULT_ESP32_IP
    return _DISCOVERED_IP


COLOR_MAP: dict[str, tuple[int, int, int]] = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "purple": (180, 0, 255),
    "pink": (255, 20, 147),
    "orange": (255, 100, 0),
    "white": (255, 255, 255),
    "warm_white": (255, 180, 100),
    "warm white": (255, 180, 100),
    "off": (0, 0, 0),
    "black": (0, 0, 0),
}

# State tracking for toggle
_LAST_STATE = {"on": False}


def resolve_color(color_name: str, r=None, g=None, b=None, brightness: float = 1.0) -> tuple[int, int, int]:
    """Resolve color input to RGB values with optional brightness (0.0 to 1.0)."""
    color_clean = str(color_name or "").strip().lower().replace(" ", "_")

    if r is not None and g is not None and b is not None:
        target_r, target_g, target_b = int(r), int(g), int(b)
    elif color_clean in COLOR_MAP:
        target_r, target_g, target_b = COLOR_MAP[color_clean]
    elif "off" in color_clean:
        target_r, target_g, target_b = 0, 0, 0
    else:
        target_r, target_g, target_b = 255, 255, 255

    brightness = max(0.0, min(1.0, float(brightness)))
    return int(target_r * brightness), int(target_g * brightness), int(target_b * brightness)


def send_to_esp32(r: int, g: int, b: int, ip: str | None = None, timeout: float = 3.0) -> dict[str, Any]:
    """Send RGB values to ESP32 /rgb or /set endpoint."""
    target_ip = ip or get_esp32_ip()
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))

    endpoints = [
        f"http://{target_ip}/rgb?r={r}&g={g}&b={b}",
        f"http://{target_ip}/set?r={r}&g={g}&b={b}",
    ]
    last_err = None
    for url in endpoints:
        try:
            req = urllib.request.Request(url, headers={"Connection": "close"}, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read().decode("utf-8").strip()
                _LAST_STATE["on"] = (r > 0 or g > 0 or b > 0)
                return {
                    "success": True,
                    "status": "ok",
                    "ip": target_ip,
                    "r": r,
                    "g": g,
                    "b": b,
                    "esp32_response": body,
                    "message": f"Light set to RGB({r}, {g}, {b})",
                }
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            last_err = e
        except Exception as e:
            last_err = e
            break

    # If offline or failed, return graceful status so caller won't crash
    _LAST_STATE["on"] = (r > 0 or g > 0 or b > 0)
    return {
        "success": False,
        "error": f"Failed to connect to ESP32 at {target_ip}: {last_err}",
        "message": f"Set light to RGB({r}, {g}, {b}) (Dispatched to {target_ip})",
        "ip": target_ip,
        "r": r,
        "g": g,
        "b": b,
    }


def check_status(ip: str | None = None, timeout: float = 2.0) -> dict[str, Any]:
    """Check if ESP32 web server is reachable."""
    target_ip = ip or get_esp32_ip()
    url = f"http://{target_ip}/"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8").strip()
            return {
                "success": True,
                "online": True,
                "ip": target_ip,
                "esp32_response": body,
            }
    except Exception as e:
        return {
            "success": False,
            "online": False,
            "ip": target_ip,
            "error": str(e),
        }


def handle_request(params: dict[str, Any]) -> dict[str, Any]:
    """Execute light control HTTP GET request to ESP32."""
    ip = params.get("ip") or get_esp32_ip()
    action = params.get("action", "set")

    if action == "status":
        return check_status(ip=ip)

    if action in ("turn_off", "off"):
        res = send_to_esp32(0, 0, 0, ip=ip)
        res["message"] = "Turned off the smart light."
        _LAST_STATE["on"] = False
        return res

    if action in ("turn_on", "on"):
        res = send_to_esp32(255, 255, 255, ip=ip)
        res["message"] = "Turned on the smart light."
        _LAST_STATE["on"] = True
        return res

    if action == "toggle":
        if _LAST_STATE["on"]:
            res = send_to_esp32(0, 0, 0, ip=ip)
            res["message"] = "Toggled smart light off."
            _LAST_STATE["on"] = False
        else:
            res = send_to_esp32(255, 255, 255, ip=ip)
            res["message"] = "Toggled smart light on."
            _LAST_STATE["on"] = True
        return res

    if action == "brightness":
        val = int(params.get("value", 255))
        if val <= 100:
            val = int(val * 2.55)
        val = max(0, min(255, val))
        res = send_to_esp32(val, val, val, ip=ip)
        res["message"] = f"Adjusted smart light brightness to {val}."
        _LAST_STATE["on"] = val > 0
        return res

    color = params.get("color", "")
    r = params.get("r")
    g = params.get("g")
    b = params.get("b")
    brightness = params.get("brightness", 1.0)
    if isinstance(brightness, (int, float)) and brightness > 1.0:
        brightness = brightness / 100.0

    final_r, final_g, final_b = resolve_color(color, r, g, b, brightness)
    res = send_to_esp32(final_r, final_g, final_b, ip=ip)
    color_desc = color or f"RGB({final_r},{final_g},{final_b})"
    res["message"] = f"Set smart light to {color_desc}."
    res["color_requested"] = color_desc
    return res


def resolve_esp32_light_request(question: str) -> dict[str, Any] | None:
    """Fast-path query matcher for ESP32 light requests."""
    return resolve_light_request(question)


def resolve_light_request(question: str) -> dict[str, Any] | None:
    """Fast-path resolution for light commands."""
    q = question.strip().lower()
    q_clean = re.sub(r"[?!.,;:']", "", q)

    # Ignore media playback
    if any(q_clean.startswith(p) for p in ("play ", "queue ", "listen to ", "stream ")) or any(
        k in q_clean for k in ["spotify", "youtube", "music", "song", "track", "video", "playlist"]
    ):
        return None

    # Check for off commands first
    if (
        re.search(r"\b(turn|switch|shut)\s+(off|down)\b.*\b(light|led)s?\b", q_clean)
        or re.search(r"\b(light|led)s?\b.*\b(turn|switch|shut)?\s*off\b", q_clean)
        or q_clean in ("lights off", "light off", "turn off light", "turn off lights", "dim off")
    ):
        return {"action": "off"}

    # Check toggle
    if any(k in q_clean for k in ["toggle light", "toggle lights", "switch light"]):
        return {"action": "toggle"}

    is_light_mention = bool(re.search(r"\b(light|led|smart light)s?\b", q_clean))
    found_color = None
    for color_name in sorted(COLOR_MAP.keys(), key=lambda x: -len(x)):
        if color_name in ("off", "black"):
            continue
        c_pat = color_name.replace("_", " ")
        if re.search(r"\b" + re.escape(c_pat) + r"\b", q_clean):
            found_color = color_name
            break

    if is_light_mention:
        brightness = 1.0
        pct_match = re.search(r"(\d{1,3})\s*%", q_clean)
        if pct_match:
            brightness = float(pct_match.group(1)) / 100.0

        if (
            re.search(r"\b(turn|switch)\s+on\b", q_clean)
            or re.search(r"\b(set|change|make|dim|brighten)\b", q_clean)
            or found_color
            or q_clean in ("lights on", "light on", "turn on light", "turn on lights")
        ):
            return {
                "action": "set",
                "color": found_color or "white",
                "brightness": brightness,
            }

    if found_color and ("light" in q_clean or "led" in q_clean):
        return {
            "action": "set",
            "color": found_color,
            "brightness": 1.0,
        }

    if q_clean in {"lights", "light", "smart light", "smart lights", "toggle"}:
        return {"action": "toggle"}

    return None


def main():
    if len(sys.argv) < 2:
        res = handle_request({"action": "status"})
        print(json.dumps(res, indent=2))
        return

    arg = sys.argv[1].strip()
    if arg.startswith("{"):
        try:
            params = json.loads(arg)
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"Invalid JSON input: {e}"}))
            sys.exit(1)
    else:
        arg_lower = arg.lower()
        if arg_lower in COLOR_MAP:
            params = {"action": "set", "color": arg_lower}
        elif arg_lower in {"on", "off", "toggle", "status"}:
            params = {"action": arg_lower}
        else:
            resolved = resolve_light_request(arg)
            params = resolved if resolved else {"color": arg}

    result = handle_request(params)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
