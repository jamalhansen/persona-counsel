"""Council orchestration: run persona evaluations in parallel, then synthesize."""
import asyncio
from typing import Any

from local_first_common.personas import PersonaCard
from pydantic_ai import Agent

from .models import CouncilSynthesis, PersonaEvaluation

EVALUATION_USER_PROMPT = """\
Please review the following monthly goals note and evaluate this month from your unique perspective.

--- MONTHLY GOALS ---
{goals_text}
{prior_section}

Return your evaluation as structured output.
"""

SYNTHESIS_SYSTEM_PROMPT = """\
You are a council facilitator who synthesizes perspectives from multiple advisors.
Each advisor has evaluated the same month's goals from a different lens.
Your job is to find common ground, surface genuine tensions, and distill priorities.

Rules:
- Do not suppress disagreement. Tensions between advisors are diagnostic, not problems.
- The consensus should be honest -- do not sand off the rough edges.
- Coyote's dissent should be surfaced separately in coyote_dissent, in Coyote's voice.
- Priorities should be concrete and actionable.
- Weights are provided per persona to reflect current life priorities.
  A weight above 1.0 means that persona's concerns should carry more influence.
  A weight below 1.0 means less influence. All weights default to 1.0.
"""

SYNTHESIS_USER_PROMPT = """\
Here are the evaluations from the council. Persona weights are shown.
Synthesize a consensus, surface tensions, propose priorities, and quote Coyote's dissent.

{evaluations_text}
"""


def _build_evaluation_prompt(goals_text: str, prior_text: str | None) -> str:
    prior_section = ""
    if prior_text:
        prior_section = f"\n--- PRIOR MONTH (for context) ---\n{prior_text}\n"
    return EVALUATION_USER_PROMPT.format(
        goals_text=goals_text,
        prior_section=prior_section,
    )


def _format_evaluations_for_synthesis(
    evaluations: list[PersonaEvaluation], weights: dict[str, float]
) -> str:
    parts = []
    for ev in evaluations:
        weight = weights.get(ev.persona_name.lower(), 1.0)
        parts.append(f"### {ev.persona_name} ({ev.archetype}) [weight: {weight}]")
        parts.append(f"Assessment: {ev.assessment}")
        parts.append("Concerns:")
        for c in ev.concerns:
            parts.append(f"  - {c}")
        parts.append("Recommendations:")
        for r in ev.recommendations:
            parts.append(f"  - {r}")
        parts.append(f"Key question: {ev.key_question}")
        parts.append("")
    return "\n".join(parts)


async def _evaluate_persona(
    persona: PersonaCard,
    goals_text: str,
    prior_text: str | None,
    model: Any,
) -> PersonaEvaluation:
    """Run a single persona evaluation."""
    agent: Agent[None, PersonaEvaluation] = Agent(
        model,
        output_type=PersonaEvaluation,
        system_prompt=persona.system_prompt,
    )
    user_prompt = _build_evaluation_prompt(goals_text, prior_text)
    result = await agent.run(user_prompt)
    # Ensure persona metadata is correct regardless of LLM output
    ev = result.output
    ev.persona_name = persona.name
    ev.archetype = persona.archetype
    return ev


async def _synthesize(
    evaluations: list[PersonaEvaluation],
    weights: dict[str, float],
    model: Any,
) -> CouncilSynthesis:
    """Run the synthesis agent with all persona evaluations."""
    agent: Agent[None, CouncilSynthesis] = Agent(
        model,
        output_type=CouncilSynthesis,
        system_prompt=SYNTHESIS_SYSTEM_PROMPT,
    )
    eval_text = _format_evaluations_for_synthesis(evaluations, weights)
    user_prompt = SYNTHESIS_USER_PROMPT.format(evaluations_text=eval_text)
    result = await agent.run(user_prompt)
    return result.output


async def run_council(
    personas: list[PersonaCard],
    goals_text: str,
    prior_text: str | None,
    model: Any,
    weights: dict[str, float],
) -> tuple[list[PersonaEvaluation], CouncilSynthesis]:
    """Evaluate all personas in parallel, then synthesize. Returns (evaluations, synthesis)."""
    # All persona evaluations run concurrently -- no persona sees another's output
    evaluation_tasks = [
        _evaluate_persona(persona, goals_text, prior_text, model) for persona in personas
    ]
    evaluations: list[PersonaEvaluation] = list(await asyncio.gather(*evaluation_tasks))

    synthesis = await _synthesize(evaluations, weights, model)
    return evaluations, synthesis
