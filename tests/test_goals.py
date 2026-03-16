"""Tests for goals.py -- loading notes from vault for all scope types."""
import pytest

from persona_counsel.goals import (
    annual_output_path,
    current_month,
    current_week,
    current_year,
    goals_output_path,
    load_annual_goals,
    load_council_report,
    load_goals,
    load_weekly_goals,
    weekly_output_path,
)


def _write_note(path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestLoadGoals:
    def test_loads_existing_note(self, tmp_path):
        path = tmp_path / "Goals" / "2026" / "_monthly" / "2026-03.md"
        _write_note(path, "# March Goals\n\nShip something good.")
        content = load_goals("2026-03", vault_root=tmp_path)
        assert "Ship something good" in content

    def test_strips_frontmatter(self, tmp_path):
        path = tmp_path / "Goals" / "2026" / "_monthly" / "2026-03.md"
        _write_note(path, "---\ntitle: March\n---\n# March\nBody here.")
        content = load_goals("2026-03", vault_root=tmp_path)
        assert "title: March" not in content
        assert "Body here" in content

    def test_missing_note_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="2026-03"):
            load_goals("2026-03", vault_root=tmp_path)

    def test_error_shows_expected_path(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="_monthly"):
            load_goals("2026-03", vault_root=tmp_path)


class TestLoadWeeklyGoals:
    def test_loads_existing_note(self, tmp_path):
        path = tmp_path / "Goals" / "2026" / "_weekly" / "2026-W10.md"
        _write_note(path, "## Week 10 Goals\n\nFocus on writing.")
        content = load_weekly_goals("2026-W10", vault_root=tmp_path)
        assert "Focus on writing" in content

    def test_strips_frontmatter(self, tmp_path):
        path = tmp_path / "Goals" / "2026" / "_weekly" / "2026-W10.md"
        _write_note(path, "---\ntitle: Week 10\n---\nBody here.")
        content = load_weekly_goals("2026-W10", vault_root=tmp_path)
        assert "Body here" in content
        assert "title: Week 10" not in content

    def test_missing_note_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="2026-W10"):
            load_weekly_goals("2026-W10", vault_root=tmp_path)


class TestLoadAnnualGoals:
    def test_loads_existing_note(self, tmp_path):
        path = tmp_path / "Goals" / "2026" / "_annual" / "2026.md"
        _write_note(path, "## 2026 Goals\n\nBuild more things.")
        content = load_annual_goals("2026", vault_root=tmp_path)
        assert "Build more things" in content

    def test_missing_note_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="2026"):
            load_annual_goals("2026", vault_root=tmp_path)


class TestCurrentPeriod:
    def test_current_month_format(self):
        m = current_month()
        assert len(m) == 7
        assert m[4] == "-"
        assert m[:4].isdigit() and m[5:].isdigit()

    def test_current_week_format(self):
        w = current_week()
        assert "-W" in w
        year, wnum = w.split("-W")
        assert len(year) == 4 and year.isdigit()
        assert 1 <= int(wnum) <= 53

    def test_current_year_format(self):
        y = current_year()
        assert len(y) == 4 and y.isdigit()


class TestOutputPaths:
    def test_monthly_output_path(self, tmp_path):
        path = goals_output_path("2026-03", vault_root=tmp_path)
        assert path == tmp_path / "Goals" / "2026" / "_monthly" / "reviews" / "2026-03-council.md"

    def test_weekly_output_path(self, tmp_path):
        path = weekly_output_path("2026-W10", vault_root=tmp_path)
        assert path == tmp_path / "Goals" / "2026" / "_weekly" / "reviews" / "2026-W10-council.md"

    def test_annual_output_path(self, tmp_path):
        path = annual_output_path("2026", vault_root=tmp_path)
        assert path == tmp_path / "Goals" / "2026" / "_annual" / "reviews" / "2026-council.md"

    def test_different_year_in_monthly_path(self, tmp_path):
        path = goals_output_path("2025-11", vault_root=tmp_path)
        assert "2025" in str(path) and "2025-11-council.md" in str(path)


class TestLoadCouncilReport:
    def _write_report(self, tmp_path, period: str, content: str) -> None:
        """Write a fake council report at the expected output path."""
        if "-W" in period:
            path = tmp_path / "Goals" / period[:4] / "_weekly" / "reviews" / f"{period}-council.md"
        elif len(period) == 4:
            path = tmp_path / "Goals" / period / "_annual" / "reviews" / f"{period}-council.md"
        else:
            path = tmp_path / "Goals" / period[:4] / "_monthly" / "reviews" / f"{period}-council.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_loads_monthly_report(self, tmp_path):
        self._write_report(tmp_path, "2026-02", "# February Council\nConsensus: great month.")
        content = load_council_report("2026-02", vault_root=tmp_path)
        assert "Consensus: great month" in content

    def test_loads_weekly_report(self, tmp_path):
        self._write_report(tmp_path, "2026-W10", "# Week 10 Council\nFocus was good.")
        content = load_council_report("2026-W10", vault_root=tmp_path)
        assert "Focus was good" in content

    def test_loads_annual_report(self, tmp_path):
        self._write_report(tmp_path, "2025", "# 2025 Council\nBig year.")
        content = load_council_report("2025", vault_root=tmp_path)
        assert "Big year" in content

    def test_missing_report_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="2026-02"):
            load_council_report("2026-02", vault_root=tmp_path)

    def test_invalid_period_raises(self, tmp_path):
        with pytest.raises(ValueError, match="Cannot determine period type"):
            load_council_report("not-a-period", vault_root=tmp_path)
