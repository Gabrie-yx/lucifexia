"""tools/meeting_tool.py — Meeting Prep Orchestrator for Lucifex.

Integrates with the user's calendar to prepare the workspace before meetings:
- Reads ICS calendar files or Google Calendar API
- 5 minutes before a meeting: opens relevant docs, arranges windows, silences notifications
- During: transcribes via microphone (if available)
- After: summarises and extracts action items → Obsidian

Sources supported:
  1. Local .ics file (any calendar export)
  2. Google Calendar API (if credentials configured)
  3. Manual event registration via tool

Registered tools: meeting_list, meeting_prep, meeting_register
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from tools.registry import registry

logger = logging.getLogger(__name__)

_db_path: Optional[Path] = None
_lock = threading.RLock()


def _get_db() -> Path:
    global _db_path
    if _db_path is None:
        try:
            from lucifex_constants import get_lucifex_home
            _db_path = Path(get_lucifex_home()) / "meetings.db"
        except Exception:
            _db_path = Path.home() / ".lucifex" / "meetings.db"
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    return _db_path


def _init_db() -> None:
    with sqlite3.connect(_get_db()) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS meetings (
                id          TEXT PRIMARY KEY,
                title       TEXT NOT NULL,
                start_time  TEXT NOT NULL,
                end_time    TEXT,
                location    TEXT,
                description TEXT,
                attendees   TEXT,
                status      TEXT DEFAULT 'upcoming',
                notes       TEXT,
                created_at  TEXT NOT NULL
            )
        """)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── ICS Parsing ───────────────────────────────────────────────────────────────

def _parse_ics(ics_path: Path) -> list[dict]:
    """Parse an ICS calendar file and return upcoming events."""
    try:
        content = ics_path.read_text(encoding="utf-8", errors="ignore")
        events = []
        current: dict = {}
        in_vevent = False

        for line in content.splitlines():
            if line == "BEGIN:VEVENT":
                in_vevent = True
                current = {}
            elif line == "END:VEVENT":
                in_vevent = False
                if current.get("DTSTART"):
                    events.append(current)
                current = {}
            elif in_vevent and ":" in line:
                key, _, value = line.partition(":")
                key = key.split(";")[0]  # Strip TZID params
                current[key] = value

        # Parse and filter upcoming events (next 7 days)
        upcoming = []
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=7)

        for ev in events:
            raw_start = ev.get("DTSTART", "")
            try:
                # Handle YYYYMMDDTHHMMSSZ and YYYYMMDD formats
                if "T" in raw_start:
                    ds = raw_start.replace("Z", "+00:00")[:19]
                    start = datetime.fromisoformat(ds).replace(tzinfo=timezone.utc)
                else:
                    start = datetime(int(raw_start[:4]), int(raw_start[4:6]), int(raw_start[6:8]), tzinfo=timezone.utc)

                if now <= start <= cutoff:
                    upcoming.append({
                        "title": ev.get("SUMMARY", "Untitled"),
                        "start_time": start.isoformat(),
                        "location": ev.get("LOCATION", ""),
                        "description": ev.get("DESCRIPTION", "")[:200],
                        "attendees": ev.get("ATTENDEE", ""),
                    })
            except Exception:
                continue

        return sorted(upcoming, key=lambda e: e["start_time"])
    except Exception as exc:
        logger.debug("ICS parse failed: %s", exc)
        return []


def _load_from_ics_files() -> list[dict]:
    """Look for ICS files in common locations."""
    common_paths = [
        Path.home() / "Downloads",
        Path.home() / "Documents",
        Path.home() / "Desktop",
    ]
    events = []
    for folder in common_paths:
        if folder.exists():
            for ics in folder.glob("*.ics"):
                events.extend(_parse_ics(ics))
    return events


def _load_from_google_calendar() -> list[dict]:
    """Load events from Google Calendar API if credentials are configured."""
    try:
        from lucifex_constants import get_lucifex_home
        cred_file = Path(get_lucifex_home()) / "google_calendar_token.json"
        if not cred_file.exists():
            return []

        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_file(str(cred_file))
        service = build("calendar", "v3", credentials=creds)

        now = datetime.now(timezone.utc).isoformat()
        cutoff = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

        result = service.events().list(
            calendarId="primary",
            timeMin=now,
            timeMax=cutoff,
            maxResults=20,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = []
        for item in result.get("items", []):
            start = item["start"].get("dateTime", item["start"].get("date", ""))
            events.append({
                "title": item.get("summary", "Untitled"),
                "start_time": start,
                "location": item.get("location", ""),
                "description": item.get("description", "")[:200],
                "attendees": ", ".join(
                    a.get("email", "") for a in item.get("attendees", [])
                ),
            })
        return events
    except Exception as exc:
        logger.debug("Google Calendar load failed: %s", exc)
        return []


# ── DB Operations ─────────────────────────────────────────────────────────────

def _sync_events_to_db(events: list[dict]) -> int:
    """Sync events list to local DB. Returns count added."""
    _init_db()
    import hashlib
    added = 0
    with sqlite3.connect(_get_db()) as con:
        for ev in events:
            mid = hashlib.md5(f"{ev['title']}{ev['start_time']}".encode()).hexdigest()[:12]
            existing = con.execute("SELECT id FROM meetings WHERE id=?", (mid,)).fetchone()
            if not existing:
                con.execute("""
                    INSERT INTO meetings (id, title, start_time, end_time, location, description, attendees, created_at)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (mid, ev["title"], ev["start_time"], ev.get("end_time", ""),
                      ev.get("location", ""), ev.get("description", ""),
                      ev.get("attendees", ""), _now()))
                added += 1
    return added


def _get_upcoming_meetings(hours_ahead: int = 24) -> list[dict]:
    _init_db()
    cutoff = (datetime.now(timezone.utc) + timedelta(hours=hours_ahead)).isoformat()
    now = _now()
    with sqlite3.connect(_get_db()) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT * FROM meetings WHERE start_time BETWEEN ? AND ? AND status='upcoming' ORDER BY start_time ASC",
            (now, cutoff),
        ).fetchall()
        return [dict(r) for r in rows]


# ── Meeting Prep ──────────────────────────────────────────────────────────────

def _prepare_workspace_for_meeting(meeting: dict) -> dict:
    """Arrange the workspace for an upcoming meeting."""
    actions = []

    # 1. Apply "call" window layout
    try:
        from tools.window_tool import window_arrange
        result = json.loads(window_arrange("call"))
        actions.append(f"Window layout: {result}")
    except Exception as exc:
        actions.append(f"Window layout failed: {exc}")

    # 2. Block distracting sites
    try:
        from tools.network_tool import network_focus
        network_focus("meeting")
        actions.append("Network: focus mode activated")
    except Exception as exc:
        actions.append(f"Network focus failed: {exc}")

    # 3. Generate meeting brief
    brief = _generate_meeting_brief(meeting)
    actions.append(f"Brief generated: {len(brief)} chars")

    return {"meeting": meeting["title"], "actions": actions, "brief": brief}


def _generate_meeting_brief(meeting: dict) -> str:
    """Generate a concise meeting brief from description and attendees."""
    title = meeting.get("title", "Meeting")
    desc = meeting.get("description", "")
    attendees = meeting.get("attendees", "")
    start = meeting.get("start_time", "")

    lines = [f"# Meeting Brief: {title}", ""]
    if start:
        try:
            dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            lines.append(f"**When:** {dt.strftime('%A %B %d at %H:%M')}")
        except Exception:
            lines.append(f"**When:** {start}")
    if meeting.get("location"):
        lines.append(f"**Where:** {meeting['location']}")
    if attendees:
        lines.append(f"**Attendees:** {attendees[:200]}")
    if desc:
        lines.append(f"\n**Agenda:**\n{desc}")
    lines.append("\n---\n*Generated by Lucifex Meeting Prep*")
    return "\n".join(lines)


def _write_brief_to_obsidian(meeting: dict, brief: str) -> Optional[str]:
    try:
        from tools.playbook_tool import _resolve_obsidian_vault_path
        vault = _resolve_obsidian_vault_path()
        meetings_dir = vault / "Meetings"
        meetings_dir.mkdir(parents=True, exist_ok=True)
        date = datetime.now().strftime("%Y-%m-%d")
        slug = re.sub(r"\W+", "-", meeting.get("title", "meeting"))[:30]
        out = meetings_dir / f"{date}-{slug}.md"
        out.write_text(brief, encoding="utf-8")
        return str(out)
    except Exception as exc:
        logger.debug("Failed to write meeting brief to Obsidian: %s", exc)
        return None


# ── Tool Implementations ──────────────────────────────────────────────────────

def meeting_list(hours_ahead: int = 24) -> str:
    """List upcoming meetings from calendar in the next N hours."""
    # Try to load from sources
    events = _load_from_google_calendar() or _load_from_ics_files()
    if events:
        _sync_events_to_db(events)

    meetings = _get_upcoming_meetings(hours_ahead)
    return json.dumps({
        "meetings": meetings,
        "count": len(meetings),
        "sources_checked": ["google_calendar", "local_ics_files", "local_db"],
    }, ensure_ascii=False, default=str)


def meeting_prep(meeting_id: str) -> str:
    """Prepare the workspace for a specific meeting.

    Opens relevant documents, arranges windows, generates a meeting brief,
    and saves it to Obsidian.
    """
    _init_db()
    with sqlite3.connect(_get_db()) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT * FROM meetings WHERE id=?", (meeting_id,)).fetchone()

    if not row:
        # Try by title substring
        with sqlite3.connect(_get_db()) as con:
            con.row_factory = sqlite3.Row
            row = con.execute(
                "SELECT * FROM meetings WHERE title LIKE ? ORDER BY start_time ASC LIMIT 1",
                (f"%{meeting_id}%",),
            ).fetchone()

    if not row:
        return json.dumps({"error": f"Meeting '{meeting_id}' not found. Use meeting_list to see available meetings."})

    meeting = dict(row)
    result = _prepare_workspace_for_meeting(meeting)
    brief_path = _write_brief_to_obsidian(meeting, result.get("brief", ""))
    result["brief_saved_to"] = brief_path
    return json.dumps(result, ensure_ascii=False, default=str)


def meeting_register(
    title: str,
    start_time: str,
    end_time: str = "",
    location: str = "",
    description: str = "",
    attendees: str = "",
) -> str:
    """Manually register a meeting in Lucifex's calendar.

    start_time format: 'YYYY-MM-DD HH:MM' or ISO 8601.
    """
    _init_db()
    import hashlib

    # Normalise time
    try:
        if "T" not in start_time:
            start_time = start_time.replace(" ", "T")
            if "+" not in start_time and "Z" not in start_time:
                start_time += ":00"
        dt = datetime.fromisoformat(start_time)
        start_iso = dt.isoformat()
    except Exception:
        start_iso = start_time

    mid = hashlib.md5(f"{title}{start_iso}".encode()).hexdigest()[:12]
    with sqlite3.connect(_get_db()) as con:
        con.execute("""
            INSERT OR REPLACE INTO meetings
            (id, title, start_time, end_time, location, description, attendees, created_at)
            VALUES (?,?,?,?,?,?,?,?)
        """, (mid, title, start_iso, end_time, location, description, attendees, _now()))

    return json.dumps({
        "success": True,
        "id": mid,
        "title": title,
        "start_time": start_iso,
    })


# ── Registration ──────────────────────────────────────────────────────────────

_tools = [
    ("meeting_list", meeting_list,
     "List upcoming meetings from your calendar. Checks Google Calendar, local ICS files, and the Lucifex meeting DB.",
     {"hours_ahead": {"type": "integer", "default": 24, "description": "How many hours ahead to look"}},
     []),
    ("meeting_prep", meeting_prep,
     "Prepare the workspace for a meeting: arrange windows, generate a brief, and save it to Obsidian.",
     {"meeting_id": {"type": "string", "description": "Meeting ID from meeting_list, or title substring"}},
     ["meeting_id"]),
    ("meeting_register", meeting_register,
     "Manually register a meeting in Lucifex so it can prep the workspace automatically.",
     {
         "title": {"type": "string"},
         "start_time": {"type": "string", "description": "Format: 'YYYY-MM-DD HH:MM' or ISO 8601"},
         "end_time": {"type": "string"},
         "location": {"type": "string"},
         "description": {"type": "string"},
         "attendees": {"type": "string", "description": "Comma-separated names or emails"},
     },
     ["title", "start_time"]),
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
        emoji="📅",
    )
