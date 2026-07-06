"""Resolve LUCIFEX_HOME for standalone skill scripts.

Skill scripts may run outside the Lucifex process (e.g. system Python,
nix env, CI) where ``lucifex_constants`` is not importable.  This module
provides the same ``get_lucifex_home()`` and ``display_lucifex_home()``
contracts as ``lucifex_constants`` without requiring it on ``sys.path``.

When ``lucifex_constants`` IS available it is used directly so that any
future enhancements (profile resolution, Docker detection, etc.) are
picked up automatically.  The fallback path replicates the core logic
from ``lucifex_constants.py`` using only the stdlib.

All scripts under ``google-workspace/scripts/`` should import from here
instead of duplicating the ``LUCIFEX_HOME = Path(os.getenv(...))`` pattern.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from lucifex_constants import display_lucifex_home as display_lucifex_home
    from lucifex_constants import get_lucifex_home as get_lucifex_home
except (ModuleNotFoundError, ImportError):

    def get_lucifex_home() -> Path:
        """Return the Lucifex home directory (default: ~/.lucifex).

        Mirrors ``lucifex_constants.get_lucifex_home()``."""
        val = os.environ.get("LUCIFEX_HOME", "").strip()
        return Path(val) if val else Path.home() / ".lucifex"

    def display_lucifex_home() -> str:
        """Return a user-friendly ``~/``-shortened display string.

        Mirrors ``lucifex_constants.display_lucifex_home()``."""
        home = get_lucifex_home()
        try:
            return "~/" + str(home.relative_to(Path.home()))
        except ValueError:
            return str(home)
