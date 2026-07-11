"""agent/hypothesis_engine.py — Autonomous hypothesis generation and testing.

When Lucifex reads source code or analyses a system, it generates hypotheses
about latent problems (performance bottlenecks, missing indexes, potential
bugs) and silently tests them using terminal commands or static analysis.

Confirmed hypotheses are written to the Obsidian vault. The agent presents
findings proactively, not just reactively.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ── Generation ────────────────────────────────────────────────────────────────

def generate_hypotheses_from_file(
    file_path: str,
    file_content: str,
    session_id: str = "",
) -> list[int]:
    """Analyse a source file and register hypotheses about potential issues.

    Returns list of hypothesis IDs added.
    """
    from agent.inner_life import add_hypothesis

    hypotheses = _pattern_scan(file_path, file_content)
    ids = []
    for h in hypotheses:
        try:
            hid = add_hypothesis(
                hypothesis=h["hypothesis"],
                target_file=file_path,
                target_function=h.get("target_function", ""),
            )
            ids.append(hid)
            logger.debug("Hypothesis registered [%d]: %s", hid, h["hypothesis"][:60])
        except Exception as exc:
            logger.debug("Failed to register hypothesis: %s", exc)
    return ids


def _pattern_scan(file_path: str, content: str) -> list[dict]:
    """Static pattern analysis to generate hypotheses."""
    hypotheses = []
    lines = content.splitlines()
    path = Path(file_path)

    # 1. Missing index hint for SQLite queries with WHERE clauses
    if re.search(r"SELECT\s+.*WHERE\s+\w+\s*=", content, re.IGNORECASE):
        if "CREATE INDEX" not in content and "index" not in content.lower():
            hypotheses.append({
                "hypothesis": (
                    f"`{path.name}` executes filtered SELECT queries but no index definition "
                    f"was found. This may cause full table scans on large datasets."
                ),
                "target_function": "",
            })

    # 2. N+1 query patterns in loops
    for i, line in enumerate(lines):
        if re.search(r"for .+ in .+:", line) and i + 1 < len(lines):
            next_lines = "\n".join(lines[i+1:i+4])
            if re.search(r"\.(query|execute|find|get|fetch)\(", next_lines):
                hypotheses.append({
                    "hypothesis": (
                        f"`{path.name}` line ~{i+1}: possible N+1 query pattern detected — "
                        f"a database call inside a loop may cause performance degradation."
                    ),
                    "target_function": line.strip()[:60],
                })
                break  # One per file is enough

    # 3. Bare except clauses that swallow errors silently
    bare_excepts = [(i+1, l) for i, l in enumerate(lines) if re.search(r"except\s*:", l)]
    if bare_excepts:
        line_num, line_txt = bare_excepts[0]
        hypotheses.append({
            "hypothesis": (
                f"`{path.name}` line {line_num}: bare `except:` clause detected. "
                f"This may silently swallow critical errors and make debugging very difficult."
            ),
            "target_function": line_txt.strip()[:60],
        })

    # 4. Large functions (> 60 lines) that are hard to test
    func_starts = [(i, l) for i, l in enumerate(lines) if re.match(r"\s*def \w+", l)]
    for j in range(len(func_starts) - 1):
        start, (start_line, func_line) = j, func_starts[j]
        end_line = func_starts[j+1][0]
        length = end_line - start_line
        if length > 60:
            func_name = re.search(r"def (\w+)", func_line)
            name = func_name.group(1) if func_name else "unknown"
            hypotheses.append({
                "hypothesis": (
                    f"`{path.name}` function `{name}` spans ~{length} lines. "
                    f"Functions this large are hard to unit-test and often contain implicit coupling."
                ),
                "target_function": name,
            })
            break

    return hypotheses[:3]  # Max 3 hypotheses per file


# ── Testing ───────────────────────────────────────────────────────────────────

def test_pending_hypotheses(max_tests: int = 2) -> list[dict]:
    """Test pending hypotheses using available tools. Returns results."""
    from agent.inner_life import get_pending_hypotheses, update_hypothesis

    pending = get_pending_hypotheses()
    results = []
    for h in pending[:max_tests]:
        evidence, status = _run_hypothesis_test(h)
        try:
            update_hypothesis(h["id"], status=status, evidence=evidence)
        except Exception as exc:
            logger.debug("Failed to update hypothesis: %s", exc)

        if status == "confirmed":
            _write_hypothesis_to_obsidian(h, evidence)
            results.append({"hypothesis": h["hypothesis"], "status": status, "evidence": evidence})
            logger.info("Hypothesis CONFIRMED: %s", h["hypothesis"][:60])
        else:
            results.append({"hypothesis": h["hypothesis"], "status": status})

    return results


def _run_hypothesis_test(hypothesis: dict) -> tuple[str, str]:
    """Run a safe terminal check to validate or refute the hypothesis.

    Returns (evidence_text, status) where status is 'confirmed' or 'refuted'.
    """
    hyp_text = hypothesis.get("hypothesis", "")
    target = hypothesis.get("target_file", "")

    try:
        import subprocess
        # Choose test command based on hypothesis type
        if "N+1 query" in hyp_text or "loop" in hyp_text.lower():
            # Can't test dynamically without running the app — mark as pending with note
            return "Static analysis only — runtime profiling required.", "pending"

        if "bare `except:`" in hyp_text and target:
            result = subprocess.run(
                ["grep", "-n", "except:", target],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout:
                return f"Confirmed via grep:\n{result.stdout[:300]}", "confirmed"
            return "Not found in current file state.", "refuted"

        if "full table scan" in hyp_text.lower() and target:
            result = subprocess.run(
                ["grep", "-in", "CREATE INDEX", target],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0 or not result.stdout.strip():
                return "No index definitions found in file — hypothesis plausible.", "confirmed"
            return "Index definitions found — hypothesis refuted.", "refuted"

    except Exception as exc:
        logger.debug("Hypothesis test failed: %s", exc)

    return "Could not run automated test.", "pending"


def _write_hypothesis_to_obsidian(hypothesis: dict, evidence: str) -> None:
    """Write a confirmed hypothesis as a discovery to Obsidian."""
    try:
        from tools.playbook_tool import _resolve_obsidian_vault_path
        from datetime import datetime
        import re as _re

        vault = _resolve_obsidian_vault_path()
        disc_dir = vault / "Discoveries"
        disc_dir.mkdir(parents=True, exist_ok=True)

        slug = _re.sub(r"\W+", "-", hypothesis["hypothesis"][:40]).lower()
        date = datetime.now().strftime("%Y-%m-%d")
        fname = f"{date}-hypothesis-{slug[:35]}.md"

        content = f"""---
title: "Hypothesis Confirmed: {hypothesis['hypothesis'][:60]}"
category: hypothesis
impact: medium
created: {datetime.now().isoformat()}
source: agent-hypothesis-engine
tags:
  - hypothesis
  - autonomous-analysis
related_files:
  - {hypothesis.get('target_file', '')}
---

## Hypothesis

{hypothesis['hypothesis']}

## Evidence

{evidence}

## Recommendation

Review `{Path(hypothesis.get('target_file', 'the file')).name}` and address this issue to improve reliability and performance.
"""
        (disc_dir / fname).write_text(content, encoding="utf-8")
        logger.info("Hypothesis discovery written: %s", fname)
    except Exception as exc:
        logger.debug("Failed to write hypothesis discovery: %s", exc)
