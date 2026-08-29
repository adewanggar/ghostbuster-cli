# Contributing to Ghostbuster

First off, thank you for considering contributing to Ghostbuster!

## Development Setup

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Quick Start

```bash
# Clone the repo
git clone https://github.com/adewanggar/ghostbuster-cli.git
cd ghostbuster-cli

# Create virtual environment & install in development mode
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]" 2>/dev/null || pip install -e .
pip install pytest ruff mypy

# Run the tool locally
ghostbuster scan .

# Run tests
pytest tests/ -v

# Run linter
ruff check src/ tests/

# Run type checker
mypy src/
```

## Making Changes

### Code Style

- We use **Ruff** for linting and formatting.
- All code must have **type hints**.
- Follow the existing code patterns - especially the core/CLI separation.

### Architecture Rules

1. **`core/`** must NOT import from `cli/`, `rich`, or any UI library.
2. **`cli/`** is the only layer that touches terminal I/O.
3. Each scanner is a self-contained module implementing the `Scanner` protocol.
4. All new scanners must be registered in `scanner.py:create_default_orchestrator()`.

### Adding a New Scanner

1. Create `src/ghostbuster/core/my_scanner.py`
2. Implement the `Scanner` protocol (must have `name: str` and `scan(path) -> list[Ghost]`)
3. Register in `create_default_orchestrator()`
4. Add tests in `tests/test_my_scanner.py`
5. Update the README feature list

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_dead_imports.py -v

# Run with coverage
pip install pytest-cov
pytest tests/ --cov=ghostbuster --cov-report=html
```

### Commit Messages

Use conventional commit messages:

```
feat: add Node.js dependency scanner
fix: handle missing pyproject.toml gracefully
docs: update README with new scanner info
test: add edge case for empty requirements.txt
chore: bump ruff version
```

## Pull Request Process

1. Fork the repo and create a feature branch from `main`.
2. Make your changes with tests.
3. Ensure all checks pass: `ruff check`, `mypy`, `pytest`.
4. Open a PR with a clear description of what you changed and why.
5. Wait for review - we aim to respond within 48 hours.

## Reporting Bugs

Open an issue with:
- Your OS and Python version
- The command you ran
- Expected vs actual behavior
- Minimal reproducible example (if possible)

## Feature Requests

Open an issue with:
- What problem does it solve?
- Who would use it?
- Any implementation ideas?

## Code of Conduct

Be kind, be constructive, and respect other contributors.
