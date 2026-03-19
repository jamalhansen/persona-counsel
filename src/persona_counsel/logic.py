"""Typer CLI for persona-counsel."""
import asyncio
import os
import re
from pathlib import Path
from typing import Annotated, Optional

import typer
from local_first_common.obsidian import find_vault_root
from local_first_common.personas import list_personas
from rich.console import Console
from rich.markdown import Markdown

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
from .model_factory import PROVIDER_DEFAULTS, VALID_PROVIDERS, build_model
from .renderer import render_report

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


def _parse_weight(raw: str) -> tuple[str, float]:
    """Parse a 'name=value' weight flag. Returns (name, value)."""
    try:
        name, value = raw.split("=", 1)
        return name.strip().lower(), float(value.strip())
    except (ValueError, AttributeError):
        raise typer.BadParameter(
            f"Weight must be in 'name=value' format (e.g. solomon=1.5), got: {raw!r}"
        )


def _validate_scope(month: Optional[str], week: Optional[str], year: Optional[str]) -> str:
    """Ensure at most one scope flag is set. Return the active scope: 'month', 'week', or 'year'."""
    active = sum(x is not None for x in [month, week, year])
    if active > 1:
        raise typer.BadParameter(
            "--month, --week, and --year are mutually exclusive. Specify at most one."
        )
    if week is not None:
        if not _WEEK_RE.match(week):
            raise typer.BadParameter(f"--week must be YYYY-WNN (e.g. 2026-W10), got: {week!r}")
        return "week"
    if year is not None:
        if not _YEAR_RE.match(year):
            raise typer.BadParameter(f"--year must be YYYY (e.g. 2026), got: {year!r}")
        return "year"
    if month is not None and not _MONTH_RE.match(month):
        raise typer.BadParameter(f"--month must be YYYY-MM (e.g. 2026-03), got: {month!r}")
    return "month"


@app.command()
def main(
    month: Annotated[
        Optional[str],
        typer.Option("--month", "-m", help="Month to evaluate (YYYY-MM). Defaults to current month."),
    ] = None,
    week: Annotated[
        Optional[str],
        typer.Option("--week", help="ISO week to evaluate (YYYY-WNN, e.g. 2026-W10)."),
    ] = None,
    year: Annotated[
        Optional[str],
        typer.Option("--year", help="Year to evaluate (YYYY, e.g. 2026)."),
    ] = None,
    prior: Annotated[
        Optional[str],
        typer.Option(
            "--prior",
            help="Prior period goals note for context (YYYY-MM / YYYY-WNN / YYYY).",
        ),
    ] = None,
    prior_report: Annotated[
        Optional[str],
        typer.Option(
            "--prior-report",
            help="Prior council report for context — lets personas see what was recommended last time (YYYY-MM / YYYY-WNN / YYYY).",
        ),
    ] = None,
    provider: Annotated[
        str,
        typer.Option(
            "--provider",
            "-p",
            help=f"LLM provider. Choices: {', '.join(VALID_PROVIDERS)}",
        ),
    ] = os.environ.get("MODEL_PROVIDER", "ollama"),
    model: Annotated[
        Optional[str],
        typer.Option("--model", help="Override the provider's default model."),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Print to terminal only, do not write a file."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show extra progress output."),
    ] = False,
    vault: Annotated[
        Optional[Path],
        typer.Option("--vault", help="Override the Obsidian vault path."),
    ] = None,
    weight: Annotated[
        Optional[list[str]],
        typer.Option(
            "--weight",
            "-w",
            help="Override persona weight (e.g. --weight solomon=1.5). Repeatable.",
        ),
    ] = None,
    concurrency: Annotated[
        int,
        typer.Option(
            "--concurrency",
            "-c",
            help="Max parallel API calls (lower = fewer rate-limit errors, default 3).",
        ),
    ] = 3,
    list_personas_flag: Annotated[
        bool,
        typer.Option("--list-personas", help="List available personas and exit."),
    ] = False,
) -> None:
    """Run your goals through the council and receive a qualitative synthesis.

    Scope flags (pick one):
      --month YYYY-MM   Monthly goals note (default: current month)
      --week  YYYY-WNN  Weekly goals note (e.g. 2026-W10)
      --year  YYYY      Annual goals note (e.g. 2026)
    """

    # Handle --list-personas
    if list_personas_flag:
        personas = list_personas()
        if not personas:
            err_console.print("[yellow]No personas found. Check ~/.config/local-first/personas/[/yellow]")
            raise typer.Exit(1)
        console.print("\n[bold]Available personas:[/bold]\n")
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
    for w in (weight or []):
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
            console.print(f"[dim]Loading prior council report {prior_report} for context...[/dim]")
        try:
            prior_report_text = load_council_report(prior_report, vault_root=vault_root)
        except (FileNotFoundError, ValueError) as e:
            err_console.print(f"[yellow]Warning:[/yellow] {e}")

    # Load personas
    all_personas = list_personas()
    council_personas = [p for p in all_personas if p.name.lower() in COUNCIL_PERSONA_NAMES]
    missing = set(COUNCIL_PERSONA_NAMES) - {p.name.lower() for p in council_personas}
    if missing:
        err_console.print(
            f"[yellow]Warning:[/yellow] Missing personas: {', '.join(sorted(missing))}"
        )
    if not council_personas:
        err_console.print("[red]Error:[/red] No personas found. Run --list-personas to diagnose.")
        raise typer.Exit(1)

    # Build model
    try:
        pai_model = build_model(provider, model)
    except ValueError as e:
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
        evaluations, synthesis = asyncio.run(
            run_council(
                council_personas, goals_text, prior_text, pai_model, weights,
                concurrency, prior_report_text,
            )
        )
    except Exception as e:
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
        return

    # Write to file
    output_path = output_fn(period, vault_root=vault_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    console.print(f"\n[green]Written:[/green] {output_path}")
