"""tools/network_tool.py — Network Guardian for Lucifex.

Controls what the system can access based on context:
- Block distracting sites during focus mode (via hosts file)
- Monitor active connections per process
- Alert on unexpected outbound connections
- Switch configuration on network change

Works cross-platform: Windows (hosts at C:\\Windows\\System32\\drivers\\etc\\hosts),
macOS/Linux (/etc/hosts). Requires elevated privileges for hosts modification.
Gracefully degrades when privileges aren't available.
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from tools.registry import registry

logger = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform == "win32"

_HOSTS_FILE = (
    Path("C:/Windows/System32/drivers/etc/hosts")
    if _IS_WINDOWS
    else Path("/etc/hosts")
)

_LUCIFEX_BLOCK_MARKER = "# lucifex-block"

_FOCUS_PRESETS: dict[str, list[str]] = {
    "deep_work": [
        "twitter.com", "x.com", "reddit.com", "youtube.com",
        "instagram.com", "facebook.com", "tiktok.com", "twitch.tv",
        "news.ycombinator.com", "discord.com",
    ],
    "writing": [
        "twitter.com", "x.com", "reddit.com", "youtube.com",
        "instagram.com", "facebook.com",
    ],
    "meeting": [],  # No blocks during meetings
    "off": [],      # Remove all blocks
}


# ── Hosts File Management ─────────────────────────────────────────────────────

def _read_hosts() -> str:
    try:
        return _HOSTS_FILE.read_text(encoding="utf-8", errors="ignore")
    except PermissionError:
        return ""
    except Exception as exc:
        logger.debug("Cannot read hosts: %s", exc)
        return ""


def _write_hosts(content: str) -> bool:
    try:
        if _IS_WINDOWS:
            # Write via PowerShell (may need admin)
            escaped = content.replace('"', '`"').replace("'", "`'")
            result = subprocess.run(
                ["powershell", "-command",
                 f'Set-Content -Path "{_HOSTS_FILE}" -Value @"\n{escaped}\n"@'],
                capture_output=True, timeout=10
            )
            return result.returncode == 0
        else:
            _HOSTS_FILE.write_text(content, encoding="utf-8")
            return True
    except Exception as exc:
        logger.debug("Cannot write hosts: %s", exc)
        return False


def _get_current_blocks() -> list[str]:
    hosts = _read_hosts()
    blocked = []
    for line in hosts.splitlines():
        if _LUCIFEX_BLOCK_MARKER in line:
            parts = line.split()
            if len(parts) >= 2 and parts[0] == "0.0.0.0":
                blocked.append(parts[1])
    return blocked


def _apply_block_list(domains: list[str]) -> bool:
    """Replace all lucifex-managed blocks with the given domain list."""
    hosts = _read_hosts()
    if not hosts:
        return False

    # Remove all existing lucifex blocks
    clean_lines = [
        line for line in hosts.splitlines()
        if _LUCIFEX_BLOCK_MARKER not in line
    ]

    # Add new blocks
    if domains:
        clean_lines.append(f"\n{_LUCIFEX_BLOCK_MARKER} — managed by Lucifex")
        for domain in domains:
            clean_lines.append(f"0.0.0.0 {domain} {_LUCIFEX_BLOCK_MARKER}")
            clean_lines.append(f"0.0.0.0 www.{domain} {_LUCIFEX_BLOCK_MARKER}")

    return _write_hosts("\n".join(clean_lines))


# ── Network Monitoring ────────────────────────────────────────────────────────

def _get_connections_psutil() -> list[dict]:
    try:
        import psutil
        conns = []
        for proc in psutil.process_iter(["name", "pid"]):
            try:
                for conn in proc.net_connections(kind="inet"):
                    if conn.status == "ESTABLISHED" and conn.raddr:
                        conns.append({
                            "process": proc.info["name"],
                            "pid": proc.info["pid"],
                            "remote_ip": conn.raddr.ip,
                            "remote_port": conn.raddr.port,
                            "local_port": conn.laddr.port if conn.laddr else None,
                        })
            except Exception:
                continue
        return conns
    except ImportError:
        return []


def _get_connections_netstat() -> list[dict]:
    """Fallback: parse netstat output."""
    try:
        if _IS_WINDOWS:
            result = subprocess.run(
                ["netstat", "-no"], capture_output=True, text=True, timeout=5
            )
        else:
            result = subprocess.run(
                ["netstat", "-tnp"], capture_output=True, text=True, timeout=5
            )
        if result.returncode != 0:
            return []

        conns = []
        for line in result.stdout.splitlines():
            if "ESTABLISHED" in line:
                parts = line.split()
                if len(parts) >= 4:
                    remote = parts[2] if not _IS_WINDOWS else parts[2]
                    conns.append({"remote": remote})
        return conns[:20]
    except Exception:
        return []


# ── Tool Implementations ──────────────────────────────────────────────────────

def network_block(domains: str, preset: Optional[str] = None) -> str:
    """Block specific domains or apply a focus preset.

    domains: comma-separated list of domains, or empty string if using preset.
    preset: 'deep_work', 'writing', 'off' (removes all blocks).
    Note: Requires admin/root privileges to modify hosts file.
    """
    if preset and preset in _FOCUS_PRESETS:
        domain_list = _FOCUS_PRESETS[preset]
        ok = _apply_block_list(domain_list)
        if ok:
            return json.dumps({"success": True, "preset": preset, "blocked": len(domain_list)})
        return json.dumps({"success": False, "error": "Could not modify hosts file. Run Lucifex as administrator."})

    if domains:
        domain_list = [d.strip() for d in domains.split(",") if d.strip()]
        current = _get_current_blocks()
        combined = list(set(current + domain_list))
        ok = _apply_block_list(combined)
        return json.dumps({"success": ok, "added": domain_list, "total_blocked": len(combined)})

    return json.dumps({"error": "Provide domains or a preset name."})


def network_unblock(domains: str) -> str:
    """Unblock specific domains from the lucifex block list."""
    to_remove = set(d.strip().lower() for d in domains.split(",") if d.strip())
    current = _get_current_blocks()
    remaining = [d for d in current if d not in to_remove]
    ok = _apply_block_list(remaining)
    return json.dumps({"success": ok, "removed": list(to_remove), "remaining": len(remaining)})


def network_focus(preset: str) -> str:
    """Apply a focus preset to block distracting sites.

    Presets: deep_work (all social/entertainment), writing (social only), off (remove all blocks).
    """
    return network_block("", preset=preset)


def network_status() -> str:
    """Show current blocked domains and active connections."""
    blocked = _get_current_blocks()
    connections = _get_connections_psutil() or _get_connections_netstat()
    return json.dumps({
        "blocked_domains": blocked,
        "active_connections": connections[:15],
        "connection_count": len(connections),
    }, ensure_ascii=False)


def network_monitor_suspicious() -> str:
    """Check for processes making unexpected outbound connections."""
    conns = _get_connections_psutil()
    EXPECTED_PROCESSES = {
        "chrome", "firefox", "safari", "code", "cursor", "python", "node",
        "slack", "discord", "zoom", "teams", "spotify",
    }
    suspicious = [
        c for c in conns
        if c.get("process", "").lower() not in EXPECTED_PROCESSES
        and c.get("remote_port") in {80, 443, 8080, 8443}
    ]
    return json.dumps({
        "suspicious_connections": suspicious[:10],
        "count": len(suspicious),
        "note": "Review any unexpected processes making HTTP/HTTPS connections.",
    })


# ── Registration ──────────────────────────────────────────────────────────────

_tools = [
    ("network_block", network_block,
     "Block specific domains or apply a focus preset. Requires admin privileges.",
     {"domains": {"type": "string", "description": "Comma-separated domains to block"},
      "preset": {"type": "string", "description": "Focus preset: deep_work | writing | off"}},
     []),
    ("network_unblock", network_unblock,
     "Unblock specific domains that were previously blocked.",
     {"domains": {"type": "string", "description": "Comma-separated domains to unblock"}},
     ["domains"]),
    ("network_focus", network_focus,
     "Apply a named focus preset: deep_work (blocks social/entertainment), writing, off (removes all blocks).",
     {"preset": {"type": "string", "enum": ["deep_work", "writing", "meeting", "off"]}},
     ["preset"]),
    ("network_status", network_status,
     "Show currently blocked domains and active network connections per process.",
     {}, []),
    ("network_monitor_suspicious", network_monitor_suspicious,
     "Check for processes making unexpected outbound HTTP/HTTPS connections.",
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
        emoji="🌐",
    )
