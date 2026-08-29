"""Ghost Score calculation — the signature viraliy metric.

Computes a 0-100 "hauntedness" score based on ghost findings.
Designed to be provocative enough to screenshot and share.
"""

from __future__ import annotations

from ghostbuster.core.models import Ghost, GhostCategory, GhostScore, Severity

# Weight multipliers per category (reflects real-world severity impact)
CATEGORY_WEIGHTS: dict[GhostCategory, int] = {
    GhostCategory.DEAD_IMPORT: 5,    # Common, moderate waste
    GhostCategory.ORPHAN_FILE: 8,    # Disk space, clone time
    GhostCategory.ZOMBIE_CODE: 3,    # Confusing but usually harmless
    GhostCategory.PHANTOM_ENV: 10,   # Can cause runtime crashes
}

# Bonus weight for high-severity ghosts
SEVERITY_MULTIPLIER: dict[Severity, float] = {
    Severity.LOW: 0.5,
    Severity.MEDIUM: 1.0,
    Severity.HIGH: 1.5,
}

# Score thresholds and their labels
SCORE_LABELS: list[tuple[int, str]] = [
    (0, "No ghosts detected. Your codebase is clean!"),
    (10, "Almost clean - just a few minor issues."),
    (20, "Mildly affected. Nothing a quick cleanup cannot fix."),
    (35, "Multiple issues detected. Time for cleanup."),
    (50, "Noticeable technical debt detected."),
    (70, "Seriously affected. Your codebase needs significant cleanup."),
    (85, "Extremely cluttered with unused code and files."),
    (100, "Severe technical debt detected across multiple categories."),
]


def calculate_score(ghosts: list[Ghost]) -> GhostScore:
    """Calculate the Ghost Score from a list of ghost findings.

    The score is a weighted sum of ghosts, capped at 100.
    Each ghost contributes its category weight × severity multiplier.

    Args:
        ghosts: List of Ghost findings from all scanners.

    Returns:
        GhostScore with value (0-100), label, and per-category breakdown.
    """
    if not ghosts:
        return GhostScore(
            value=0,
            label=SCORE_LABELS[0][1],
            breakdown={cat: 0 for cat in GhostCategory},
        )

    # Calculate raw score with weighted contributions
    raw_score = 0.0
    breakdown: dict[GhostCategory, int] = {cat: 0 for cat in GhostCategory}

    for ghost in ghosts:
        weight = CATEGORY_WEIGHTS.get(ghost.category, 3)
        multiplier = SEVERITY_MULTIPLIER.get(ghost.severity, 1.0)
        contribution = weight * multiplier
        raw_score += contribution
        breakdown[ghost.category] = breakdown.get(ghost.category, 0) + 1

    # Cap at 100
    final_score = min(int(raw_score), 100)

    # Find the appropriate label
    label = SCORE_LABELS[-1][1]  # Default to worst
    for threshold, score_label in SCORE_LABELS:
        if final_score <= threshold:
            label = score_label
            break

    return GhostScore(
        value=final_score,
        label=label,
        breakdown=breakdown,
    )
