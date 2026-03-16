"""Render council results as a markdown report."""
from datetime import date

from .models import CouncilSynthesis, PersonaEvaluation

MONTH_NAMES = {
    "01": "January",
    "02": "February",
    "03": "March",
    "04": "April",
    "05": "May",
    "06": "June",
    "07": "July",
    "08": "August",
    "09": "September",
    "10": "October",
    "11": "November",
    "12": "December",
}


def _period_label(period: str) -> str:
    """Convert a period string to a human-readable label.

    YYYY-MM  -> "March 2026"
    YYYY-WNN -> "Week 10, 2026"
    YYYY     -> "2026"
    """
    if len(period) == 4 and period.isdigit():
        return period  # annual: "2026"
    if "-W" in period:
        year, week = period.split("-W", 1)
        return f"Week {int(week)}, {year}"
    year, m = period.split("-")
    return f"{MONTH_NAMES.get(m, m)} {year}"


# Keep the old name as an alias so tests importing it directly still pass
_month_label = _period_label


def render_evaluation(ev: PersonaEvaluation) -> str:
    """Render a single persona evaluation as markdown."""
    lines = [
        f"### {ev.persona_name} ({ev.archetype})",
        "",
        ev.assessment,
        "",
    ]
    if ev.concerns:
        lines.append("**Concerns:**")
        for c in ev.concerns:
            lines.append(f"- {c}")
        lines.append("")
    if ev.recommendations:
        lines.append("**Recommendations:**")
        for r in ev.recommendations:
            lines.append(f"- {r}")
        lines.append("")
    lines.append(f"**Question to sit with:** {ev.key_question}")
    return "\n".join(lines)


def render_report(
    period: str,
    evaluations: list[PersonaEvaluation],
    synthesis: CouncilSynthesis,
    provider: str,
    model: str,
) -> str:
    """Render the full council report as a markdown string."""
    persona_names = ", ".join(ev.persona_name for ev in evaluations)
    generated = date.today().isoformat()
    label = _period_label(period)

    fm = (
        f"---\n"
        f"Generated: {generated}\n"
        f"Period: {period}\n"
        f"Personas: {persona_names}\n"
        f"Provider: {provider}\n"
        f"Model: {model}\n"
        f"---\n"
    )

    sections = [
        fm,
        f"# Council Review: {label}",
        "",
        "## Consensus",
        "",
        synthesis.consensus,
        "",
        "## Tensions",
        "",
    ]
    for tension in synthesis.tensions:
        sections.append(f"- {tension}")
    sections.append("")
    sections.append("## Priorities")
    sections.append("")
    for priority in synthesis.priorities:
        sections.append(f"- {priority}")
    sections.append("")
    sections.append("## Coyote Says")
    sections.append("")
    sections.append(synthesis.coyote_dissent)
    sections.append("")
    sections.append("---")
    sections.append("")
    sections.append("## Individual Evaluations")
    sections.append("")
    for ev in evaluations:
        sections.append(render_evaluation(ev))
        sections.append("")

    return "\n".join(sections)
