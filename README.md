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

## Usage

```bash
# Evaluate current month's goals (ollama default)
uv run python src/main.py

# Evaluate a specific week
uv run python src/main.py --week 2026-W11

# Use Anthropic for a higher-quality synthesis
uv run python src/main.py --provider anthropic

# Dry run: print report to terminal instead of writing to vault
uv run python src/main.py --dry-run -n: Call LLM but do not save results. Print to stdout.

# Override persona weights for this run (default 1.0)
uv run python src/main.py --weight solomon=1.5 --weight hiro=0.8

# List available personas
uv run python src/main.py --list-personas
```

## CLI Reference

All tools in this series share a common set of CLI flags for model management via [local-first-common](https://github.com/jamalhansen/local-first-common).

| Flag | Short | Default | Description |
|---|---|---|---|
| `--month` | `-m` | current | Month to evaluate (YYYY-MM) |
| `--week` | | — | ISO week to evaluate (YYYY-WNN) |
| `--year` | | — | Year to evaluate (YYYY) |
| `--provider` | `-p` | `ollama` | LLM provider (`ollama`, `anthropic`, `gemini`, `groq`, `deepseek`) |
| `--model` | | provider default | Override provider's default model |
| `--dry-run -n: Call LLM but do not save results. Print to stdout.
| `--verbose` | `-v` | off | Show extra progress output |
| `--debug` | `-d` | off | Show raw prompts and LLM responses |
| `--weight` | `-w` | 1.0 | Override a persona's weight (e.g. `solomon=1.5`). Repeatable. |
| `--list-personas` | | — | List available personas and exit. |

## Project Structure

This tool follows the [Local-First AI project blueprint](https://github.com/jamalhansen/local-first-common).

```
persona-counsel/
├── src/
│   ├── main.py           # Typer CLI entry point
│   ├── logic.py          # Core council orchestration
│   ├── council.py        # Persona execution logic
│   ├── models.py         # Pydantic models for evaluations
│   ├── renderer.py       # Markdown report generator
│   ├── goals.py          # Load monthly goals from Obsidian vault
│   └── model_factory.py  # Provider/model resolution
├── pyproject.toml        # Managed by uv
└── tests/
    ├── test_main.py      # CLI integration tests via MockProvider
    └── ...
```

## Running Tests

```bash
uv run pytest
```
