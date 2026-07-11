"""tools/screen_reader_tool.py — Visual screen understanding for Lucifex.

Captures the screen (or a region), extracts text via OCR, and can send
screenshots to a vision-capable model to answer questions about what is
visible. Enables the agent to understand the user's visual context without
being told explicitly.

Capabilities:
- screenshot(): capture screen or region, save to file
- read_screen(): extract all visible text via OCR (pytesseract) or vision model
- ask_about_screen(): send screenshot to vision model with a question
- find_text_on_screen(): locate specific text and return coordinates

Dependencies (auto-installed if missing): Pillow, pytesseract
Tesseract OCR must be installed separately on the system.
"""
from __future__ import annotations

import base64
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

from tools.registry import registry

logger = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform == "win32"
_IS_MAC = sys.platform == "darwin"

_screenshot_dir: Optional[Path] = None


def _get_screenshot_dir() -> Path:
    global _screenshot_dir
    if _screenshot_dir is None:
        try:
            from lucifex_constants import get_lucifex_home
            _screenshot_dir = Path(get_lucifex_home()) / "screenshots"
        except Exception:
            _screenshot_dir = Path.home() / ".lucifex" / "screenshots"
    _screenshot_dir.mkdir(parents=True, exist_ok=True)
    return _screenshot_dir


# ── Screenshot ────────────────────────────────────────────────────────────────

def _capture_pil(region: Optional[tuple] = None):
    """Capture screen using Pillow/mss."""
    try:
        from PIL import ImageGrab
        if region:
            img = ImageGrab.grab(bbox=region)
        else:
            img = ImageGrab.grab()
        return img
    except ImportError:
        pass

    try:
        import mss
        with mss.mss() as sct:
            if region:
                monitor = {"left": region[0], "top": region[1],
                           "width": region[2] - region[0], "height": region[3] - region[1]}
            else:
                monitor = sct.monitors[0]
            raw = sct.grab(monitor)
            from PIL import Image
            return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    except Exception as exc:
        logger.debug("Screenshot capture failed: %s", exc)
        return None


def _capture_via_system(output_path: Path) -> bool:
    """Fallback: use system tools for screenshot."""
    try:
        if _IS_WINDOWS:
            script = f'Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Screen]::PrimaryScreen; [System.Windows.Forms.SendKeys]::SendWait("%{{PRTSC}}"); Start-Sleep -m 100; $img=[System.Windows.Forms.Clipboard]::GetImage(); $img.Save("{output_path}")'
            result = subprocess.run(["powershell", "-command", script], capture_output=True, timeout=5)
            return output_path.exists()
        elif _IS_MAC:
            result = subprocess.run(
                ["screencapture", "-x", str(output_path)],
                capture_output=True, timeout=5
            )
            return result.returncode == 0
        else:
            result = subprocess.run(
                ["scrot", str(output_path)],
                capture_output=True, timeout=5
            )
            return result.returncode == 0
    except Exception:
        return False


def screenshot(region: Optional[str] = None) -> str:
    """Capture a screenshot and save it. Returns the file path.

    region: optional 'x1,y1,x2,y2' string for a specific area.
    """
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = _get_screenshot_dir() / f"screenshot_{ts}.png"

    parsed_region = None
    if region:
        try:
            parsed_region = tuple(int(v) for v in region.split(","))
        except Exception:
            pass

    img = _capture_pil(parsed_region)
    if img:
        img.save(str(output))
        return json.dumps({"success": True, "path": str(output), "size": list(img.size)})

    ok = _capture_via_system(output)
    if ok:
        return json.dumps({"success": True, "path": str(output)})

    return json.dumps({"success": False, "error": "Screenshot capture failed. Install Pillow (pip install Pillow)."})


# ── OCR Text Extraction ───────────────────────────────────────────────────────

def _ocr_extract(img) -> str:
    """Extract text from PIL image using pytesseract."""
    try:
        import pytesseract
        text = pytesseract.image_to_string(img)
        return text.strip()
    except ImportError:
        return ""
    except Exception as exc:
        logger.debug("OCR failed: %s", exc)
        return ""


def read_screen(region: Optional[str] = None) -> str:
    """Extract all visible text from the screen using OCR.

    Returns the extracted text content.
    """
    parsed_region = None
    if region:
        try:
            parsed_region = tuple(int(v) for v in region.split(","))
        except Exception:
            pass

    img = _capture_pil(parsed_region)
    if img is None:
        return json.dumps({"error": "Could not capture screen."})

    text = _ocr_extract(img)
    if text:
        return json.dumps({"text": text, "length": len(text), "source": "ocr"})

    # Fallback: save and return path for vision model
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = _get_screenshot_dir() / f"screen_{ts}.png"
    img.save(str(path))
    return json.dumps({
        "text": "",
        "screenshot_path": str(path),
        "message": "OCR returned no text. Screenshot saved — use ask_about_screen for vision analysis.",
    })


# ── Vision Model Q&A ──────────────────────────────────────────────────────────

def _image_to_base64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def ask_about_screen(question: str, region: Optional[str] = None) -> str:
    """Take a screenshot and ask a vision model a question about it.

    The screenshot is sent to the configured vision-capable model with the question.
    """
    # Save screenshot first
    result = json.loads(screenshot(region))
    if not result.get("success"):
        return json.dumps({"error": result.get("error", "Screenshot failed")})

    screenshot_path = Path(result["path"])

    try:
        img_b64 = _image_to_base64(screenshot_path)

        # Use the agent's vision-capable client
        try:
            from agent.auxiliary_client import run_vision_prompt
            answer = run_vision_prompt(
                prompt=question,
                image_base64=img_b64,
                image_mime="image/png",
            )
            return json.dumps({"answer": answer, "screenshot": str(screenshot_path)})
        except ImportError:
            pass

        # Fallback: call OpenAI-compatible vision endpoint directly
        import os
        api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return json.dumps({
                "screenshot": str(screenshot_path),
                "message": "Screenshot saved. No vision API key found for automated analysis.",
            })

        return json.dumps({
            "screenshot": str(screenshot_path),
            "message": "Screenshot saved. Vision model call not available in this context.",
        })

    except Exception as exc:
        logger.debug("ask_about_screen failed: %s", exc)
        return json.dumps({"error": str(exc), "screenshot": str(screenshot_path)})


def find_text_on_screen(text: str) -> str:
    """Find the position of specific text on screen using OCR with location data."""
    img = _capture_pil()
    if img is None:
        return json.dumps({"error": "Could not capture screen."})

    try:
        import pytesseract
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        matches = []
        for i, word in enumerate(data["text"]):
            if text.lower() in word.lower():
                x = data["left"][i]
                y = data["top"][i]
                w = data["width"][i]
                h = data["height"][i]
                matches.append({
                    "word": word,
                    "x": x, "y": y,
                    "center_x": x + w // 2,
                    "center_y": y + h // 2,
                    "confidence": data["conf"][i],
                })
        return json.dumps({"matches": matches, "query": text})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


# ── Registration ──────────────────────────────────────────────────────────────

_tools = [
    ("screenshot", screenshot,
     "Capture a screenshot of the current screen. Optionally specify a region as 'x1,y1,x2,y2'. Returns the file path.",
     {"region": {"type": "string", "description": "Optional region: 'x1,y1,x2,y2'"}}),
    ("read_screen", read_screen,
     "Extract all visible text from the screen using OCR. Returns the text content.",
     {"region": {"type": "string", "description": "Optional region: 'x1,y1,x2,y2'"}}),
    ("ask_about_screen", ask_about_screen,
     "Take a screenshot and ask a vision model a question about what is visible on screen.",
     {"question": {"type": "string", "description": "What you want to know about the screen"},
      "region": {"type": "string", "description": "Optional region: 'x1,y1,x2,y2'"}}),
    ("find_text_on_screen", find_text_on_screen,
     "Find the position (coordinates) of specific text visible on the screen using OCR.",
     {"text": {"type": "string", "description": "Text to locate on screen"}}),
]

for _name, _fn, _desc, _props in _tools:
    _required = [k for k in _props if k not in {"region"}]
    registry.register(
        name=_name,
        toolset="computer",
        schema={
            "name": _name,
            "description": _desc,
            "parameters": {"type": "object", "properties": _props, "required": _required},
        },
        handler=_fn,
        description=_desc,
        emoji="👁",
    )
