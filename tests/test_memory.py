"""Tests for longitudinal memory retrieval in persona-counsel."""

import sqlite3

from persona_counsel.council import _build_evaluation_prompt
from persona_counsel.memory import (
    _extract_report_summary,
    find_recent_council_reports_on_disk,
    format_council_memory,
    get_council_memory,
    get_vsearch_db_path,
    search_council_memory_via_vsearch,
)


def test_get_vsearch_db_path(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    path = get_vsearch_db_path()
    assert path == tmp_path / "vsearch" / "bm25.db"


def test_search_council_memory_via_vsearch_missing_db(tmp_path):
    missing_db = tmp_path / "bm25.db"
    results = search_council_memory_via_vsearch("2026-03", "Ship product", db_path=missing_db)
    assert results == []


def test_search_council_memory_via_vsearch_hits(tmp_path):
    db_file = tmp_path / "bm25.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute(
        """
        CREATE VIRTUAL TABLE chunks_fts USING fts5(
            chunk_id UNINDEXED,
            source_file UNINDEXED,
            breadcrumb UNINDEXED,
            content
        );
        """
    )
    # Insert test data:
    # 1. Past council review with matching term
    conn.execute(
        "INSERT INTO chunks_fts VALUES (?, ?, ?, ?)",
        (
            "c1",
            "Goals/2026/reviews/2026-02-council.md",
            "Consensus > Priorities",
            "Council consensus: focus on shipping the core offline engine first.",
        ),
    )
    # 2. Current period (should be excluded)
    conn.execute(
        "INSERT INTO chunks_fts VALUES (?, ?, ?, ?)",
        (
            "c2",
            "Goals/2026/reviews/2026-03-council.md",
            "Consensus",
            "Council consensus: current month goals.",
        ),
    )
    # 3. Not a council review (should be excluded)
    conn.execute(
        "INSERT INTO chunks_fts VALUES (?, ?, ?, ?)",
        (
            "c3",
            "Notes/random-article.md",
            "Article",
            "A consensus recommendation was reached on completely unrelated matters.",
        ),
    )
    conn.commit()
    conn.close()

    results = search_council_memory_via_vsearch(
        current_period="2026-03",
        goals_text="Shipping the core engine",
        top_k=5,
        db_path=db_file,
    )
    assert len(results) == 1
    assert results[0]["source_file"] == "Goals/2026/reviews/2026-02-council.md"
    assert "core offline engine" in results[0]["snippet"]
    assert results[0]["breadcrumb"] == "Consensus > Priorities"


def test_find_recent_council_reports_on_disk(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    reviews_dir = vault / "Goals" / "2026" / "reviews"
    reviews_dir.mkdir(parents=True)

    # Current month
    (reviews_dir / "2026-03-council.md").write_text(
        "## Consensus\nCurrent review content.", encoding="utf-8"
    )
    # Previous month
    (reviews_dir / "2026-02-council.md").write_text(
        "## Consensus\nPrevious review: stick to 3 goals and say no to distractions.",
        encoding="utf-8",
    )
    # Earlier month
    (reviews_dir / "2026-01-council.md").write_text(
        "---\ntitle: Jan Review\n---\nJanuary initial council notes.",
        encoding="utf-8",
    )

    results = find_recent_council_reports_on_disk(vault, current_period="2026-03", max_reports=2)
    assert len(results) == 2
    stems = [r["source_file"] for r in results]
    assert any("2026-02-council.md" in s for s in stems)
    assert not any("2026-03-council.md" in s for s in stems)
    assert "stick to 3 goals" in results[0]["snippet"]


def test_extract_report_summary():
    content_with_consensus = """
# Council Report

## Consensus
Solomon and Ada agreed to consolidate tasks. Silas raised risk concerns.

## Persona Evaluations
### Solomon
Everything is good.
"""
    summary = _extract_report_summary(content_with_consensus)
    assert "Solomon and Ada agreed" in summary
    assert "### Solomon" not in summary

    content_without_consensus = """---
tags: [review]
---
# Council Report

First paragraph describing general outcome and progress.
"""
    summary2 = _extract_report_summary(content_without_consensus)
    assert "First paragraph describing" in summary2


def test_get_council_memory_fallback(tmp_path):
    vault = tmp_path / "vault"
    reviews_dir = vault / "Goals" / "2026" / "reviews"
    reviews_dir.mkdir(parents=True)
    (reviews_dir / "2026-01-council.md").write_text(
        "## Consensus\nPrior consensus advice.", encoding="utf-8"
    )

    # Missing db path forces disk fallback
    results = get_council_memory(
        current_period="2026-02",
        goals_text="Work on goals",
        vault_root=vault,
        db_path=tmp_path / "nonexistent.db",
    )
    assert len(results) == 1
    assert "Prior consensus advice" in results[0]["snippet"]


def test_format_council_memory():
    assert format_council_memory([]) == ""

    items = [
        {
            "source_file": "Goals/2026/reviews/2026-02-council.md",
            "breadcrumb": "Consensus",
            "snippet": "Don't overload sprint.",
            "score": 0.9,
        },
        {
            "source_file": "Goals/2026/reviews/2026-01-council.md",
            "breadcrumb": None,
            "snippet": "Watch out for burn-out.",
            "score": 0.8,
        },
    ]
    formatted = format_council_memory(items)
    assert "1. `Goals/2026/reviews/2026-02-council.md` [Consensus]:" in formatted
    assert '"Don\'t overload sprint."' in formatted
    assert "2. `Goals/2026/reviews/2026-01-council.md`:" in formatted
    assert '"Watch out for burn-out."' in formatted


def test_build_evaluation_prompt_with_council_memory():
    goals = "Ship offline search"
    memory_text = "1. `Goals/2026-01-council.md`: Prior recommendation"
    prompt = _build_evaluation_prompt(goals, None, council_memory_text=memory_text)
    assert "HISTORICAL COUNCIL MEMORY" in prompt
    assert memory_text in prompt
