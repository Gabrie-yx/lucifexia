"""agent/event_reactor.py — System Event Reactor for Lucifex.

An IFTTT-style engine that reacts to real system events with intelligent
actions. The agent can register triggers that fire when:
- A file is created/modified/deleted in a watched path
- A process spikes CPU or crashes
- Battery drops below a threshold
- A USB device is connected
- Network connectivity changes

Each trigger executes a Python callable or shell command as the reaction.
Triggers are stored persistently and survive agent restarts.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

_reactor_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()
_triggers: list["Trigger"] = []
_triggers_lock = threading.RLock()

_IS_WINDOWS = sys.platform == "win32"
_IS_MAC = sys.platform == "darwin"


# ── Trigger Definition ────────────────────────────────────────────────────────

@dataclass
class Trigger:
    trigger_id: str
    event_type: str          # file_created, file_modified, cpu_spike, battery_low, process_crash, network_change, usb_connected
    condition: dict          # event-specific params: path, process_name, threshold, etc.
    action_type: str         # notify, shell, telegram, log, python
    action_payload: str      # shell command, message, python expression, etc.
    enabled: bool = True
    fired_count: int = 0


# ── Persistent Storage ────────────────────────────────────────────────────────

def _triggers_file() -> Path:
    try:
        from lucifex_constants import get_lucifex_home
        p = Path(get_lucifex_home()) / "event_triggers.json"
    except Exception:
        p = Path.home() / ".lucifex" / "event_triggers.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _save_triggers() -> None:
    with _triggers_lock:
        data = [
            {
                "trigger_id": t.trigger_id,
                "event_type": t.event_type,
                "condition": t.condition,
                "action_type": t.action_type,
                "action_payload": t.action_payload,
                "enabled": t.enabled,
                "fired_count": t.fired_count,
            }
            for t in _triggers
        ]
    _triggers_file().write_text(json.dumps(data, indent=2), encoding="utf-8")


def _load_triggers() -> None:
    f = _triggers_file()
    if not f.exists():
        return
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        with _triggers_lock:
            _triggers.clear()
            for d in data:
                _triggers.append(Trigger(**d))
    except Exception as exc:
        logger.debug("Failed to load triggers: %s", exc)


# ── Action Execution ──────────────────────────────────────────────────────────

def _execute_action(trigger: Trigger, context: dict) -> None:
    """Execute the trigger's action."""
    payload = trigger.action_payload

    try:
        if trigger.action_type == "notify":
            logger.info("EVENT REACTOR [%s]: %s — context=%s", trigger.trigger_id, payload, context)
            _notify_user(payload, context)

        elif trigger.action_type == "shell":
            result = subprocess.run(
                payload, shell=True, capture_output=True, text=True, timeout=30
            )
            logger.info("EVENT REACTOR shell [%s]: exit=%d stdout=%s",
                        trigger.trigger_id, result.returncode, result.stdout[:200])

        elif trigger.action_type == "telegram":
            try:
                from gateway.run import send_proactive_message
                msg = payload.format(**context)
                send_proactive_message(msg)
            except Exception as exc:
                logger.debug("Telegram notification failed: %s", exc)

        elif trigger.action_type == "log":
            logger.warning("EVENT REACTOR [%s]: %s | context=%s", trigger.trigger_id, payload, context)

        elif trigger.action_type == "python":
            exec(payload, {"context": context, "trigger": trigger})  # noqa: S102

    except Exception as exc:
        logger.debug("Action execution failed for trigger %s: %s", trigger.trigger_id, exc)


def _notify_user(message: str, context: dict) -> None:
    """Send a desktop notification (best-effort)."""
    try:
        if _IS_WINDOWS:
            script = f'[System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms"); [System.Windows.Forms.MessageBox]::Show("{message}", "Lucifex Event", "OK", "Information")'
            subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-command", script])
        elif _IS_MAC:
            subprocess.Popen(["osascript", "-e", f'display notification "{message}" with title "Lucifex Event"'])
        else:
            subprocess.Popen(["notify-send", "Lucifex Event", message])
    except Exception:
        pass


# ── Event Checkers ─────────────────────────────────────────────────────────────

_last_battery = None
_last_network = None
_watched_file_mtimes: dict[str, float] = {}


def _check_battery(trigger: Trigger) -> Optional[dict]:
    threshold = trigger.condition.get("threshold", 20)
    try:
        import psutil
        battery = psutil.sensors_battery()
        if battery and not battery.power_plugged:
            pct = battery.percent
            global _last_battery
            if pct <= threshold and (_last_battery is None or _last_battery > threshold):
                _last_battery = pct
                return {"battery_percent": pct, "threshold": threshold}
            _last_battery = pct
    except Exception:
        pass
    return None


def _check_cpu_spike(trigger: Trigger) -> Optional[dict]:
    threshold = trigger.condition.get("threshold", 90)
    duration = trigger.condition.get("duration_seconds", 30)
    process_name = trigger.condition.get("process_name")
    try:
        import psutil
        if process_name:
            for proc in psutil.process_iter(["name", "cpu_percent"]):
                if process_name.lower() in proc.info["name"].lower():
                    cpu = proc.cpu_percent(interval=1)
                    if cpu >= threshold:
                        return {"process": proc.info["name"], "cpu_percent": cpu}
        else:
            cpu = psutil.cpu_percent(interval=1)
            if cpu >= threshold:
                return {"cpu_percent": cpu, "threshold": threshold}
    except Exception:
        pass
    return None


def _check_file_event(trigger: Trigger) -> Optional[dict]:
    path_str = trigger.condition.get("path", "")
    event_type = trigger.event_type  # file_created, file_modified, file_deleted
    path = Path(path_str)

    if not path.exists() and event_type == "file_deleted":
        if path_str in _watched_file_mtimes:
            del _watched_file_mtimes[path_str]
            return {"path": path_str, "event": "deleted"}
        return None

    if not path.exists():
        return None

    if path.is_dir():
        # Watch for new files in directory
        for f in path.iterdir():
            key = str(f)
            mtime = f.stat().st_mtime
            if key not in _watched_file_mtimes and event_type == "file_created":
                _watched_file_mtimes[key] = mtime
                return {"path": key, "event": "created"}
            elif key in _watched_file_mtimes and _watched_file_mtimes[key] != mtime and event_type == "file_modified":
                _watched_file_mtimes[key] = mtime
                return {"path": key, "event": "modified"}
            elif key not in _watched_file_mtimes:
                _watched_file_mtimes[key] = mtime
    else:
        mtime = path.stat().st_mtime
        if path_str not in _watched_file_mtimes:
            _watched_file_mtimes[path_str] = mtime
        elif _watched_file_mtimes[path_str] != mtime and event_type == "file_modified":
            _watched_file_mtimes[path_str] = mtime
            return {"path": path_str, "event": "modified"}

    return None


def _check_network_change(trigger: Trigger) -> Optional[dict]:
    global _last_network
    try:
        import socket
        try:
            socket.setdefaulttimeout(2)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
            current = "connected"
        except Exception:
            current = "disconnected"

        if _last_network is not None and current != _last_network:
            _last_network = current
            return {"status": current, "previous": _last_network}
        _last_network = current
    except Exception:
        pass
    return None


_CHECKER_MAP = {
    "battery_low": _check_battery,
    "cpu_spike": _check_cpu_spike,
    "file_created": _check_file_event,
    "file_modified": _check_file_event,
    "file_deleted": _check_file_event,
    "network_change": _check_network_change,
}


# ── Reactor Loop ──────────────────────────────────────────────────────────────

def _reactor_loop(interval: float = 10.0) -> None:
    logger.info("Event reactor started with %d trigger(s).", len(_triggers))

    while not _stop_event.is_set():
        with _triggers_lock:
            active = [t for t in _triggers if t.enabled]

        for trigger in active:
            try:
                checker = _CHECKER_MAP.get(trigger.event_type)
                if checker:
                    context = checker(trigger)
                    if context:
                        trigger.fired_count += 1
                        _execute_action(trigger, context)
                        _save_triggers()
            except Exception as exc:
                logger.debug("Trigger %s check failed: %s", trigger.trigger_id, exc)

        _stop_event.wait(interval)

    logger.info("Event reactor stopped.")


def start_reactor() -> None:
    """Start the event reactor background thread."""
    global _reactor_thread
    if _reactor_thread and _reactor_thread.is_alive():
        return
    _load_triggers()
    _stop_event.clear()
    _reactor_thread = threading.Thread(target=_reactor_loop, daemon=True, name="event-reactor")
    _reactor_thread.start()


def stop_reactor() -> None:
    _stop_event.set()


# ── Public API ─────────────────────────────────────────────────────────────────

def register_trigger(
    event_type: str,
    condition: dict,
    action_type: str,
    action_payload: str,
    trigger_id: Optional[str] = None,
) -> str:
    """Register a new event trigger. Returns trigger ID."""
    import uuid
    if trigger_id is None:
        trigger_id = str(uuid.uuid4())[:8]

    t = Trigger(
        trigger_id=trigger_id,
        event_type=event_type,
        condition=condition,
        action_type=action_type,
        action_payload=action_payload,
    )
    with _triggers_lock:
        # Remove existing trigger with same ID
        _triggers[:] = [x for x in _triggers if x.trigger_id != trigger_id]
        _triggers.append(t)
    _save_triggers()
    logger.info("Trigger registered: %s [%s] → %s", trigger_id, event_type, action_type)
    return trigger_id


def list_triggers() -> list[dict]:
    with _triggers_lock:
        return [
            {
                "id": t.trigger_id,
                "event": t.event_type,
                "action": t.action_type,
                "enabled": t.enabled,
                "fired": t.fired_count,
            }
            for t in _triggers
        ]


def remove_trigger(trigger_id: str) -> bool:
    with _triggers_lock:
        before = len(_triggers)
        _triggers[:] = [t for t in _triggers if t.trigger_id != trigger_id]
        removed = len(_triggers) < before
    if removed:
        _save_triggers()
    return removed


# Auto-start when imported
start_reactor()
