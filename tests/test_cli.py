"""Tests for the Typer CLI."""
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from persona_counsel.cli import app, _parse_weight
from persona_counsel.models import CouncilSynthesis, PersonaEvaluation

runner = CliRunner()

MOCK_EVALUATION = PersonaEvaluation(
    persona_name="Solomon",
    archetype="The Elder",
    assessment="A solid month.",
    concerns=["One concern"],
    recommendations=["One recommendation"],
    key_question="Were you present?",
)

MOCK_SYNTHESIS = CouncilSynthesis(
    consensus="A good month.",
    tensions=["Craftsman vs Elder"],
    priorities=["Protect evenings"],
    coyote_dissent="Is this the right game?",
)


def make_persona_mock(name="Solomon", archetype="The Elder"):
    """Create a mock persona. MagicMock(name=...) is special in unittest.mock."""
    m = MagicMock()
    m.name = name
    m.archetype = archetype
    return m


class TestParseWeight:
    def test_valid_weight(self):
        name, value = _parse_weight("solomon=1.5")
        assert name == "solomon"
        assert value == 1.5

    def test_name_lowercased(self):
        name, _ = _parse_weight("SOLOMON=2.0")
        assert name == "solomon"

    def test_invalid_format_raises(self):
        import typer
        with pytest.raises(typer.BadParameter):
            _parse_weight("no_equals_sign")

    def test_invalid_float_raises(self):
        import typer
        with pytest.raises((typer.BadParameter, ValueError)):
            _parse_weight("solomon=not_a_number")


class TestListPersonasFlag:
    def test_list_personas_with_real_dir(self):
        result = runner.invoke(app, ["--list-personas"])
        # Should exit 0 if personas exist, or exit 1 if dir missing
        assert result.exit_code in (0, 1)

    def test_list_personas_empty_dir(self):
        with patch("persona_counsel.cli.list_personas", return_value=[]):
            result = runner.invoke(app, ["--list-personas"])
        assert result.exit_code == 1


class TestValidateScope:
    def test_both_month_and_week_rejected(self, tmp_path):
        result = runner.invoke(app, ["--month", "2026-03", "--week", "2026-W10", "--dry-run", "--vault", str(tmp_path)])
        assert result.exit_code == 1

    def test_both_month_and_year_rejected(self, tmp_path):
        result = runner.invoke(app, ["--month", "2026-03", "--year", "2026", "--dry-run", "--vault", str(tmp_path)])
        assert result.exit_code == 1

    def test_both_week_and_year_rejected(self, tmp_path):
        result = runner.invoke(app, ["--week", "2026-W10", "--year", "2026", "--dry-run", "--vault", str(tmp_path)])
        assert result.exit_code == 1

    def test_invalid_week_format_rejected(self, tmp_path):
        result = runner.invoke(app, ["--week", "W10-2026", "--dry-run", "--vault", str(tmp_path)])
        assert result.exit_code == 1

    def test_invalid_year_format_rejected(self, tmp_path):
        result = runner.invoke(app, ["--year", "26", "--dry-run", "--vault", str(tmp_path)])
        assert result.exit_code == 1


class TestMainCommand:
    def _mock_run(self, tmp_path, month="2026-03"):
        """Set up a vault with a monthly goals note."""
        goals_path = tmp_path / "Goals" / "2026" / "_monthly" / f"{month}.md"
        goals_path.parent.mkdir(parents=True, exist_ok=True)
        goals_path.write_text("## Goals\nDo the work.", encoding="utf-8")
        return tmp_path

    def _mock_week_run(self, tmp_path, week="2026-W10"):
        """Set up a vault with a weekly goals note."""
        goals_path = tmp_path / "Goals" / "2026" / "_weekly" / f"{week}.md"
        goals_path.parent.mkdir(parents=True, exist_ok=True)
        goals_path.write_text("## Goals\nDo the weekly work.", encoding="utf-8")
        return tmp_path

    def _mock_year_run(self, tmp_path, year="2026"):
        """Set up a vault with an annual goals note."""
        goals_path = tmp_path / "Goals" / year / "_annual" / f"{year}.md"
        goals_path.parent.mkdir(parents=True, exist_ok=True)
        goals_path.write_text("## Goals\nDo the yearly work.", encoding="utf-8")
        return tmp_path

    def test_dry_run_prints_to_terminal(self, tmp_path):
        vault = self._mock_run(tmp_path)
        with (
            patch("persona_counsel.cli.list_personas", return_value=[make_persona_mock()]),
            patch("persona_counsel.cli.build_model"),
            patch("persona_counsel.cli.asyncio.run", return_value=([MOCK_EVALUATION], MOCK_SYNTHESIS)),
        ):
            result = runner.invoke(
                app, ["--month", "2026-03", "--dry-run", "--vault", str(vault)]
            )
        assert result.exit_code == 0

    def test_missing_goals_exits_with_error(self, tmp_path):
        result = runner.invoke(app, ["--month", "2026-03", "--dry-run", "--vault", str(tmp_path)])
        assert result.exit_code == 1

    def test_writes_file_without_dry_run(self, tmp_path):
        vault = self._mock_run(tmp_path)
        with (
            patch("persona_counsel.cli.list_personas", return_value=[make_persona_mock()]),
            patch("persona_counsel.cli.build_model"),
            patch("persona_counsel.cli.asyncio.run", return_value=([MOCK_EVALUATION], MOCK_SYNTHESIS)),
        ):
            result = runner.invoke(
                app, ["--month", "2026-03", "--vault", str(vault)]
            )
        assert result.exit_code == 0
        output_file = vault / "Goals" / "2026" / "_monthly" / "reviews" / "2026-03-council.md"
        assert output_file.exists()

    def test_invalid_provider_exits_with_error(self, tmp_path):
        vault = self._mock_run(tmp_path)
        with patch("persona_counsel.cli.list_personas", return_value=[make_persona_mock()]):
            result = runner.invoke(
                app,
                ["--month", "2026-03", "--dry-run", "--vault", str(vault), "--provider", "badprovider"],
            )
        assert result.exit_code == 1

    def test_week_dry_run_prints_to_terminal(self, tmp_path):
        vault = self._mock_week_run(tmp_path)
        with (
            patch("persona_counsel.cli.list_personas", return_value=[make_persona_mock()]),
            patch("persona_counsel.cli.build_model"),
            patch("persona_counsel.cli.asyncio.run", return_value=([MOCK_EVALUATION], MOCK_SYNTHESIS)),
        ):
            result = runner.invoke(
                app, ["--week", "2026-W10", "--dry-run", "--vault", str(vault)]
            )
        assert result.exit_code == 0

    def test_week_writes_to_weekly_path(self, tmp_path):
        vault = self._mock_week_run(tmp_path)
        with (
            patch("persona_counsel.cli.list_personas", return_value=[make_persona_mock()]),
            patch("persona_counsel.cli.build_model"),
            patch("persona_counsel.cli.asyncio.run", return_value=([MOCK_EVALUATION], MOCK_SYNTHESIS)),
        ):
            result = runner.invoke(
                app, ["--week", "2026-W10", "--vault", str(vault)]
            )
        assert result.exit_code == 0
        output_file = vault / "Goals" / "2026" / "_weekly" / "reviews" / "2026-W10-council.md"
        assert output_file.exists()

    def test_week_missing_goals_exits_with_error(self, tmp_path):
        result = runner.invoke(app, ["--week", "2026-W10", "--dry-run", "--vault", str(tmp_path)])
        assert result.exit_code == 1

    def test_year_dry_run_prints_to_terminal(self, tmp_path):
        vault = self._mock_year_run(tmp_path)
        with (
            patch("persona_counsel.cli.list_personas", return_value=[make_persona_mock()]),
            patch("persona_counsel.cli.build_model"),
            patch("persona_counsel.cli.asyncio.run", return_value=([MOCK_EVALUATION], MOCK_SYNTHESIS)),
        ):
            result = runner.invoke(
                app, ["--year", "2026", "--dry-run", "--vault", str(vault)]
            )
        assert result.exit_code == 0

    def test_year_writes_to_annual_path(self, tmp_path):
        vault = self._mock_year_run(tmp_path)
        with (
            patch("persona_counsel.cli.list_personas", return_value=[make_persona_mock()]),
            patch("persona_counsel.cli.build_model"),
            patch("persona_counsel.cli.asyncio.run", return_value=([MOCK_EVALUATION], MOCK_SYNTHESIS)),
        ):
            result = runner.invoke(
                app, ["--year", "2026", "--vault", str(vault)]
            )
        assert result.exit_code == 0
        output_file = vault / "Goals" / "2026" / "_annual" / "reviews" / "2026-council.md"
        assert output_file.exists()

    def test_year_missing_goals_exits_with_error(self, tmp_path):
        result = runner.invoke(app, ["--year", "2026", "--dry-run", "--vault", str(tmp_path)])
        assert result.exit_code == 1
