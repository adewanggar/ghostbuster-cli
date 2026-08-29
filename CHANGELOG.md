# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
