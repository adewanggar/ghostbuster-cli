"""Tests for Ghost Score calculation."""

from __future__ import annotations

from ghostbuster.core.models import Ghost, GhostCategory, Severity
from ghostbuster.core.scoring import calculate_score


class TestGhostScoring:
    """Tests for the Ghost Score algorithm."""

    def test_empty_ghosts(self) -> None:
        """Score should be 0 with no ghosts."""
        score = calculate_score([])
        assert score.value == 0
        assert "clean" in score.label.lower()

    def test_single_dead_import(self) -> None:
        """A single dead import should contribute a small score."""
        ghosts = [
            Ghost(
                category=GhostCategory.DEAD_IMPORT,
                name="flask",
                message="Unused",
                severity=Severity.MEDIUM,
            ),
        ]
        score = calculate_score(ghosts)
        assert score.value == 5  # weight 5 × multiplier 1.0

    def test_single_phantom_env(self) -> None:
        """A phantom env should contribute heavily (it can crash at runtime)."""
        ghosts = [
            Ghost(
                category=GhostCategory.PHANTOM_ENV,
                name="API_KEY",
                message="Missing",
                severity=Severity.HIGH,
            ),
        ]
        score = calculate_score(ghosts)
        assert score.value == 15  # weight 10 × multiplier 1.5

    def test_score_caps_at_100(self) -> None:
        """Score should never exceed 100."""
        ghosts = [
            Ghost(
                category=GhostCategory.PHANTOM_ENV,
                name=f"VAR_{i}",
                message="Missing",
                severity=Severity.HIGH,
            )
            for i in range(50)  # 50 × 10 × 1.5 = 750 raw
        ]
        score = calculate_score(ghosts)
        assert score.value == 100

    def test_breakdown_by_category(self) -> None:
        """Score breakdown should count ghosts per category."""
        ghosts = [
            Ghost(category=GhostCategory.DEAD_IMPORT, name="a", message="", severity=Severity.MEDIUM),
            Ghost(category=GhostCategory.DEAD_IMPORT, name="b", message="", severity=Severity.MEDIUM),
            Ghost(category=GhostCategory.ORPHAN_FILE, name="c", message="", severity=Severity.HIGH),
        ]
        score = calculate_score(ghosts)
        assert score.breakdown[GhostCategory.DEAD_IMPORT] == 2
        assert score.breakdown[GhostCategory.ORPHAN_FILE] == 1
        assert score.breakdown[GhostCategory.ZOMBIE_CODE] == 0

    def test_severity_multiplier(self) -> None:
        """Higher severity should contribute more to the score."""
        low = [Ghost(category=GhostCategory.ZOMBIE_CODE, name="a", message="", severity=Severity.LOW)]
        high = [Ghost(category=GhostCategory.ZOMBIE_CODE, name="b", message="", severity=Severity.HIGH)]

        score_low = calculate_score(low)
        score_high = calculate_score(high)
        assert score_high.value > score_low.value

    def test_label_for_medium_score(self) -> None:
        """Should get an appropriate label for a medium score."""
        ghosts = [
            Ghost(
                category=GhostCategory.DEAD_IMPORT,
                name=f"pkg_{i}",
                message="Unused",
                severity=Severity.MEDIUM,
            )
            for i in range(8)  # 8 × 5 = 40 raw
        ]
        score = calculate_score(ghosts)
        assert score.value == 40
        assert "debt" in score.label.lower() or "cleanup" in score.label.lower()

    def test_score_serialization(self) -> None:
        """GhostScore.to_dict() should be JSON-serializable."""
        ghosts = [
            Ghost(category=GhostCategory.DEAD_IMPORT, name="a", message="test", severity=Severity.MEDIUM),
        ]
        score = calculate_score(ghosts)
        data = score.to_dict()
        assert isinstance(data["score"], int)
        assert isinstance(data["label"], str)
        assert isinstance(data["breakdown"], dict)
