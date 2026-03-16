"""Tests for council orchestration (using pydantic-ai TestModel)."""
import asyncio

from pydantic_ai.models.test import TestModel

from persona_counsel.council import (
    _build_evaluation_prompt,
    _format_evaluations_for_synthesis,
    run_council,
)
from persona_counsel.models import CouncilSynthesis, PersonaEvaluation


def make_evaluation(name="Solomon", archetype="The Elder") -> PersonaEvaluation:
    return PersonaEvaluation(
        persona_name=name,
        archetype=archetype,
        assessment="A fine month.",
        concerns=["One concern"],
        recommendations=["One recommendation"],
        key_question="Did it matter?",
    )


class TestBuildEvaluationPrompt:
    def test_includes_goals_text(self):
        prompt = _build_evaluation_prompt("## Goals\nShip the thing.", None)
        assert "Ship the thing" in prompt

    def test_no_prior_section_when_none(self):
        prompt = _build_evaluation_prompt("## Goals", None)
        assert "PRIOR MONTH" not in prompt

    def test_includes_prior_when_provided(self):
        prompt = _build_evaluation_prompt("## Goals", "## Prior Goals")
        assert "PRIOR MONTH" in prompt
        assert "## Prior Goals" in prompt


class TestFormatEvaluationsForSynthesis:
    def test_includes_all_persona_names(self):
        ev1 = make_evaluation("Solomon", "The Elder")
        ev2 = make_evaluation("Hiro", "The Craftsman")
        text = _format_evaluations_for_synthesis([ev1, ev2], {})
        assert "Solomon" in text
        assert "Hiro" in text

    def test_default_weight_shown(self):
        ev = make_evaluation("Solomon")
        text = _format_evaluations_for_synthesis([ev], {})
        assert "weight: 1.0" in text

    def test_custom_weight_shown(self):
        ev = make_evaluation("Solomon")
        text = _format_evaluations_for_synthesis([ev], {"solomon": 1.5})
        assert "weight: 1.5" in text

    def test_includes_concerns_and_recommendations(self):
        ev = make_evaluation("Solomon")
        text = _format_evaluations_for_synthesis([ev], {})
        assert "One concern" in text
        assert "One recommendation" in text


class TestRunCouncil:
    def test_returns_evaluations_for_each_persona(self, sample_persona, second_persona):
        model = TestModel()
        evaluations, synthesis = asyncio.run(
            run_council([sample_persona, second_persona], "## Goals\nDo things.", None, model, {})
        )
        assert len(evaluations) == 2

    def test_evaluation_names_match_personas(self, sample_persona, second_persona):
        model = TestModel()
        evaluations, synthesis = asyncio.run(
            run_council([sample_persona, second_persona], "## Goals\nDo things.", None, model, {})
        )
        names = {ev.persona_name for ev in evaluations}
        assert "Testus" in names
        assert "Secondus" in names

    def test_synthesis_is_council_synthesis(self, sample_persona):
        model = TestModel()
        _, synthesis = asyncio.run(
            run_council([sample_persona], "## Goals", None, model, {})
        )
        assert isinstance(synthesis, CouncilSynthesis)

    def test_single_persona_works(self, sample_persona):
        model = TestModel()
        evaluations, synthesis = asyncio.run(
            run_council([sample_persona], "## Goals\nDo one thing.", None, model, {})
        )
        assert len(evaluations) == 1

    def test_with_prior_text(self, sample_persona):
        model = TestModel()
        evaluations, synthesis = asyncio.run(
            run_council([sample_persona], "## Goals", "## Prior", model, {})
        )
        assert len(evaluations) == 1
