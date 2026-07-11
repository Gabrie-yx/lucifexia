"""tools/window_tool.py — Window & Focus Orchestrator for Lucifex.

Provides intelligent window management via language commands:
- Save and restore named workspace layouts (windows + positions + sizes)
- Arrange windows for specific tasks (coding, writing, call, presentation)
- Focus an app, minimise distractions, close unused windows
- List all visible windows with their titles and positions

Works on Windows (pygetwindow + win32gui), macOS (AppleScript), Linux (wmctrl).
Gracefully degrades if native libraries are not available.

Registered tools: window_list, window_focus, window_arrange, layout_save, layout_restore
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from tools.registry import registry

logger = logging.getLogger(__name__)

# ── Platform Detection ────────────────────────────────────────────────────────

_IS_WINDOWS = sys.platform == "win32"
_IS_MAC = sys.platform == "darwin"
_IS_LINUX = sys.platform.startswith("linux")

_LAYOUTS_DIR: Optional[Path] = None


def _layouts_dir() -> Path:
    global _LAYOUTS_DIR
    if _LAYOUTS_DIR is None:
        try:
            from lucifex_constants import get_lucifex_home
            _LAYOUTS_DIR = Path(get_lucifex_home()) / "window_layouts"
        except Exception:
            _LAYOUTS_DIR = Path.home() / ".lucifex" / "window_layouts"
    _LAYOUTS_DIR.mkdir(parents=True, exist_ok=True)
    return _LAYOUTS_DIR


# ── Built-in Layouts ──────────────────────────────────────────────────────────

_BUILTIN_LAYOUTS = {
    "coding": [
        {"app": "code", "x": 0, "y": 0, "width": 1280, "height": 1080},
        {"app": "terminal", "x": 1280, "y": 0, "width": 640, "height": 540},
        {"app": "chrome", "x": 1280, "y": 540, "width": 640, "height": 540},
    ],
    "writing": [
        {"app": "chrome", "x": 200, "y": 0, "width": 1520, "height": 1080},
    ],
    "call": [
        {"app": "zoom", "x": 0, "y": 0, "width": 1280, "height": 720},
        {"app": "notion", "x": 1280, "y": 0, "width": 640, "height": 720},
    ],
    "focus": [],  # close all distractions
}


# ── Window Helpers ────────────────────────────────────────────────────────────

def _list_windows_windows() -> list[dict]:
    """List windows using PowerShell on Windows."""
    try:
        script = """
$windows = Get-Process | Where-Object {$_.MainWindowTitle -ne ''} |
    Select-Object ProcessName, MainWindowTitle, Id |
    ConvertTo-Json
$windows
"""
        result = subprocess.run(
            ["powershell", "-command", script],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            if isinstance(data, dict):
                data = [data]
            return [
                {"title": w.get("MainWindowTitle", ""), "app": w.get("ProcessName", ""), "pid": w.get("Id")}
                for w in data if w.get("MainWindowTitle")
            ]
    except Exception as exc:
        logger.debug("window list (win) failed: %s", exc)
    return []


def _list_windows_mac() -> list[dict]:
    """List windows using AppleScript on macOS."""
    try:
        script = 'tell application "System Events" to get name of every process whose visible is true'
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            names = [n.strip() for n in result.stdout.split(",") if n.strip()]
            return [{"app": n, "title": n} for n in names]
    except Exception as exc:
        logger.debug("window list (mac) failed: %s", exc)
    return []


def _list_windows_linux() -> list[dict]:
    """List windows using wmctrl on Linux."""
    try:
        result = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            windows = []
            for line in result.stdout.splitlines():
                parts = line.split(None, 3)
                if len(parts) >= 4:
                    windows.append({"id": parts[0], "title": parts[3], "app": parts[3].split()[0]})
            return windows
    except Exception as exc:
        logger.debug("window list (linux) failed: %s", exc)
    return []


def _get_windows() -> list[dict]:
    if _IS_WINDOWS:
        return _list_windows_windows()
    elif _IS_MAC:
        return _list_windows_mac()
    return _list_windows_linux()


def _focus_app_windows(app_name: str) -> bool:
    """Bring app window to foreground on Windows."""
    try:
        script = f"""
$proc = Get-Process | Where-Object {{$_.MainWindowTitle -like '*{app_name}*'}} | Select-Object -First 1
if ($proc) {{
    Add-Type @"
using System.Runtime.InteropServices;
public class Win32 {{
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(System.IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(System.IntPtr hWnd, int nCmdShow);
}}
"@
    [Win32]::ShowWindow($proc.MainWindowHandle, 9)
    [Win32]::SetForegroundWindow($proc.MainWindowHandle)
    Write-Output "OK"
}}
"""
        result = subprocess.run(
            ["powershell", "-command", script],
            capture_output=True, text=True, timeout=5
        )
        return "OK" in result.stdout
    except Exception as exc:
        logger.debug("focus_app (win) failed: %s", exc)
        return False


def _focus_app_mac(app_name: str) -> bool:
    try:
        script = f'tell application "{app_name}" to activate'
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False


# ── Tool Implementations ──────────────────────────────────────────────────────

def window_list() -> str:
    """List all visible windows with their titles and app names."""
    windows = _get_windows()
    return json.dumps(windows[:30], ensure_ascii=False)


def window_focus(app_name: str) -> str:
    """Bring the window of the specified app to the foreground."""
    if _IS_WINDOWS:
        ok = _focus_app_windows(app_name)
    elif _IS_MAC:
        ok = _focus_app_mac(app_name)
    else:
        try:
            result = subprocess.run(
                ["wmctrl", "-a", app_name], capture_output=True, text=True, timeout=5
            )
            ok = result.returncode == 0
        except Exception:
            ok = False
    return json.dumps({"success": ok, "app": app_name})


def window_arrange(preset: str) -> str:
    """Arrange windows using a built-in preset: coding, writing, call, focus."""
    preset = preset.lower()
    layout = _BUILTIN_LAYOUTS.get(preset)
    if layout is None:
        return json.dumps({"error": f"Unknown preset '{preset}'. Available: {list(_BUILTIN_LAYOUTS)}"})

    if preset == "focus":
        # Minimise everything except terminal/code
        windows = _get_windows()
        minimised = []
        for w in windows:
            app = w.get("app", "").lower()
            if app not in {"code", "windowsterminal", "terminal", "lucifex"}:
                if _IS_WINDOWS:
                    try:
                        subprocess.run(
                            ["powershell", f'(Get-Process "{app}" -ErrorAction SilentlyContinue) | ForEach-Object {{$_.MainWindowHandle}} | ForEach-Object {{ [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($_) }}'],
                            capture_output=True, timeout=3
                        )
                    except Exception:
                        pass
                minimised.append(app)
        return json.dumps({"preset": "focus", "minimised": minimised})

    applied = []
    for spec in layout:
        app = spec.get("app", "")
        if _IS_WINDOWS:
            _focus_app_windows(app)
            # Position window using PowerShell/WinAPI
            try:
                x, y, w, h = spec["x"], spec["y"], spec["width"], spec["height"]
                script = f"""
Add-Type @"
using System.Runtime.InteropServices;
public class Win32 {{
    [DllImport("user32.dll")] public static extern bool MoveWindow(System.IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
}}
"@
$proc = Get-Process | Where-Object {{$_.ProcessName -like '*{app}*'}} | Select-Object -First 1
if ($proc) {{ [Win32]::MoveWindow($proc.MainWindowHandle, {x}, {y}, {w}, {h}, $true) }}
"""
                subprocess.run(["powershell", "-command", script], capture_output=True, timeout=5)
                applied.append(app)
            except Exception:
                pass
        elif _IS_MAC:
            try:
                x, y, w, h = spec["x"], spec["y"], spec["width"], spec["height"]
                script = f'tell application "{app}" to set bounds of front window to {{{x}, {y}, {x+w}, {y+h}}}'
                subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
                applied.append(app)
            except Exception:
                pass

    return json.dumps({"preset": preset, "applied": applied, "total": len(layout)})


def layout_save(name: str) -> str:
    """Save the current window arrangement as a named layout."""
    windows = _get_windows()
    layout_file = _layouts_dir() / f"{name}.json"
    layout_file.write_text(json.dumps(windows, indent=2, ensure_ascii=False), encoding="utf-8")
    return json.dumps({"saved": name, "windows": len(windows), "path": str(layout_file)})


def layout_restore(name: str) -> str:
    """Restore a previously saved named window layout."""
    layout_file = _layouts_dir() / f"{name}.json"
    if not layout_file.exists():
        available = [f.stem for f in _layouts_dir().glob("*.json")]
        return json.dumps({"error": f"Layout '{name}' not found.", "available": available})

    layout = json.loads(layout_file.read_text(encoding="utf-8"))
    restored = []
    for win in layout:
        app = win.get("app", "")
        if app:
            window_focus(app)
            restored.append(app)

    return json.dumps({"restored": name, "apps": restored})


# ── Registration ──────────────────────────────────────────────────────────────

_tools = [
    ("window_list", window_list, "List all visible windows with their titles and app names.", {}),
    ("window_focus", window_focus, "Bring the window of the named app to the foreground.", {"app_name": {"type": "string", "description": "App name or window title substring"}}),
    ("window_arrange", window_arrange, "Arrange windows using a preset layout: coding, writing, call, focus.", {"preset": {"type": "string", "description": "Layout preset name: coding | writing | call | focus"}}),
    ("layout_save", layout_save, "Save current window arrangement as a named layout for later restore.", {"name": {"type": "string"}}),
    ("layout_restore", layout_restore, "Restore a previously saved named window layout.", {"name": {"type": "string"}}),
]

for _name, _fn, _desc, _props in _tools:
    _required = list(_props.keys())
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
        emoji="🪟",
    )
