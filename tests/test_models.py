"""Tests for PersonaEvaluation and CouncilSynthesis models."""
import pytest
from pydantic import ValidationError

from persona_counsel.models import CouncilSynthesis, PersonaEvaluation


class TestPersonaEvaluation:
    def test_valid_evaluation(self):
        ev = PersonaEvaluation(
            persona_name="Solomon",
            archetype="The Elder",
            assessment="A solid month for family presence.",
            concerns=["Work crept in twice"],
            recommendations=["Guard Friday evenings"],
            key_question="Did you actually slow down?",
        )
        assert ev.persona_name == "Solomon"
        assert len(ev.concerns) == 1

    def test_empty_lists_allowed(self):
        ev = PersonaEvaluation(
            persona_name="X",
            archetype="Y",
            assessment="Fine.",
            concerns=[],
            recommendations=[],
            key_question="OK?",
        )
        assert ev.concerns == []
        assert ev.recommendations == []

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            PersonaEvaluation(
                persona_name="Solo",
                archetype="Elder",
                assessment="Good.",
                concerns=[],
                # missing recommendations and key_question
            )


class TestCouncilSynthesis:
    def test_valid_synthesis(self):
        s = CouncilSynthesis(
            consensus="A productive month overall.",
            tensions=["Craftsman vs Elder on deep work"],
            priorities=["Protect family evenings"],
            coyote_dissent="Are you sure that goal even matters?",
        )
        assert s.coyote_dissent.startswith("Are you sure")

    def test_empty_tensions_and_priorities(self):
        s = CouncilSynthesis(
            consensus="Fine.",
            tensions=[],
            priorities=[],
            coyote_dissent="Nothing to see here.",
        )
        assert s.tensions == []

    def test_missing_field_raises(self):
        with pytest.raises(ValidationError):
            CouncilSynthesis(
                consensus="Fine.",
                tensions=[],
                # missing priorities and coyote_dissent
            )
