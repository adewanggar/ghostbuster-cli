"""Scanner protocol and orchestrator for running all ghost detectors."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Protocol, runtime_checkable

from ghostbuster.core.models import Ghost, GhostCategory, ScanResult, Severity
from ghostbuster.core.scoring import calculate_score


@runtime_checkable
class Scanner(Protocol):
    """Protocol that all ghost scanners must implement.

    Each scanner is responsible for detecting one category of ghosts.
    Scanners must be pure logic — no CLI/UI side effects.
    """

    name: str

    def scan(self, path: Path) -> list[Ghost]:
        """Scan the given path and return a list of found ghosts."""
        ...


class ScanOrchestrator:
    """Runs all registered scanners and aggregates results.

    Usage::

        orchestrator = ScanOrchestrator()
        orchestrator.register(DeadImportScanner())
        orchestrator.register(OrphanFileScanner())
        result = orchestrator.run(Path("."))
    """

    def __init__(self) -> None:
        self._scanners: list[Scanner] = []

    def register(self, scanner: Scanner) -> None:
        """Register a scanner to be run during scan."""
        self._scanners.append(scanner)

    @property
    def scanner_names(self) -> list[str]:
        """Return names of all registered scanners."""
        return [s.name for s in self._scanners]

    def run(
        self,
        path: Path,
        categories: list[str] | None = None,
        changed_files: set[Path] | None = None,
    ) -> ScanResult:
        """Run all registered scanners (or filtered subset) on the given path.

        Args:
            path: Root directory to scan.
            categories: Optional list of category names to filter scanners.
                        If None, all scanners are run.
            changed_files: Optional set of changed file Paths from git diff.
                           If provided, results will be filtered to these files.

        Returns:
            Aggregated ScanResult with all ghosts found and a score.
        """
        start = time.perf_counter()
        all_ghosts: list[Ghost] = []

        scanners_to_run = self._scanners
        if categories:
            scanners_to_run = [s for s in self._scanners if s.name in categories]

        for scanner in scanners_to_run:
            try:
                ghosts = scanner.scan(path)
                all_ghosts.extend(ghosts)
            except Exception as exc:
                # Don't let one scanner crash the entire run.
                # In debug mode, the CLI layer will re-raise.
                all_ghosts.append(
                    Ghost(
                        category=GhostCategory.DEAD_IMPORT,
                        name=f"scanner-error-{scanner.name}",
                        message=f"Scanner '{scanner.name}' failed: {exc}",
                        severity=Severity.LOW,
                    )
                )

        # In diff mode, filter ghosts to only those originating in changed files
        if changed_files is not None:
            resolved_changed = {p.resolve() for p in changed_files}
            filtered_ghosts: list[Ghost] = []
            for g in all_ghosts:
                if g.file_path and g.file_path.resolve() in resolved_changed:
                    filtered_ghosts.append(g)
                elif not g.file_path:
                    # Keep findings without a specific file path (general warnings)
                    filtered_ghosts.append(g)
            all_ghosts = filtered_ghosts

        elapsed_ms = (time.perf_counter() - start) * 1000
        score = calculate_score(all_ghosts)

        return ScanResult(
            ghosts=all_ghosts,
            score=score,
            scanned_path=path,
            duration_ms=elapsed_ms,
        )


def create_default_orchestrator() -> ScanOrchestrator:
    """Create an orchestrator with all built-in scanners registered."""
    from ghostbuster.core.dead_imports import DeadImportScanner
    from ghostbuster.core.orphan_files import OrphanFileScanner
    from ghostbuster.core.phantom_env import PhantomEnvScanner
    from ghostbuster.core.zombie_code import ZombieCodeScanner

    orchestrator = ScanOrchestrator()
    orchestrator.register(DeadImportScanner())
    orchestrator.register(OrphanFileScanner())
    orchestrator.register(ZombieCodeScanner())
    orchestrator.register(PhantomEnvScanner())
    return orchestrator
