"""Typer CLI for persona-counsel."""

import asyncio
import os
import re
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.markdown import Markdown

from local_first_common.cli import (
    init_config_option,
    dry_run_option,
    no_llm_option,
    resolve_dry_run,
    provider_option,
    model_option,
)
from local_first_common.tracking import register_tool, timed_run
from local_first_common.obsidian import find_vault_root
from local_first_common.personas import list_personas
from local_first_common.pydantic_ai_utils import build_model, PROVIDER_DEFAULTS

from .council import run_council
from .goals import (
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
from .renderer import render_report

TOOL_NAME = "persona-counsel"
DEFAULTS = {"provider": "ollama", "model": "llama3"}
_TOOL = register_tool("persona-counsel")

app = typer.Typer(help="Run your goals through a council of named personas.")
console = Console()
err_console = Console(stderr=True)

COUNCIL_PERSONA_NAMES = [
    "solomon",
    "hiro",
    "zora",
    "silas",
    "ada",
    "nneka",
    "eli",
    "coyote",
]

_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
_WEEK_RE = re.compile(r"^\d{4}-W\d{1,2}$")
_YEAR_RE = re.compile(r"^\d{4}$")


class PersonaCounselError(Exception):
    """Base error for strict persona-counsel operations."""


class ModelBuildError(PersonaCounselError):
    """Raised when provider/model cannot be initialized."""


class CouncilRunError(PersonaCounselError):
    """Raised when council execution fails."""


def _parse_weight(raw: str) -> tuple[str, float]:
    """Parse a 'name=value' weight flag. Returns (name, value)."""
    try:
        name, value = raw.split("=", 1)
        return name.strip().lower(), float(value.strip())
    except (ValueError, AttributeError):
        raise typer.BadParameter(
            f"Weight must be in 'name=value' format (e.g. solomon=1.5), got: {raw!r}"
        )


def _validate_scope(
    month: Optional[str], week: Optional[str], year: Optional[str]
) -> str:
    """Ensure at most one scope flag is set. Return the active scope: 'month', 'week', or 'year'."""
    active = sum(x is not None for x in [month, week, year])
    if active > 1:
        raise typer.BadParameter(
            "--month, --week, and --year are mutually exclusive. Specify at most one."
        )
    if week is not None:
        if not _WEEK_RE.match(week):
            raise typer.BadParameter(
                f"--week must be YYYY-WNN (e.g. 2026-W10), got: {week!r}"
            )
        return "week"
    if year is not None:
        if not _YEAR_RE.match(year):
            raise typer.BadParameter(f"--year must be YYYY (e.g. 2026), got: {year!r}")
        return "year"
    if month is not None and not _MONTH_RE.match(month):
        raise typer.BadParameter(
            f"--month must be YYYY-MM (e.g. 2026-03), got: {month!r}"
        )
    return "month"


def _build_model_or_raise(provider: str, model: Optional[str]):
    """Create the pydantic-ai model or raise typed error."""
    try:
        return build_model(provider, model)
    except Exception as e:  # noqa: BLE001
        raise ModelBuildError(str(e)) from e


def _run_council_or_raise(
    council_personas,
    goals_text: str,
    prior_text: Optional[str],
    pai_model,
    weights: dict[str, float],
    concurrency: int,
    prior_report_text: Optional[str],
):
    """Run council and raise typed error on failure."""
    try:
        return asyncio.run(
            run_council(
                council_personas,
                goals_text,
                prior_text,
                pai_model,
                weights,
                concurrency,
                prior_report_text,
            )
        )
    except Exception as e:  # noqa: BLE001
        raise CouncilRunError(str(e)) from e


@app.command()
def main(
    month: Optional[str] = typer.Option(
        None,
        "--month",
        "-M",
        help="Month to evaluate (YYYY-MM). Defaults to current month.",
    ),
    week: Optional[str] = typer.Option(
        None, "--week", help="ISO week to evaluate (YYYY-WNN, e.g. 2026-W10)."
    ),
    year: Optional[str] = typer.Option(
        None, "--year", help="Year to evaluate (YYYY, e.g. 2026)."
    ),
    prior: Optional[str] = typer.Option(
        None,
        "--prior",
        help="Prior period goals note for context (YYYY-MM / YYYY-WNN / YYYY).",
    ),
    prior_report: Optional[str] = typer.Option(
        None,
        "--prior-report",
        help="Prior council report for context — lets personas see what was recommended last time (YYYY-MM / YYYY-WNN / YYYY).",
    ),
    provider: Annotated[str, provider_option()] = os.environ.get(
        "MODEL_PROVIDER", "ollama"
    ),
    model: Annotated[Optional[str], model_option()] = None,
    dry_run: Annotated[bool, dry_run_option()] = False,
    no_llm: Annotated[bool, no_llm_option()] = False,
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show extra progress output."
    ),
    vault: Optional[Path] = typer.Option(
        None, "--vault", help="Override the Obsidian vault path."
    ),
    weight: Optional[list[str]] = typer.Option(
        None,
        "--weight",
        "-w",
        help="Override persona weight (e.g. --weight solomon=1.5). Repeatable.",
    ),
    concurrency: int = typer.Option(
        3,
        "--concurrency",
        "-c",
        help="Max parallel API calls (lower = fewer rate-limit errors, default 3).",
    ),
    list_personas_flag: bool = typer.Option(
        False, "--list-personas", help="List available personas and exit."
    ),
    init_config: Annotated[bool, init_config_option(TOOL_NAME, DEFAULTS)] = False,
) -> None:
    """Run your goals through the council and receive a qualitative synthesis.

    Scope flags (pick one):
      --month YYYY-MM   Monthly goals note (default: current month)
      --week  YYYY-WNN  Weekly goals note (e.g. 2026-W10)
      --year  YYYY      Annual goals note (e.g. 2026)
    """

    # Handle --list-personas
    if list_personas_flag:
        personas = list_personas("Counsel", vault_path=vault)
        if not personas:
            err_console.print(
                "[yellow]No personas found. Check OBSIDIAN_VAULT_PATH/personas/Counsel or ~/.config/local-first/personas/Counsel[/yellow]"
            )
            raise typer.Exit(1)
        console.print("\n[bold]Available personas (Counsel):[/bold]\n")
        for p in personas:
            console.print(f"  [cyan]{p.name}[/cyan] ({p.archetype}) -- {p.domain}")
        console.print()
        raise typer.Exit()

    # Validate scope flags
    try:
        scope = _validate_scope(month, week, year)
    except typer.BadParameter as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Resolve the active period and select loaders
    if scope == "week":
        period = week or current_week()
        loader = load_weekly_goals
        output_fn = weekly_output_path
    elif scope == "year":
        period = year or current_year()
        loader = load_annual_goals
        output_fn = annual_output_path
    else:
        period = month or current_month()
        loader = load_goals
        output_fn = goals_output_path

    # Parse weights
    weights: dict[str, float] = {}
    for w in weight or []:
        name, value = _parse_weight(w)
        weights[name] = value

    # Resolve vault
    vault_root = vault or find_vault_root()

    # Load goals
    if verbose:
        console.print(f"[dim]Loading goals for {period}...[/dim]")
    try:
        goals_text = loader(period, vault_root=vault_root)
    except FileNotFoundError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    prior_text: Optional[str] = None
    if prior:
        if verbose:
            console.print(f"[dim]Loading prior period {prior} for context...[/dim]")
        try:
            prior_text = loader(prior, vault_root=vault_root)
        except FileNotFoundError as e:
            err_console.print(f"[yellow]Warning:[/yellow] {e}")

    prior_report_text: Optional[str] = None
    if prior_report:
        if verbose:
            console.print(
                f"[dim]Loading prior council report {prior_report} for context...[/dim]"
            )
        try:
            prior_report_text = load_council_report(prior_report, vault_root=vault_root)
        except (FileNotFoundError, ValueError) as e:
            err_console.print(f"[yellow]Warning:[/yellow] {e}")

    # Load personas
    all_personas = list_personas("Counsel", vault_path=vault_root)
    council_personas = [
        p for p in all_personas if p.name.lower() in COUNCIL_PERSONA_NAMES
    ]
    missing = set(COUNCIL_PERSONA_NAMES) - {p.name.lower() for p in council_personas}
    if missing:
        err_console.print(
            f"[yellow]Warning:[/yellow] Missing personas: {', '.join(sorted(missing))}"
        )
    if not council_personas:
        err_console.print(
            "[red]Error:[/red] No personas found in category 'Counsel'. Run --list-personas to diagnose."
        )
        raise typer.Exit(1)

    dry_run = resolve_dry_run(dry_run, no_llm)

    # Resolve provider (uses pydantic-ai model, not BaseProvider)
    try:
        pai_model = _build_model_or_raise(provider, model)
    except ModelBuildError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    model_name = model or PROVIDER_DEFAULTS.get(provider, "unknown")

    console.print(
        f"[bold]Running council[/bold] for [cyan]{period}[/cyan] "
        f"with [dim]{provider}:{model_name}[/dim] "
        f"({len(council_personas)} personas)..."
    )

    # Run the council
    try:
        with timed_run(
            "persona-counsel", f"{provider}:{model_name}", source_location=period
        ) as _run:
            evaluations, synthesis = _run_council_or_raise(
                council_personas,
                goals_text,
                prior_text,
                pai_model,
                weights,
                concurrency,
                prior_report_text,
            )
            _run.item_count = len(council_personas)
    except CouncilRunError as e:
        err_console.print(f"[red]Council run failed:[/red] {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        raise typer.Exit(1)

    # Render report
    report = render_report(period, evaluations, synthesis, provider, model_name)

    if dry_run:
        console.print("\n")
        console.print(Markdown(report))

    # Write to file
    output_path = output_fn(period, vault_root=vault_root)
    if not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        console.print(f"\n[green]Written:[/green] {output_path}")
    else:
        console.print(f"\n[dim][dry-run] Would have written to: {output_path}[/dim]")
