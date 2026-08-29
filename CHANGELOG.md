# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.2] - 2026-08-29

### Fixed

- Use absolute GitHub raw asset URLs in `README.md` so headers and icons render properly on PyPI and third-party package viewers.

## [0.2.1] - 2026-08-29

### Fixed

- `ghostbuster bust --confirm` now properly removes unused dependencies from `requirements.txt` and `pyproject.toml`.

## [0.2.0] - 2026-08-29

### Added

- **Pre-commit Hook Integration**: added `.pre-commit-hooks.yaml` for automated pre-commit scanning (`ghostbuster-scan`).
- **Auto-Fix for Orphan Files**: `ghostbuster bust --confirm` now automatically appends missing folders and files to `.gitignore`.
- **Auto-Fix for Phantom Env Vars**: `ghostbuster bust --confirm` now automatically appends missing environment variable stubs to `.env.example`.
- **Poetry Dependencies Support**: Dead Import Scanner now automatically parses `[tool.poetry.dependencies]` and `[tool.poetry.group.*.dependencies]`.
- Comprehensive test suite for all auto-fixers (`GitignoreFixer`, `EnvFixer`, `ImportFixer`).

## [0.1.0] - 2026-08-29

### Added

- `ghostbuster scan` command with 4 built-in scanners
- **Dead Import Scanner** - detects dependencies declared but never imported
- **Orphan File Scanner** - finds files/dirs that should be in .gitignore
- **Zombie Code Scanner** - detects functions/classes that are never called
- **Phantom Env Scanner** - finds env vars referenced but not set
- `ghostbuster bust` command with dry-run (default) and --confirm modes
- **Ghost Score** - weighted 0-100 technical debt score
- Formatted terminal output with tables, progress bars, and score cards
- JSON and Markdown output formats (`--format json|markdown`)
- Configuration via `.ghostbuster.toml` or `pyproject.toml [tool.ghostbuster]`
- Full test suite with pytest
- GitHub Actions CI (lint, test, build)
