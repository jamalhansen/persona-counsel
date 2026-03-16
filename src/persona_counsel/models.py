"""Structured output models for the council evaluation."""
from pydantic import BaseModel, Field


class PersonaEvaluation(BaseModel):
    """What a single persona returns after reviewing the month."""

    persona_name: str = Field(description="The persona's name (e.g. Solomon, Hiro)")
    archetype: str = Field(description="The persona's archetype (e.g. The Elder, The Craftsman)")
    assessment: str = Field(
        description="2-4 sentence narrative evaluation from this persona's lens"
    )
    concerns: list[str] = Field(
        description="Specific things this persona flags as problems or risks"
    )
    recommendations: list[str] = Field(
        description="Concrete changes this persona would recommend"
    )
    key_question: str = Field(
        description="One question for the human to sit with after reading this evaluation"
    )


class CouncilSynthesis(BaseModel):
    """The final synthesis across all persona evaluations."""

    consensus: str = Field(
        description="3-5 sentence overall narrative combining the council's perspectives"
    )
    tensions: list[str] = Field(
        description="Where personas disagreed and why the tension matters"
    )
    priorities: list[str] = Field(
        description="What the council collectively recommends focusing on next"
    )
    coyote_dissent: str = Field(
        description="Coyote's independent take, surfaced separately from the consensus"
    )
