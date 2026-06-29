from __future__ import annotations

import base64
import io
import os
from PIL import Image, ImageDraw, ImageFont

def annotate_screenshot(screenshot_path: str, steps: list[dict]) -> str | None:
    """
    Draw highlight boxes on the screenshot for each step's match,
    and return the annotated image as a base64-encoded PNG string.
    """
    if not os.path.exists(screenshot_path):
        return None

    try:
        image = Image.open(screenshot_path)
        draw = ImageDraw.Draw(image)
        
        # Try to load a nice font, fallback to default if not found
        font = None
        try:
            # Common paths for Windows fonts
            font_path = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Fonts", "segoeui.ttf")
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, 20)
        except Exception:
            pass

        has_highlights = False

        for step in steps:
            match = step.get("match")
            if not match:
                continue

            x = match.get("x")
            y = match.get("y")
            w = match.get("width")
            h = match.get("height")

            if x is None or y is None or w is None or h is None:
                continue

            has_highlights = True

            # Draw outer glow / shadow (black, slightly larger)
            draw.rectangle(
                [x - 2, y - 2, x + w + 2, y + h + 2],
                outline="black",
                width=4
            )

            # Draw the main neon-orange highlight rectangle
            draw.rectangle(
                [x, y, x + w, y + h],
                outline="#FF5722",
                width=3
            )

            # Draw a step number badge (e.g. "1") at the top-left of the box
            step_num = str(step.get("step", 1))
            
            # Badge size estimation
            badge_w = 24
            badge_h = 24
            
            badge_x = max(0, x - 12)
            badge_y = max(0, y - 12)

            # Draw badge background (black circle/ellipse or rounded rect)
            draw.ellipse(
                [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
                fill="#FF5722",
                outline="black",
                width=1
            )

            # Draw badge text inside
            # simple text positioning fallback
            text_x = badge_x + 8
            text_y = badge_y + 2
            if font:
                text_x = badge_x + (badge_w - font.getlength(step_num)) / 2
                text_y = badge_y + 1
            draw.text((text_x, text_y), step_num, fill="white", font=font)

        # Save to memory as JPEG (efficient compression for mobile transfer)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85)
        img_bytes = buffer.getvalue()
        
        return base64.b64encode(img_bytes).decode("utf-8")

    except Exception as e:
        from utils.logging import get_logger
        get_logger("blinky.screen_annotator").error(f"Error annotating screenshot: {e}")
        return None


def save_parsed_ui_screenshot(screenshot_path: str, ref_items: list[dict]) -> str | None:
    """
    Draw bounding boxes and references (@e1, @e2, etc.) for all parsed UI elements
    onto the screenshot, and save it to the 'screenshots_parsed' folder.
    """
    if not os.path.exists(screenshot_path):
        return None

    try:
        from pathlib import Path
        image = Image.open(screenshot_path)
        draw = ImageDraw.Draw(image)
        
        # Load a nice font if possible
        font = None
        try:
            font_path = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Fonts", "segoeui.ttf")
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, 14)
        except Exception:
            pass

        for item in ref_items:
            x = item.get("x")
            y = item.get("y")
            w = item.get("width")
            h = item.get("height")
            ref = item.get("ref", "")
            source = item.get("source", "")
            
            if x is None or y is None or w is None or h is None or not ref:
                continue

            # Neon Green/Lime for UIA, Cyan/DeepSkyBlue for OmniParser/OCR
            color = "#39FF14" if source == "uia" else "#00E5FF"
            
            # Draw bounding box
            draw.rectangle(
                [x, y, x + w, y + h],
                outline=color,
                width=2
            )

            # Draw a small text badge with the @ref name (e.g. "@e25")
            text = f"{ref}:{item.get('control_type', 'Control')}"
            text_w = 70
            try:
                if font:
                    text_w = font.getlength(text)
            except Exception:
                pass
            
            # Background rect for badge
            badge_y = max(0, y - 18)
            draw.rectangle(
                [x, badge_y, x + text_w + 4, y],
                fill=color
            )
            # Text label
            draw.text((x + 2, badge_y + 1), text, fill="black", font=font)

        # Create screenshots_parsed folder in the parent directory of screenshots
        screenshot_path_obj = Path(screenshot_path)
        parent_dir = screenshot_path_obj.parent.parent
        output_dir = parent_dir / "screenshots_parsed"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / screenshot_path_obj.name
        image.save(output_path, format="JPEG", quality=85)
        return str(output_path)

    except Exception as e:
        from utils.logging import get_logger
        get_logger("blinky.screen_annotator").error(f"Error saving parsed UI screenshot: {e}")
        return None
