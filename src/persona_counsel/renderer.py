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


def _month_label(month: str) -> str:
    """Convert YYYY-MM to 'Month YYYY'."""
    year, m = month.split("-")
    return f"{MONTH_NAMES.get(m, m)} {year}"


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
    month: str,
    evaluations: list[PersonaEvaluation],
    synthesis: CouncilSynthesis,
    provider: str,
    model: str,
) -> str:
    """Render the full council report as a markdown string."""
    persona_names = ", ".join(ev.persona_name for ev in evaluations)
    generated = date.today().isoformat()
    label = _month_label(month)

    frontmatter = (
        f"---\n"
        f"Generated: {generated}\n"
        f"Month: {month}\n"
        f"Personas: {persona_names}\n"
        f"Provider: {provider}\n"
        f"Model: {model}\n"
        f"---\n"
    )

    sections = [
        frontmatter,
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
