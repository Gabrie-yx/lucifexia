"""agent/ontology_builder.py — Personal Knowledge Ontology for Lucifex. (Feature 31)

Builds a dense personal ontology of the user's domain over time:
- Learns their specific terminology, naming conventions, architecture
- Compresses domain knowledge so the agent stops needing re-explanation
- Detects terminology used inconsistently across sessions
- Maps concepts to their own explanations: "X means Y in this project"
- The agent's contextual startup cost drops each week

Stored as a flat SQLite + FTS table. Exports to Obsidian as a knowledge map.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)
_lock = threading.RLock()
_db_path: Optional[Path] = None

# Patterns that signal a concept definition
_DEFINITION_PATTERNS = [
    (r"(?:the |a |an )?(\w[\w\s]{2,30}) (?:is|are|means?|refers? to)\s+(.{10,200})", "definition"),
    (r"(?:we|I) call (?:it|this|them|that) (?:the |a )?[\"']?(\w[\w\s]{2,30})[\"']?\s+(?:because|when|to|for)\s+(.{10,150})", "naming"),
    (r"(\w[\w\s]{2,30}) (?:in|within|for) (?:this|our|the) (?:project|system|codebase|app) (?:is|means?|refers? to)\s+(.{10,200})", "project_term"),
]
_DEF_RE = [(re.compile(p, re.IGNORECASE), t) for p, t in _DEFINITION_PATTERNS]


def _get_db() -> Path:
    global _db_path
    if _db_path is None:
        try:
            from lucifex_constants import get_lucifex_home
            _db_path = Path(get_lucifex_home()) / "ontology.db"
        except Exception:
            _db_path = Path.home() / ".lucifex" / "ontology.db"
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    return _db_path


@contextmanager
def _conn():
    with _lock:
        con = sqlite3.connect(_get_db(), check_same_thread=False)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS concepts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                term        TEXT NOT NULL,
                definition  TEXT NOT NULL,
                concept_type TEXT,
                session_id  TEXT,
                usage_count INTEGER DEFAULT 1,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL,
                UNIQUE(term)
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS concepts_fts
            USING fts5(id UNINDEXED, term, definition);
            CREATE TABLE IF NOT EXISTS term_usages (
                term        TEXT NOT NULL,
                context     TEXT,
                session_id  TEXT,
                used_at     TEXT NOT NULL
            );
        """)


def extract_and_store_concepts(text: str, session_id: str = "") -> int:
    """Extract concept definitions from text and store them."""
    init_db()
    stored = 0
    for pattern, concept_type in _DEF_RE:
        for match in pattern.finditer(text):
            groups = match.groups()
            if len(groups) >= 2:
                term = groups[0].strip().lower()[:60]
                definition = groups[1].strip()[:300]
                if len(term) < 3 or len(definition) < 10:
                    continue
                _upsert_concept(term, definition, concept_type, session_id)
                stored += 1
    return stored


def _upsert_concept(term: str, definition: str, concept_type: str, session_id: str) -> None:
    with _conn() as con:
        existing = con.execute("SELECT id, usage_count FROM concepts WHERE term=?", (term,)).fetchone()
        if existing:
            con.execute("""
                UPDATE concepts SET definition=?, usage_count=usage_count+1, updated_at=?
                WHERE term=?
            """, (definition, _now(), term))
        else:
            cur = con.execute("""
                INSERT INTO concepts (term, definition, concept_type, session_id, created_at, updated_at)
                VALUES (?,?,?,?,?,?)
            """, (term, definition, concept_type, session_id, _now(), _now()))
            con.execute(
                "INSERT INTO concepts_fts(id, term, definition) VALUES (?,?,?)",
                (cur.lastrowid, term, definition),
            )


def record_term_usage(term: str, context: str, session_id: str = "") -> None:
    """Record that a term was used in a given context."""
    init_db()
    with _conn() as con:
        con.execute(
            "INSERT INTO term_usages (term, context, session_id, used_at) VALUES (?,?,?,?)",
            (term.lower()[:60], context[:100], session_id, _now()),
        )
        con.execute(
            "UPDATE concepts SET usage_count=usage_count+1, updated_at=? WHERE term=?",
            (_now(), term.lower()),
        )


def find_concept(term: str) -> Optional[dict]:
    """Look up a concept by term."""
    init_db()
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM concepts WHERE term=?", (term.lower(),)
        ).fetchone()
        return dict(row) if row else None


def detect_inconsistent_usage(term: str) -> Optional[str]:
    """Detect if a term is being used inconsistently across sessions."""
    init_db()
    with _conn() as con:
        usages = con.execute(
            "SELECT context FROM term_usages WHERE term=? ORDER BY used_at DESC LIMIT 10",
            (term.lower(),),
        ).fetchall()
    if len(usages) < 3:
        return None

    contexts = [u["context"] for u in usages]
    # Simple heuristic: high variance in context length signals inconsistency
    lengths = [len(c) for c in contexts]
    avg = sum(lengths) / len(lengths)
    variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)
    if variance > 2000:
        return f"Term '{term}' appears to be used inconsistently across contexts."
    return None


def get_ontology_summary() -> dict:
    """Return a summary of the current personal ontology."""
    init_db()
    with _conn() as con:
        total = con.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
        top_terms = con.execute(
            "SELECT term, usage_count FROM concepts ORDER BY usage_count DESC LIMIT 10"
        ).fetchall()
        by_type = con.execute(
            "SELECT concept_type, COUNT(*) as cnt FROM concepts GROUP BY concept_type"
        ).fetchall()
    return {
        "total_concepts": total,
        "top_terms": [dict(r) for r in top_terms],
        "by_type": {r["concept_type"]: r["cnt"] for r in by_type},
    }


def get_context_prefix(max_concepts: int = 15) -> str:
    """Return a compact context string of key concepts for injection into prompts."""
    init_db()
    with _conn() as con:
        rows = con.execute(
            "SELECT term, definition FROM concepts ORDER BY usage_count DESC LIMIT ?",
            (max_concepts,),
        ).fetchall()
    if not rows:
        return ""
    items = [f"- **{r['term']}**: {r['definition'][:80]}" for r in rows]
    return "**Project Ontology (key terms):**\n" + "\n".join(items)


def export_to_obsidian() -> Optional[str]:
    """Export the ontology to Obsidian as a knowledge map."""
    try:
        from tools.playbook_tool import _resolve_obsidian_vault_path
        vault = _resolve_obsidian_vault_path()
        onto_dir = vault / "Ontology"
        onto_dir.mkdir(parents=True, exist_ok=True)
        out = onto_dir / "project-ontology.md"

        init_db()
        with _conn() as con:
            rows = con.execute(
                "SELECT * FROM concepts ORDER BY usage_count DESC"
            ).fetchall()

        lines = [
            "---\ntitle: Project Ontology\nsource: agent-ontology-builder\n---\n",
            "# Project Ontology\n",
            f"*{len(rows)} concepts learned — auto-maintained by Lucifex*\n",
        ]
        by_type: dict = {}
        for row in rows:
            t = row["concept_type"] or "general"
            by_type.setdefault(t, []).append(row)

        for ctype, concepts in sorted(by_type.items()):
            lines.append(f"\n## {ctype.replace('_', ' ').title()}\n")
            for c in concepts:
                lines.append(f"### {c['term'].title()}")
                lines.append(f"{c['definition']}")
                lines.append(f"*Used {c['usage_count']} times*\n")

        out.write_text("\n".join(lines), encoding="utf-8")
        return str(out)
    except Exception as exc:
        logger.debug("Ontology export failed: %s", exc)
        return None
