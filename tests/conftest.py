"""Shared test fixtures for persona-counsel."""
import pytest
import yaml

from local_first_common.personas import PersonaCard


PERSONA_DATA = {
    "name": "Testus",
    "archetype": "The Tester",
    "domain": "Testing",
    "principle": "Test Everything",
    "lens": "Looks for gaps.",
    "bias": {"overweights": ["coverage"], "underweights": ["speed"]},
    "evaluation_questions": ["Was everything tested?"],
    "rewards": ["Full coverage"],
    "penalizes": ["Skipped tests"],
    "conflict_signature": "Clashes with nobody.",
    "system_prompt": "You are Testus. Be thorough.",
}

SECOND_PERSONA_DATA = {
    **PERSONA_DATA,
    "name": "Secondus",
    "archetype": "The Tester Two",
    "system_prompt": "You are Secondus. Be quick.",
}


@pytest.fixture
def personas_dir(tmp_path):
    """Create a temporary personas directory with two test personas."""
    for data in [PERSONA_DATA, SECOND_PERSONA_DATA]:
        path = tmp_path / f"{data['name'].lower()}.yaml"
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f)
    return tmp_path


@pytest.fixture
def sample_persona():
    return PersonaCard(**PERSONA_DATA)


@pytest.fixture
def second_persona():
    return PersonaCard(**SECOND_PERSONA_DATA)


SAMPLE_GOALS = """\
## Active Goals

| Goal | Status |
|------|--------|
| Ship blog post | In progress |
| Exercise 3x/week | Done |

## End of Month Check

- What went well?
- What would I change?

## Wins

- Finished the draft
"""
