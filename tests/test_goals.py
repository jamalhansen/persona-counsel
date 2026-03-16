"""Tests for goals.py -- loading monthly notes from vault."""
import pytest

from persona_counsel.goals import current_month, goals_output_path, load_goals


def _write_goals(vault_root, month: str, content: str) -> None:
    year = month[:4]
    path = vault_root / "Goals" / year / "_monthly" / f"{month}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestLoadGoals:
    def test_loads_existing_note(self, tmp_path):
        _write_goals(tmp_path, "2026-03", "# March Goals\n\nShip something good.")
        content = load_goals("2026-03", vault_root=tmp_path)
        assert "Ship something good" in content

    def test_strips_frontmatter(self, tmp_path):
        _write_goals(tmp_path, "2026-03", "---\ntitle: March\n---\n# March\nBody here.")
        content = load_goals("2026-03", vault_root=tmp_path)
        assert "title: March" not in content
        assert "Body here" in content

    def test_missing_note_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="2026-03"):
            load_goals("2026-03", vault_root=tmp_path)

    def test_error_shows_expected_path(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="_monthly"):
            load_goals("2026-03", vault_root=tmp_path)


class TestCurrentMonth:
    def test_returns_yyyy_mm_format(self):
        m = current_month()
        assert len(m) == 7
        assert m[4] == "-"
        assert m[:4].isdigit()
        assert m[5:].isdigit()


class TestGoalsOutputPath:
    def test_correct_path(self, tmp_path):
        path = goals_output_path("2026-03", vault_root=tmp_path)
        assert path == tmp_path / "Goals" / "2026" / "_monthly" / "reviews" / "2026-03-council.md"

    def test_different_year(self, tmp_path):
        path = goals_output_path("2025-11", vault_root=tmp_path)
        assert "2025" in str(path)
        assert "2025-11-council.md" in str(path)
