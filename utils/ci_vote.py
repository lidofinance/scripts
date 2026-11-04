"""Select a discovered vote script for an external regression run."""

from pathlib import Path
from typing import Optional, Sequence


def select_vote_script(vote_files: Sequence[str], requested: str = "") -> Optional[str]:
    """Keep auto-selection strict; an explicit filename must match a discovered script."""
    if requested:
        matches = [path for path in vote_files if Path(path).name == requested]
        if len(matches) != 1:
            raise RuntimeError(f"VOTE_SCRIPT must name exactly one discovered vote/upgrade script: {requested!r}")
        return matches[0]
    if not vote_files:
        return None
    if len(vote_files) > 1:
        raise RuntimeError("More than one vote script found.")
    return vote_files[0]
