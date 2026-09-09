"""Longitudinal memory retrieval for persona-counsel.

Retrieves prior council consensus, persona recommendations, and Coyote dissents
via vsearch (SQLite FTS5 BM25) with fallback to vault review files.
"""

from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Optional

from local_first_common.obsidian import find_vault_root


def get_vsearch_db_path() -> Path:
    """Return path to vsearch SQLite BM25 database."""
    xdg_data = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
    return Path(xdg_data) / "vsearch" / "bm25.db"


def search_council_memory_via_vsearch(
    current_period: str,
    goals_text: str,
    top_k: int = 3,
    db_path: Optional[Path] = None,
) -> list[dict]:
    """Search vsearch for prior council recommendations, dissents, and decisions."""
    path = db_path or get_vsearch_db_path()
    if not path.exists():
        return []

    # Build search query emphasizing council reviews and goal topics
    goal_words = [w for w in re.findall(r"\b[A-Za-z]{3,}\b", goals_text)[:15]]
    terms = ['"council"', '"consensus"', '"recommendation"', '"dissent"'] + [f'"{w}"' for w in goal_words[:5]]
    fts_query = " OR ".join(terms)

    results: list[dict] = []
    try:
        conn = sqlite3.connect(str(path))
        sql = """
            SELECT chunk_id, source_file, breadcrumb, content, bm25(chunks_fts) as rank
            FROM chunks_fts
            WHERE chunks_fts MATCH ?
            ORDER BY rank ASC
            LIMIT ?
        """
        cur = conn.execute(sql, (fts_query, top_k * 4))
        rows = cur.fetchall()
        conn.close()
    except Exception:
        return []

    for _, source_file, breadcrumb, text, rank in rows:
        # Exclude current period
        if current_period and current_period in source_file:
            continue
        # Prioritize files that are actual council reports or reviews
        is_council = (
            "council" in source_file.lower()
            or "review" in source_file.lower()
            or "council" in (breadcrumb or "").lower()
        )
        if not is_council:
            continue

        snippet = " ".join(text.strip().split())
        if len(snippet) > 280:
            snippet = snippet[:280].rsplit(" ", 1)[0] + "…"

        results.append(
            {
                "source_file": source_file,
                "breadcrumb": breadcrumb or "Council Report",
                "snippet": snippet,
                "score": -float(rank),
            }
        )
        if len(results) >= top_k:
            break

    return results


def find_recent_council_reports_on_disk(
    vault_root: Path,
    current_period: str,
    max_reports: int = 2,
) -> list[dict]:
    """Fallback: scan vault for recent council report files."""
    if not vault_root.exists():
        return []

    found = []
    for path in sorted(vault_root.glob("Goals/**/reviews/*-council.md"), reverse=True):
        stem = path.stem.replace("-council", "")
        if stem == current_period:
            continue
        try:
            content = path.read_text(encoding="utf-8")
            snippet = _extract_report_summary(content)
            try:
                rel_path = str(path.relative_to(vault_root))
            except ValueError:
                rel_path = path.name
            found.append(
                {
                    "source_file": rel_path,
                    "breadcrumb": f"Prior Council ({stem})",
                    "snippet": snippet,
                    "score": 1.0,
                }
            )
            if len(found) >= max_reports:
                break
        except Exception:
            continue

    return found


def _extract_report_summary(content: str, max_chars: int = 300) -> str:
    """Extract consensus and priorities or first paragraph from a report."""
    match = re.search(r"##\s*Consensus\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
    if match:
        text = " ".join(match.group(1).strip().split())
        if len(text) > max_chars:
            return text[:max_chars].rsplit(" ", 1)[0] + "…"
        return text

    lines = []
    in_fm = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped == "---":
            in_fm = not in_fm
            continue
        if in_fm or not stripped or stripped.startswith("#"):
            continue
        lines.append(stripped)
        if len(" ".join(lines)) > max_chars:
            break
    text = " ".join(lines)
    if len(text) > max_chars:
        return text[:max_chars].rsplit(" ", 1)[0] + "…"
    return text


def get_council_memory(
    current_period: str,
    goals_text: str,
    vault_root: Optional[Path] = None,
    top_k: int = 3,
    db_path: Optional[Path] = None,
) -> list[dict]:
    """Retrieve prior council recommendations and decisions using vsearch with disk fallback."""
    results = search_council_memory_via_vsearch(
        current_period, goals_text, top_k=top_k, db_path=db_path
    )
    if results:
        return results

    root = vault_root or find_vault_root()
    return find_recent_council_reports_on_disk(root, current_period, max_reports=top_k)


def format_council_memory(memory_items: list[dict]) -> str:
    """Format memory items into prompt-ready markdown."""
    if not memory_items:
        return ""
    lines = []
    for i, item in enumerate(memory_items, start=1):
        src = item["source_file"]
        bc = f" [{item['breadcrumb']}]" if item.get("breadcrumb") else ""
        lines.append(f"{i}. `{src}`{bc}:\n   \"{item['snippet']}\"")
    return "\n\n".join(lines)
