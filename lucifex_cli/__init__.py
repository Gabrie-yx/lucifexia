"""
Lucifex CLI - Unified command-line interface for Lucifex Agent.

Provides subcommands for:
- lucifex chat          - Interactive chat (same as ./lucifex)
- lucifex gateway       - Run gateway in foreground
- lucifex gateway start - Start gateway service
- lucifex gateway stop  - Stop gateway service
- lucifex setup         - Interactive setup wizard
- lucifex status        - Show status of all components
- lucifex cron          - Manage cron jobs
"""

import os
import sys

__version__ = "0.20.3"
__release_date__ = "2026.7.13"


def _ensure_utf8():
    """Force UTF-8 stdout/stderr to prevent UnicodeEncodeError crashes."""
    repaired = False

    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            encoding = (getattr(stream, "encoding", "") or "").lower().replace("-", "")
            if encoding == "utf8":
                continue

            reconfigure = getattr(stream, "reconfigure", None)
            if callable(reconfigure):
                reconfigure(encoding="utf-8", errors="replace")
                repaired = True
                continue

            new_stream = open(
                stream.fileno(), "w", encoding="utf-8",
                errors="replace", buffering=1, closefd=False,
            )
            setattr(sys, stream_name, new_stream)
            repaired = True
        except (AttributeError, OSError, ValueError):
            pass

    if repaired:
        os.environ.setdefault("PYTHONUTF8", "1")
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")


_ensure_utf8()

# Alias lucifex_cli module to lucifex_cli for seamless backwards compatibility
sys.modules["lucifex_cli"] = sys.modules[__name__]
