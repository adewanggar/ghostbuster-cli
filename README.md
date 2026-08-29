<div align="center">

<img src="https://raw.githubusercontent.com/adewanggar/ghostbuster-cli/main/assets/readme_header.png" alt="Ghostbuster Header" width="100%" />

# Ghostbuster

**Find and bust the ghosts haunting your codebase.**

[![PyPI version](https://img.shields.io/pypi/v/ghostbuster-cli?logo=pypi&label=PyPI&color=3775A9)](https://pypi.org/project/ghostbuster-cli/)
[![Python](https://img.shields.io/pypi/pyversions/ghostbuster-cli?logo=python)](https://pypi.org/project/ghostbuster-cli/)
[![CI](https://github.com/adewanggar/ghostbuster-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/adewanggar/ghostbuster-cli/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

Unused dependencies, dead functions, orphan files, and phantom environment variables lurk in codebases - slowing down repos, confusing new contributors, and wasting CI minutes.

**Ghostbuster finds them all in one command.**

</div>

---

## <img src="https://raw.githubusercontent.com/adewanggar/ghostbuster-cli/main/assets/terminal_icon.png" width="24" height="24" valign="middle" /> Quick Start

```bash
# Install
pip install ghostbuster-cli

# Scan your project
ghostbuster scan

# No config needed.
```

## What It Finds

Ghostbuster detects **4 categories** in your codebase:

| Category | Identifier | What It Detects |
|:---------|:-----------|:----------------|
| **Dead Import** | `dead-import` | Dependencies in `requirements.txt` / `pyproject.toml` that are never imported |
| **Orphan File** | `orphan-file` | `node_modules/`, `venv/`, `.pyc`, large files that should be in `.gitignore` |
| **Zombie Code** | `zombie-code` | Functions and classes that are defined but never called from anywhere |
| **Phantom Env** | `phantom-env` | `os.environ["KEY"]` / `os.getenv("KEY")` where KEY is never set |

## Ghost Score

Every scan produces a **Ghost Score** (0-100) - the higher the score, the more technical debt in your codebase:

```
+----------------------- Ghost Score ------------------------+
|                                                            |
|    47 / 100                                                |
|                                                            |
|    #########################--------------------------     |
|                                                            |
|    Noticeable technical debt detected.                     |
|                                                            |
+------------------------------------------------------------+
```

## Auto-Fix

Ghostbuster can also fix detected issues:

```bash
# Preview what would be fixed (safe, default)
ghostbuster bust

# Actually apply fixes
ghostbuster bust --confirm
```

Currently auto-fixes:
- Removes unused import statements from Python files
- Appends missing orphan files and directories to `.gitignore`
- Appends missing environment variable stubs (`KEY=`) to `.env.example`

## Usage

### Basic Scan

```bash
# Scan current directory
ghostbuster scan

# Scan a specific path
ghostbuster scan ./my-project

# Verbose mode (show locations and fix suggestions)
ghostbuster scan -v
```

### Incremental / Git Diff Scan

Scan only files that were modified, staged, or untracked in your working tree:

```bash
# Scan modified files only (fast mode)
ghostbuster scan --diff

# Compare working branch against main/master
ghostbuster scan --diff-base origin/main
```

### Filtered Scan

```bash
# Only check for dead imports
ghostbuster scan --category dead-import

# Only check for zombie code
ghostbuster scan -c zombie-code
```

### Output Formats

```bash
# Default: formatted terminal output
ghostbuster scan

# JSON (for CI pipelines and scripting)
ghostbuster scan --format json

# Markdown (for pasting into issues/PRs)
ghostbuster scan --format markdown
```

### Pre-commit Hook Integration

Add Ghostbuster to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/adewanggar/ghostbuster-cli
    rev: v0.2.0
    hooks:
      - id: ghostbuster-scan
```

### CI Integration

```yaml
# .github/workflows/ghostbuster.yml
name: Ghost Check
on: [push, pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ghostbuster-cli
      - run: ghostbuster scan --format json
```

> Note: `ghostbuster scan` exits with code 1 if issues are found - ideal for CI gates.

## Configuration

Ghostbuster works with **zero config**, but you can customize it:

### `pyproject.toml`

```toml
[tool.ghostbuster]
exclude_dirs = ["migrations", "generated"]
ignore_packages = ["my-internal-lib"]
ignore_env_vars = ["CI", "GITHUB_ACTIONS"]
ignore_names = ["deprecated_helper"]
large_file_threshold = 5242880  # 5MB
```

### `.ghostbuster.toml`

```toml
exclude_dirs = ["vendor", "third_party"]
categories = ["dead-import", "phantom-env"]  # Only run these scanners
```

## How It Works

Ghostbuster uses **pure AST analysis** - no runtime imports, no code execution, no external services:

1. **Dead Imports**: Parses `requirements.txt`/`pyproject.toml` for declared dependencies, walks AST for imports, cross-references with a package-to-import mapping table.
2. **Orphan Files**: Walks the file tree checking for known ignorable patterns (`node_modules/`, `venv/`, `__pycache__/`, large binary files) and verifies they are covered by `.gitignore`.
3. **Zombie Code**: Collects all function/class definitions and references across the codebase, identifying definitions with zero references (skipping `__init__`, `test_*`, and decorated functions).
4. **Phantom Env**: Detects `os.environ["KEY"]`, `os.environ.get("KEY")`, `os.getenv("KEY")` patterns via AST and checks against `.env` files and system environment.

## Alternatives

| Tool | Scope | Ghostbuster Advantage |
|:-----|:------|:----------------------|
| [Vulture](https://github.com/jendrikseipp/vulture) | Dead code only | Ghostbuster also covers dependencies, files, and env vars |
| [deptry](https://deptry.com/) | Unused deps only | Ghostbuster is a superset with unified output |
| [deadcode](https://github.com/albertas/deadcode) | Dead code only | Ghostbuster adds auto-fix and unified scoring |
| [git-sizer](https://github.com/github/git-sizer) | Repo size | Ghostbuster checks .gitignore coverage |

## Roadmap

- [x] <img src="https://raw.githubusercontent.com/adewanggar/ghostbuster-cli/main/assets/npm_package_icon.png" width="18" height="18" valign="middle" /> Node.js / JavaScript / TypeScript support (`package.json`, `process.env`, `import.meta.env`)
- [x] Pre-commit hook integration (`.pre-commit-hooks.yaml`)
- [ ] GitHub Actions reporter (comment Ghost Score on PRs)
- [ ] Config inheritance for monorepos
- [ ] Ghost Score history tracking & trend chart

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
git clone https://github.com/adewanggar/ghostbuster-cli.git
cd ghostbuster-cli
pip install -e .
pip install pytest ruff mypy
pytest tests/ -v
```

## Support & Sponsor

If Ghostbuster helped clean up your codebase or saved CI minutes, consider supporting the project:

[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20on%20Ko--fi-FF5E5B?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/adewanggar)
[![Saweria](https://img.shields.io/badge/Saweria-Dukung%20lewat%20Saweria-FA8072?style=for-the-badge&logo=tether&logoColor=white)](https://saweria.co/adewanggar)

## License

MIT (c) Ghostbuster Contributors

---

<div align="center">

[Report Bug](https://github.com/adewanggar/ghostbuster-cli/issues) | [Request Feature](https://github.com/adewanggar/ghostbuster-cli/issues) | [Changelog](CHANGELOG.md)

</div>
