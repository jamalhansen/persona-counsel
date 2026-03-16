"""Load monthly goals notes from the Obsidian vault."""
from datetime import date
from pathlib import Path
from typing import Optional

import frontmatter
from local_first_common.obsidian import find_vault_root


def _monthly_note_path(vault_root: Path, month: str) -> Path:
    """Return the expected path for a monthly goals note (YYYY-MM.md)."""
    year = month[:4]
    return vault_root / "Goals" / year / "_monthly" / f"{month}.md"


def load_goals(
    month: str,
    vault_root: Optional[Path] = None,
) -> str:
    """Load the monthly goals note for the given YYYY-MM month string.

    Returns the note content as a string. Raises FileNotFoundError if missing.
    """
    root = vault_root or find_vault_root()
    path = _monthly_note_path(root, month)
    if not path.exists():
        raise FileNotFoundError(
            f"Monthly goals note not found: {path}\n"
            f"Expected format: Goals/YYYY/_monthly/YYYY-MM.md"
        )
    post = frontmatter.load(str(path))
    return post.content


def current_month() -> str:
    """Return the current month as a YYYY-MM string."""
    return date.today().strftime("%Y-%m")


def goals_output_path(month: str, vault_root: Optional[Path] = None) -> Path:
    """Return the path where the council review should be written."""
    root = vault_root or find_vault_root()
    year = month[:4]
    return root / "Goals" / year / "_monthly" / "reviews" / f"{month}-council.md"
