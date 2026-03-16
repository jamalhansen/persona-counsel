"""Load goals notes from the Obsidian vault -- monthly, weekly, or annual scope."""
import re
from datetime import date
from pathlib import Path
from typing import Optional

import frontmatter
from local_first_common.obsidian import find_vault_root

_WEEK_RE = re.compile(r"^\d{4}-W\d{1,2}$")
_YEAR_RE = re.compile(r"^\d{4}$")
_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _monthly_note_path(vault_root: Path, month: str) -> Path:
    year = month[:4]
    return vault_root / "Goals" / year / "_monthly" / f"{month}.md"


def _weekly_note_path(vault_root: Path, week: str) -> Path:
    year = week[:4]
    return vault_root / "Goals" / year / "_weekly" / f"{week}.md"


def _annual_note_path(vault_root: Path, year: str) -> Path:
    return vault_root / "Goals" / year / "_annual" / f"{year}.md"


def _read_note(path: Path, description: str) -> str:
    if not path.exists():
        raise FileNotFoundError(f"{description} not found: {path}")
    post = frontmatter.load(str(path))
    return post.content


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_goals(month: str, vault_root: Optional[Path] = None) -> str:
    """Load a monthly goals note (YYYY-MM). Raises FileNotFoundError if missing."""
    root = vault_root or find_vault_root()
    path = _monthly_note_path(root, month)
    return _read_note(path, f"Monthly goals note for {month}")


def load_weekly_goals(week: str, vault_root: Optional[Path] = None) -> str:
    """Load a weekly goals note (YYYY-WNN). Raises FileNotFoundError if missing."""
    root = vault_root or find_vault_root()
    path = _weekly_note_path(root, week)
    return _read_note(path, f"Weekly goals note for {week}")


def load_annual_goals(year: str, vault_root: Optional[Path] = None) -> str:
    """Load an annual goals note (YYYY). Raises FileNotFoundError if missing."""
    root = vault_root or find_vault_root()
    path = _annual_note_path(root, year)
    return _read_note(path, f"Annual goals note for {year}")


# ---------------------------------------------------------------------------
# Output paths
# ---------------------------------------------------------------------------


def goals_output_path(month: str, vault_root: Optional[Path] = None) -> Path:
    root = vault_root or find_vault_root()
    year = month[:4]
    return root / "Goals" / year / "_monthly" / "reviews" / f"{month}-council.md"


def weekly_output_path(week: str, vault_root: Optional[Path] = None) -> Path:
    root = vault_root or find_vault_root()
    year = week[:4]
    return root / "Goals" / year / "_weekly" / "reviews" / f"{week}-council.md"


def annual_output_path(year: str, vault_root: Optional[Path] = None) -> Path:
    root = vault_root or find_vault_root()
    return root / "Goals" / year / "_annual" / "reviews" / f"{year}-council.md"


# ---------------------------------------------------------------------------
# Current-period helpers
# ---------------------------------------------------------------------------


def current_month() -> str:
    """Return the current month as YYYY-MM."""
    return date.today().strftime("%Y-%m")


def current_week() -> str:
    """Return the current ISO week as YYYY-WNN (e.g. 2026-W11)."""
    today = date.today()
    iso = today.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def current_year() -> str:
    """Return the current year as YYYY."""
    return str(date.today().year)


# ---------------------------------------------------------------------------
# Council report loader (prior-report context)
# ---------------------------------------------------------------------------


def _output_path_for_period(period: str, vault_root: Path) -> Path:
    """Return the council output path for any period string (auto-detects type)."""
    if _WEEK_RE.match(period):
        return weekly_output_path(period, vault_root)
    if _YEAR_RE.match(period):
        return annual_output_path(period, vault_root)
    if _MONTH_RE.match(period):
        return goals_output_path(period, vault_root)
    raise ValueError(f"Cannot determine period type for: {period!r}")


def load_council_report(period: str, vault_root: Optional[Path] = None) -> str:
    """Load a prior council report file for any period (YYYY-MM, YYYY-WNN, or YYYY).

    Raises FileNotFoundError if the report has not been generated yet.
    """
    root = vault_root or find_vault_root()
    path = _output_path_for_period(period, root)
    if not path.exists():
        raise FileNotFoundError(f"Council report for {period} not found: {path}")
    return path.read_text(encoding="utf-8")
