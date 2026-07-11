"""agent/isomorphism_engine.py — Cross-domain pattern transfer for Lucifex.

When the agent solves a problem, it extracts an abstract pattern (the
structural shape of the solution) and stores it in a pattern library.
When a new problem arrives, it searches for isomorphic patterns and adapts
the known solution to the new context.

This enables genuine cross-domain reasoning: a rate-limiting solution from
a web API can inspire a throttling solution for a background worker.
A cache invalidation strategy from Redis can map to a local file cache.

Pattern library is stored in SQLite and grows over time.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_lock = threading.RLock()
_db_path: Optional[Path] = None


def _get_db() -> Path:
    global _db_path
    if _db_path is None:
        try:
            from lucifex_constants import get_lucifex_home
            _db_path = Path(get_lucifex_home()) / "isomorphisms.db"
        except Exception:
            _db_path = Path.home() / ".lucifex" / "isomorphisms.db"
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    return _db_path


@contextmanager
def _conn():
    db = _get_db()
    with _lock:
        con = sqlite3.connect(db, check_same_thread=False)
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
            CREATE TABLE IF NOT EXISTS patterns (
                id              TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                abstract_shape  TEXT NOT NULL,
                domain          TEXT,
                problem_type    TEXT,
                solution_sketch TEXT,
                keywords        TEXT,
                used_count      INTEGER DEFAULT 0,
                created_at      TEXT NOT NULL
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS patterns_fts
            USING fts5(id UNINDEXED, name, abstract_shape, keywords, domain);
        """)
        _seed_builtin_patterns(con)


def _seed_builtin_patterns(con) -> None:
    """Seed the library with fundamental software patterns."""
    builtins = [
        {
            "id": "rate_limit",
            "name": "Rate Limiter / Token Bucket",
            "abstract_shape": "Limit(resource, max_units, window) → allow if tokens_available > 0 else reject/wait",
            "domain": "systems",
            "problem_type": "resource_control",
            "solution_sketch": "Maintain a counter of consumed units. Refill at fixed rate. Reject requests that exceed the limit.",
            "keywords": "rate limit throttle quota token bucket sliding window",
        },
        {
            "id": "circuit_breaker",
            "name": "Circuit Breaker",
            "abstract_shape": "State(closed→open→half-open) transitions on error_rate > threshold",
            "domain": "systems",
            "problem_type": "fault_tolerance",
            "solution_sketch": "Track failure rate. Open circuit (fail fast) when threshold exceeded. Half-open after timeout to probe recovery.",
            "keywords": "circuit breaker fault tolerance resilience cascade failure",
        },
        {
            "id": "cache_aside",
            "name": "Cache-Aside / Lazy Loading",
            "abstract_shape": "read(key) → if cache_hit: return cache[key] else: v=source(key); cache[key]=v; return v",
            "domain": "data",
            "problem_type": "performance",
            "solution_sketch": "Check cache first. On miss, load from source and populate cache. On write, invalidate or update cache entry.",
            "keywords": "cache performance latency hit miss invalidation TTL",
        },
        {
            "id": "event_sourcing",
            "name": "Event Sourcing",
            "abstract_shape": "state = reduce(events, initial_state) — never mutate, only append",
            "domain": "data",
            "problem_type": "state_management",
            "solution_sketch": "Store sequence of events, not current state. Reconstruct state by replaying events. Enables time travel and audit.",
            "keywords": "event sourcing cqrs audit log replay immutable history",
        },
        {
            "id": "bulkhead",
            "name": "Bulkhead Isolation",
            "abstract_shape": "Partition(resources) → failure in partition A cannot exhaust resources of partition B",
            "domain": "systems",
            "problem_type": "isolation",
            "solution_sketch": "Assign fixed resource pools (threads, connections) per consumer. One misbehaving consumer cannot starve others.",
            "keywords": "bulkhead isolation partition resource pool thread pool connection pool",
        },
        {
            "id": "saga",
            "name": "Saga Pattern (Distributed Transactions)",
            "abstract_shape": "sequence(local_tx) where each tx has a compensating_tx for rollback",
            "domain": "distributed",
            "problem_type": "consistency",
            "solution_sketch": "Break distributed transaction into local transactions with compensating actions. On failure, run compensating transactions in reverse.",
            "keywords": "saga distributed transaction compensation rollback microservices",
        },
        {
            "id": "backpressure",
            "name": "Backpressure / Flow Control",
            "abstract_shape": "producer.rate = f(consumer.capacity) — slow producer when consumer is overwhelmed",
            "domain": "systems",
            "problem_type": "flow_control",
            "solution_sketch": "Signal slowdown from consumer to producer. Drop, buffer, or throttle when queue depth exceeds threshold.",
            "keywords": "backpressure flow control queue overflow producer consumer reactive",
        },
        {
            "id": "observer",
            "name": "Observer / Pub-Sub",
            "abstract_shape": "subject.notify_all(event) → observers react independently, decoupled from subject",
            "domain": "design",
            "problem_type": "decoupling",
            "solution_sketch": "Subject maintains subscriber list. On state change, broadcast event. Observers register/unregister independently.",
            "keywords": "observer pubsub event listener callback reactive notification",
        },
    ]

    for p in builtins:
        existing = con.execute("SELECT id FROM patterns WHERE id=?", (p["id"],)).fetchone()
        if not existing:
            con.execute("""
                INSERT INTO patterns (id, name, abstract_shape, domain, problem_type, solution_sketch, keywords, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (p["id"], p["name"], p["abstract_shape"], p["domain"],
                  p.get("problem_type", ""), p.get("solution_sketch", ""), p.get("keywords", ""), _now()))
            con.execute("""
                INSERT INTO patterns_fts (id, name, abstract_shape, keywords, domain)
                VALUES (?, ?, ?, ?, ?)
            """, (p["id"], p["name"], p["abstract_shape"], p.get("keywords", ""), p["domain"]))


def add_pattern(
    name: str,
    abstract_shape: str,
    domain: str = "general",
    problem_type: str = "",
    solution_sketch: str = "",
    keywords: str = "",
) -> str:
    """Add a new pattern to the library. Returns pattern ID."""
    import re
    pattern_id = re.sub(r"\W+", "_", name.lower())[:40]
    init_db()
    with _conn() as con:
        con.execute("""
            INSERT OR REPLACE INTO patterns
            (id, name, abstract_shape, domain, problem_type, solution_sketch, keywords, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (pattern_id, name, abstract_shape, domain, problem_type, solution_sketch, keywords, _now()))
        con.execute("""
            INSERT OR REPLACE INTO patterns_fts (id, name, abstract_shape, keywords, domain)
            VALUES (?, ?, ?, ?, ?)
        """, (pattern_id, name, abstract_shape, keywords, domain))
    return pattern_id


def find_similar_patterns(problem_description: str, limit: int = 3) -> list[dict]:
    """Find patterns isomorphic to the described problem."""
    init_db()

    # FTS search
    try:
        words = [w for w in problem_description.split() if len(w) > 3][:8]
        query = " OR ".join(words)
        with _conn() as con:
            rows = con.execute("""
                SELECT p.* FROM patterns p
                JOIN patterns_fts f ON p.id = f.id
                WHERE patterns_fts MATCH ?
                ORDER BY p.used_count DESC
                LIMIT ?
            """, (query, limit)).fetchall()
            if rows:
                return [dict(r) for r in rows]
    except Exception:
        pass

    # Fallback: keyword overlap
    with _conn() as con:
        rows = con.execute("SELECT * FROM patterns ORDER BY used_count DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def extract_and_store_pattern(
    problem: str,
    solution: str,
    domain: str = "general",
) -> Optional[str]:
    """Use AI to extract an abstract pattern from a problem/solution pair and store it."""
    try:
        from agent.oneshot import run_oneshot
        prompt = f"""Extract the abstract pattern from this problem/solution pair.

Problem: {problem[:400]}
Solution: {solution[:600]}

Return a JSON object with these fields:
{{
  "name": "Short pattern name (e.g. 'Retry with Exponential Backoff')",
  "abstract_shape": "Abstract formula: X(params) → outcome when condition",
  "problem_type": "One of: performance, fault_tolerance, consistency, decoupling, flow_control, resource_control, state_management, isolation",
  "keywords": "space-separated keywords for search",
  "solution_sketch": "2-3 sentence description of the general solution approach"
}}

Return ONLY the JSON object, no explanation."""

        result = run_oneshot(prompt, max_tokens=300)
        if not result:
            return None

        import re
        match = re.search(r"\{.*\}", result, re.DOTALL)
        if not match:
            return None

        data = json.loads(match.group())
        pattern_id = add_pattern(
            name=data.get("name", "Unnamed Pattern"),
            abstract_shape=data.get("abstract_shape", ""),
            domain=domain,
            problem_type=data.get("problem_type", ""),
            solution_sketch=data.get("solution_sketch", ""),
            keywords=data.get("keywords", ""),
        )
        logger.info("Pattern extracted and stored: %s", data.get("name", "unnamed"))
        return pattern_id
    except Exception as exc:
        logger.debug("Pattern extraction failed: %s", exc)
        return None


def apply_pattern_to_problem(problem: str, pattern_id: str) -> Optional[str]:
    """Adapt a known pattern to a new problem using AI."""
    init_db()
    with _conn() as con:
        row = con.execute("SELECT * FROM patterns WHERE id=?", (pattern_id,)).fetchone()
        if not row:
            return None
        pattern = dict(row)
        # Increment usage counter
        con.execute("UPDATE patterns SET used_count=used_count+1 WHERE id=?", (pattern_id,))

    try:
        from agent.oneshot import run_oneshot
        prompt = f"""Apply this abstract pattern to the new problem.

Pattern: {pattern['name']}
Abstract shape: {pattern['abstract_shape']}
General solution: {pattern['solution_sketch']}

New problem: {problem[:500]}

Adapt the pattern to this specific problem. Be concrete — use the actual names, types,
and constraints from the new problem. Return a specific, implementable solution.
Maximum 300 words."""
        return run_oneshot(prompt, max_tokens=400)
    except Exception as exc:
        logger.debug("Pattern application failed: %s", exc)
        return None


def find_and_apply_best_pattern(problem: str) -> Optional[dict]:
    """Find the most relevant pattern and apply it to the problem.

    Returns {"pattern_name": ..., "adapted_solution": ...} or None.
    """
    candidates = find_similar_patterns(problem, limit=1)
    if not candidates:
        return None

    best = candidates[0]
    solution = apply_pattern_to_problem(problem, best["id"])
    if not solution:
        return None

    return {
        "pattern_name": best["name"],
        "abstract_shape": best["abstract_shape"],
        "adapted_solution": solution,
        "domain": best["domain"],
    }
