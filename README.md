# persona-counsel

Load your monthly goals note, run it through a council of named personas, collect independent evaluations, and receive a synthesized qualitative consensus.

Each persona has a distinct bias and lens. Conflict between personas is surfaced explicitly -- it's diagnostic, not a problem to suppress.

## What it does

1. Reads your monthly goals note from the Obsidian vault (`Goals/YYYY/_monthly/YYYY-MM.md`)
2. Runs the note through 8 personas in parallel -- each evaluates independently
3. A synthesis agent receives all 8 evaluations and produces a weighted consensus
4. Outputs a structured markdown report with consensus, tensions, priorities, and Coyote's dissent

The tool informs. You write the actual retrospective.

## The Council

| Persona | Archetype | Domain | Lens |
|---------|-----------|--------|------|
| Solomon | The Elder | Family | Presence and connection |
| Hiro | The Craftsman | Technical Excellence | Depth and craft |
| Zora | The Torch | Teaching | Knowledge shared |
| Silas | The Architect | Financial | Independence trajectory |
| Ada | The Scout | Growth | New territory entered |
| Nneka | The Gardener | Health | Body as long-term system |
| Eli | The Witness | Presence | Month genuinely inhabited |
| Coyote | The Trickster | Chaos | Honest incongruity |

No numeric scores. Output is qualitative narrative only.

## Installation

```bash
git clone git@github.com:jamalhansen/persona-counsel.git
cd persona-counsel
uv sync
```

Persona YAML files must be present at `~/.config/local-first/personas/`. The 8 starter personas are part of the local-first-common setup. If missing, run `--list-personas` to diagnose.

## Usage

```bash
# Dry run -- print to terminal, do not write a file
uv run counsel --dry-run

# Evaluate current month, write to reviews folder
uv run counsel

# Specific month
uv run counsel --month 2026-03

# With prior month for context
uv run counsel --month 2026-03 --prior 2026-02

# Choose a different provider or model
uv run counsel --provider anthropic
uv run counsel --provider ollama --model llama3.1:8b

# Override persona weights for this run (default 1.0)
uv run counsel --weight solomon=1.5 --weight hiro=0.8

# List available personas
uv run counsel --list-personas
```

## CLI reference

| Flag | Short | Description |
|------|-------|-------------|
| `--month YYYY-MM` | `-m` | Month to evaluate. Defaults to current month. |
| `--prior YYYY-MM` | | Prior month for context (trends, carry-over). |
| `--provider NAME` | `-p` | LLM provider: ollama, anthropic, groq, deepseek, gemini. |
| `--model NAME` | | Override the provider's default model. |
| `--dry-run` | `-n` | Print to terminal only, do not write a file. |
| `--verbose` | `-v` | Show extra progress output. |
| `--vault PATH` | | Override the Obsidian vault path. |
| `--weight name=value` | `-w` | Override a persona's weight. Repeatable. |
| `--list-personas` | | List available personas and exit. |

## Provider defaults

| Provider | Default model |
|----------|---------------|
| ollama | phi4-mini |
| anthropic | claude-haiku-4-5-20251001 |
| groq | llama-3.3-70b-versatile |
| deepseek | deepseek-chat |
| gemini | gemini-2.0-flash |

## Output

Without `--dry-run`, the report is written to:

```
Goals/YYYY/_monthly/reviews/YYYY-MM-council.md
```

The reviews directory is created automatically if it does not exist.

Report sections:

- **Consensus** -- 3-5 sentence synthesis from all perspectives
- **Tensions** -- where personas disagreed and why it matters
- **Priorities** -- what the council collectively recommends
- **Coyote Says** -- Coyote's independent take, surfaced separately
- **Individual Evaluations** -- each persona's full assessment, concerns, recommendations, and key question

## Architecture

```
Monthly goals file
  |
  +-- Solomon  (parallel)  --> PersonaEvaluation
  +-- Hiro     (parallel)  --> PersonaEvaluation
  +-- Zora     (parallel)  --> PersonaEvaluation
  +-- Silas    (parallel)  --> PersonaEvaluation
  +-- Ada      (parallel)  --> PersonaEvaluation
  +-- Nneka    (parallel)  --> PersonaEvaluation
  +-- Eli      (parallel)  --> PersonaEvaluation
  +-- Coyote   (parallel)  --> PersonaEvaluation
  |
  +-- Synthesis agent (receives all 8) --> CouncilSynthesis
```

- PydanticAI agents with `output_type` for structured output
- `asyncio.gather()` for parallel persona evaluation
- No persona sees another's output before synthesis
- Coyote is mechanically identical to every other persona -- chaos comes from its system prompt

## Persona store

Personas live in `~/.config/local-first/personas/` as YAML files, loaded via `local-first-common.personas`. Other tools can consume the same persona store.

The `LOCAL_FIRST_PERSONAS_DIR` environment variable overrides the default location.

## Project structure

```
persona-counsel/
├── src/persona_counsel/
│   ├── cli.py             Typer app and entry point
│   ├── council.py         Parallel evaluation + synthesis orchestration
│   ├── goals.py           Load monthly goals from Obsidian vault
│   ├── model_factory.py   Map provider/model flags to pydantic-ai Models
│   ├── models.py          PersonaEvaluation and CouncilSynthesis
│   └── renderer.py        Render results as markdown
└── tests/
    ├── test_cli.py
    ├── test_council.py
    ├── test_goals.py
    ├── test_model_factory.py
    ├── test_models.py
    └── test_renderer.py
```

## Testing

```bash
uv run pytest
```

The test suite uses pydantic-ai's `TestModel` to stub LLM calls. No real API calls are made.
