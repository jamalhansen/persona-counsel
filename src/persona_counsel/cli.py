"""Typer CLI for persona-counsel."""
import asyncio
import os
from pathlib import Path
from typing import Annotated, Optional

import typer
from local_first_common.obsidian import find_vault_root
from local_first_common.personas import list_personas
from rich.console import Console
from rich.markdown import Markdown

from .council import run_council
from .goals import current_month, goals_output_path, load_goals
from .model_factory import PROVIDER_DEFAULTS, VALID_PROVIDERS, build_model
from .renderer import render_report

app = typer.Typer(help="Run your monthly goals through a council of named personas.")
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


def _parse_weight(raw: str) -> tuple[str, float]:
    """Parse a 'name=value' weight flag. Returns (name, value)."""
    try:
        name, value = raw.split("=", 1)
        return name.strip().lower(), float(value.strip())
    except (ValueError, AttributeError):
        raise typer.BadParameter(
            f"Weight must be in 'name=value' format (e.g. solomon=1.5), got: {raw!r}"
        )


@app.command()
def main(
    month: Annotated[
        Optional[str],
        typer.Option("--month", "-m", help="Month to evaluate (YYYY-MM). Defaults to current month."),
    ] = None,
    prior: Annotated[
        Optional[str],
        typer.Option("--prior", help="Prior month for context (YYYY-MM)."),
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
    list_personas_flag: Annotated[
        bool,
        typer.Option("--list-personas", help="List available personas and exit."),
    ] = False,
) -> None:
    """Run your monthly goals through the council and receive a qualitative synthesis."""

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

    # Resolve month
    target_month = month or current_month()

    # Parse weights
    weights: dict[str, float] = {}
    for w in (weight or []):
        name, value = _parse_weight(w)
        weights[name] = value

    # Resolve vault
    vault_root = vault or find_vault_root()

    # Load goals
    if verbose:
        console.print(f"[dim]Loading goals for {target_month}...[/dim]")
    try:
        goals_text = load_goals(target_month, vault_root=vault_root)
    except FileNotFoundError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    prior_text: Optional[str] = None
    if prior:
        if verbose:
            console.print(f"[dim]Loading prior month {prior} for context...[/dim]")
        try:
            prior_text = load_goals(prior, vault_root=vault_root)
        except FileNotFoundError as e:
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
        f"[bold]Running council[/bold] for [cyan]{target_month}[/cyan] "
        f"with [dim]{provider}:{model_name}[/dim] "
        f"({len(council_personas)} personas)..."
    )

    # Run the council
    try:
        evaluations, synthesis = asyncio.run(
            run_council(council_personas, goals_text, prior_text, pai_model, weights)
        )
    except Exception as e:
        err_console.print(f"[red]Council run failed:[/red] {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        raise typer.Exit(1)

    # Render report
    report = render_report(target_month, evaluations, synthesis, provider, model_name)

    if dry_run:
        console.print("\n")
        console.print(Markdown(report))
        return

    # Write to file
    output_path = goals_output_path(target_month, vault_root=vault_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    console.print(f"\n[green]Written:[/green] {output_path}")
