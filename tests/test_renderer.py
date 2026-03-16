"""Tests for the markdown renderer."""

from persona_counsel.models import CouncilSynthesis, PersonaEvaluation
from persona_counsel.renderer import render_evaluation, render_report, _month_label


def make_evaluation(name="Solomon", archetype="The Elder") -> PersonaEvaluation:
    return PersonaEvaluation(
        persona_name=name,
        archetype=archetype,
        assessment="A thoughtful month of presence.",
        concerns=["Work crept into evenings"],
        recommendations=["Block Friday nights"],
        key_question="Were you really there?",
    )


def make_synthesis() -> CouncilSynthesis:
    return CouncilSynthesis(
        consensus="Overall a solid month with some drift.",
        tensions=["Craftsman vs Elder on deep work time"],
        priorities=["Protect evening routines"],
        coyote_dissent="The real question is whether any of these goals matter.",
    )


class TestMonthLabel:
    def test_known_month(self):
        assert _month_label("2026-03") == "March 2026"

    def test_january(self):
        assert _month_label("2025-01") == "January 2025"

    def test_december(self):
        assert _month_label("2024-12") == "December 2024"


class TestRenderEvaluation:
    def test_contains_persona_name(self):
        ev = make_evaluation()
        output = render_evaluation(ev)
        assert "Solomon" in output

    def test_contains_assessment(self):
        ev = make_evaluation()
        output = render_evaluation(ev)
        assert "A thoughtful month" in output

    def test_contains_concern(self):
        ev = make_evaluation()
        output = render_evaluation(ev)
        assert "Work crept into evenings" in output

    def test_contains_recommendation(self):
        ev = make_evaluation()
        output = render_evaluation(ev)
        assert "Block Friday nights" in output

    def test_contains_key_question(self):
        ev = make_evaluation()
        output = render_evaluation(ev)
        assert "Were you really there?" in output

    def test_empty_concerns_excluded(self):
        ev = PersonaEvaluation(
            persona_name="X",
            archetype="Y",
            assessment="Fine.",
            concerns=[],
            recommendations=["Do this"],
            key_question="OK?",
        )
        output = render_evaluation(ev)
        assert "**Concerns:**" not in output


class TestRenderReport:
    def test_contains_month_heading(self):
        ev = make_evaluation()
        s = make_synthesis()
        report = render_report("2026-03", [ev], s, "ollama", "phi4-mini")
        assert "# Council Review: March 2026" in report

    def test_contains_frontmatter(self):
        ev = make_evaluation()
        s = make_synthesis()
        report = render_report("2026-03", [ev], s, "ollama", "phi4-mini")
        assert "Month: 2026-03" in report
        assert "Provider: ollama" in report
        assert "Model: phi4-mini" in report

    def test_contains_consensus(self):
        ev = make_evaluation()
        s = make_synthesis()
        report = render_report("2026-03", [ev], s, "ollama", "phi4-mini")
        assert "Overall a solid month" in report

    def test_contains_tensions(self):
        ev = make_evaluation()
        s = make_synthesis()
        report = render_report("2026-03", [ev], s, "ollama", "phi4-mini")
        assert "Craftsman vs Elder" in report

    def test_contains_coyote_section(self):
        ev = make_evaluation()
        s = make_synthesis()
        report = render_report("2026-03", [ev], s, "ollama", "phi4-mini")
        assert "## Coyote Says" in report
        assert "The real question" in report

    def test_contains_individual_evaluations(self):
        ev = make_evaluation()
        s = make_synthesis()
        report = render_report("2026-03", [ev], s, "ollama", "phi4-mini")
        assert "## Individual Evaluations" in report
        assert "### Solomon" in report

    def test_multiple_evaluations(self):
        ev1 = make_evaluation("Solomon", "The Elder")
        ev2 = make_evaluation("Hiro", "The Craftsman")
        s = make_synthesis()
        report = render_report("2026-03", [ev1, ev2], s, "anthropic", "claude-haiku-4-5-20251001")
        assert "Solomon" in report
        assert "Hiro" in report
        assert "Solomon, Hiro" in report  # in frontmatter
