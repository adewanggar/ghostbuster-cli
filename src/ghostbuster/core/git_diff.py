"""Git Diff helper - detects changed and untracked files in git repositories."""

from __future__ import annotations

import subprocess
from pathlib import Path


def get_changed_files(path: Path, base_ref: str | None = None) -> set[Path]:
    """Get the set of changed, added, and untracked files in a git repository.

    Args:
        path: Root path of the project.
        base_ref: Optional git reference/branch to compare against (e.g. 'main', 'origin/main', 'HEAD~1').

    Returns:
        A set of absolute Paths for all modified/added/untracked files.
    """
    changed: set[Path] = set()

    # Verify directory is a git repository
    try:
        check_git = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=path,
            capture_output=True,
            text=True,
            check=False,
        )
        if check_git.returncode != 0:
            return changed
    except (OSError, FileNotFoundError):
        return changed

    commands: list[list[str]] = []

    if base_ref:
        # Compare current working state or branch against base_ref
        commands.append(["git", "diff", "--name-only", "--diff-filter=ACMR", base_ref])
    else:
        # Unstaged changes in working tree
        commands.append(["git", "diff", "--name-only", "--diff-filter=ACMR"])
        # Staged changes in index
        commands.append(["git", "diff", "--name-only", "--cached", "--diff-filter=ACMR"])

    # Also capture untracked files from git status
    commands.append(["git", "status", "--porcelain"])

    for cmd in commands:
        try:
            res = subprocess.run(
                cmd,
                cwd=path,
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    line = line.strip()
                    if not line:
                        continue

                    # Parse git status --porcelain output: '?? path/to/file' or 'M  path/to/file'
                    if cmd[1] == "status":
                        parts = line.split(maxsplit=1)
                        if len(parts) == 2:
                            rel_file = parts[1].strip('"')
                            file_path = (path / rel_file).resolve()
                            if file_path.exists():
                                changed.add(file_path)
                    else:
                        # Parse git diff --name-only output
                        file_path = (path / line).resolve()
                        if file_path.exists():
                            changed.add(file_path)
        except OSError:
            continue

    return changed
