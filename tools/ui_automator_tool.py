"""tools/ui_automator_tool.py — UI Automation: control any app via the agent.

Provides mouse/keyboard control over any application — not just the terminal.
The agent can click buttons, type text, press key combinations, and run
recorded macros in any app visible on screen.

Uses pyautogui (cross-platform) with pywinauto for Windows-specific
element location. Gracefully degrades to coordinate-based control only.

Tools: ui_click, ui_type, ui_press, ui_find_and_click, macro_record, macro_run
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Optional

from tools.registry import registry

logger = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform == "win32"
_macros_dir: Optional[Path] = None


def _get_macros_dir() -> Path:
    global _macros_dir
    if _macros_dir is None:
        try:
            from lucifex_constants import get_lucifex_home
            _macros_dir = Path(get_lucifex_home()) / "ui_macros"
        except Exception:
            _macros_dir = Path.home() / ".lucifex" / "ui_macros"
    _macros_dir.mkdir(parents=True, exist_ok=True)
    return _macros_dir


def _pyautogui():
    try:
        import pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.05
        return pyautogui
    except ImportError:
        return None


# ── Tools ──────────────────────────────────────────────────────────────────────

def ui_click(x: int, y: int, button: str = "left", clicks: int = 1) -> str:
    """Click at screen coordinates."""
    pag = _pyautogui()
    if not pag:
        return json.dumps({"error": "pyautogui not installed. Run: pip install pyautogui"})
    try:
        pag.click(x, y, button=button, clicks=clicks, interval=0.1)
        return json.dumps({"success": True, "x": x, "y": y, "button": button, "clicks": clicks})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def ui_type(text: str, interval: float = 0.03) -> str:
    """Type text at the current cursor position in any active application."""
    pag = _pyautogui()
    if not pag:
        return json.dumps({"error": "pyautogui not installed."})
    try:
        # Handle multi-line
        lines = text.split("\n")
        for i, line in enumerate(lines):
            pag.typewrite(line, interval=interval)
            if i < len(lines) - 1:
                pag.press("enter")
        return json.dumps({"success": True, "chars_typed": len(text)})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def ui_press(keys: str) -> str:
    """Press a keyboard shortcut or key combination.

    Examples: 'ctrl+c', 'alt+f4', 'win+d', 'enter', 'escape', 'ctrl+shift+p'
    """
    pag = _pyautogui()
    if not pag:
        return json.dumps({"error": "pyautogui not installed."})
    try:
        parts = [k.strip() for k in keys.lower().split("+")]
        if len(parts) == 1:
            pag.press(parts[0])
        else:
            pag.hotkey(*parts)
        return json.dumps({"success": True, "keys": keys})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def ui_scroll(x: int, y: int, amount: int = 3) -> str:
    """Scroll the mouse wheel at a position."""
    pag = _pyautogui()
    if not pag:
        return json.dumps({"error": "pyautogui not installed."})
    try:
        pag.scroll(amount, x=x, y=y)
        return json.dumps({"success": True, "x": x, "y": y, "amount": amount})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def ui_find_and_click(target: str, confidence: float = 0.8) -> str:
    """Locate a UI element by image/text on screen and click it.

    target: text to find via OCR, or path to a reference image file.
    """
    # Try image matching first
    if target.endswith((".png", ".jpg", ".jpeg")) and Path(target).exists():
        pag = _pyautogui()
        if pag:
            try:
                location = pag.locateOnScreen(target, confidence=confidence)
                if location:
                    center = pag.center(location)
                    pag.click(center)
                    return json.dumps({"success": True, "method": "image_match", "x": center.x, "y": center.y})
            except Exception as exc:
                logger.debug("Image match failed: %s", exc)

    # Fallback: find text on screen and click its center
    try:
        from tools.screen_reader_tool import find_text_on_screen
        result = json.loads(find_text_on_screen(target))
        matches = result.get("matches", [])
        if matches:
            best = sorted(matches, key=lambda m: m.get("confidence", 0), reverse=True)[0]
            cx, cy = best["center_x"], best["center_y"]
            pag = _pyautogui()
            if pag:
                pag.click(cx, cy)
                return json.dumps({"success": True, "method": "ocr_text_match", "x": cx, "y": cy, "word": best["word"]})
    except Exception as exc:
        logger.debug("Text find failed: %s", exc)

    return json.dumps({"success": False, "error": f"Could not locate '{target}' on screen."})


def macro_record(name: str, actions: list) -> str:
    """Save a list of UI actions as a named macro.

    actions: list of dicts, each with 'type' (click/type/press/wait) and params.
    Example: [{"type":"press","keys":"ctrl+a"},{"type":"type","text":"hello"}]
    """
    macro_file = _get_macros_dir() / f"{name}.json"
    macro_file.write_text(json.dumps(actions, indent=2), encoding="utf-8")
    return json.dumps({"saved": name, "actions": len(actions), "path": str(macro_file)})


def macro_run(name: str) -> str:
    """Run a previously saved UI macro."""
    macro_file = _get_macros_dir() / f"{name}.json"
    if not macro_file.exists():
        available = [f.stem for f in _get_macros_dir().glob("*.json")]
        return json.dumps({"error": f"Macro '{name}' not found.", "available": available})

    actions = json.loads(macro_file.read_text(encoding="utf-8"))
    pag = _pyautogui()
    results = []

    for action in actions:
        atype = action.get("type", "")
        try:
            if atype == "click":
                r = json.loads(ui_click(action["x"], action["y"], action.get("button", "left")))
            elif atype == "type":
                r = json.loads(ui_type(action["text"]))
            elif atype == "press":
                r = json.loads(ui_press(action["keys"]))
            elif atype == "wait":
                time.sleep(float(action.get("seconds", 0.5)))
                r = {"success": True, "waited": action.get("seconds", 0.5)}
            elif atype == "scroll":
                r = json.loads(ui_scroll(action["x"], action["y"], action.get("amount", 3)))
            else:
                r = {"error": f"Unknown action type: {atype}"}
            results.append({"action": atype, **r})
        except Exception as exc:
            results.append({"action": atype, "error": str(exc)})

    return json.dumps({"macro": name, "steps": len(actions), "results": results})


def get_mouse_position() -> str:
    """Return the current mouse cursor position."""
    pag = _pyautogui()
    if not pag:
        return json.dumps({"error": "pyautogui not installed."})
    pos = pag.position()
    return json.dumps({"x": pos.x, "y": pos.y})


# ── Registration ──────────────────────────────────────────────────────────────

_tools = [
    ("ui_click", ui_click,
     "Click the mouse at specific screen coordinates.",
     {"x": {"type": "integer"}, "y": {"type": "integer"},
      "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
      "clicks": {"type": "integer", "default": 1}},
     ["x", "y"]),
    ("ui_type", ui_type,
     "Type text at the current cursor position in any active application.",
     {"text": {"type": "string"}, "interval": {"type": "number", "default": 0.03}},
     ["text"]),
    ("ui_press", ui_press,
     "Press a keyboard shortcut. Examples: 'ctrl+c', 'alt+f4', 'ctrl+shift+p', 'enter'.",
     {"keys": {"type": "string", "description": "Key combo like 'ctrl+c' or single key like 'enter'"}},
     ["keys"]),
    ("ui_scroll", ui_scroll,
     "Scroll the mouse wheel at a position. Positive amount = scroll up.",
     {"x": {"type": "integer"}, "y": {"type": "integer"}, "amount": {"type": "integer", "default": 3}},
     ["x", "y"]),
    ("ui_find_and_click", ui_find_and_click,
     "Find a UI element by text (using OCR) or image path, then click it.",
     {"target": {"type": "string", "description": "Text to find, or path to reference image"},
      "confidence": {"type": "number", "default": 0.8}},
     ["target"]),
    ("macro_record", macro_record,
     "Save a list of UI actions as a reusable named macro.",
     {"name": {"type": "string"}, "actions": {"type": "array", "items": {"type": "object"}}},
     ["name", "actions"]),
    ("macro_run", macro_run,
     "Run a previously saved UI macro by name.",
     {"name": {"type": "string"}},
     ["name"]),
    ("get_mouse_position", get_mouse_position,
     "Return the current mouse cursor position on screen.",
     {}, []),
]

for _name, _fn, _desc, _props, _required in _tools:
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
        emoji="🖱️",
    )
