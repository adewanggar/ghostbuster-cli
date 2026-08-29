"""Shared pytest fixtures for ghostbuster tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a minimal Python project structure for testing."""
    # Create a basic project layout
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    main_py = src_dir / "main.py"
    main_py.write_text(
        'import os\nimport json\nfrom pathlib import Path\n\ndef main():\n    print("hello")\n',
        encoding="utf-8",
    )

    return tmp_path


@pytest.fixture
def project_with_requirements(tmp_project: Path) -> Path:
    """Create a project with a requirements.txt that has unused deps."""
    req = tmp_project / "requirements.txt"
    req.write_text(
        "requests>=2.28.0\nflask>=2.0.0\nnumpy>=1.24.0\n",
        encoding="utf-8",
    )

    # Only actually import requests
    src = tmp_project / "src" / "app.py"
    src.write_text(
        'import requests\n\ndef fetch():\n    return requests.get("https://example.com")\n',
        encoding="utf-8",
    )

    return tmp_project


@pytest.fixture
def project_with_pyproject(tmp_project: Path) -> Path:
    """Create a project with pyproject.toml dependencies."""
    pyproject = tmp_project / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test-project"\nversion = "0.1.0"\n'
        'dependencies = [\n    "requests>=2.28.0",\n    "click>=8.0.0",\n'
        '    "pyyaml>=6.0",\n]\n',
        encoding="utf-8",
    )

    # Only import requests and yaml
    src = tmp_project / "src" / "app.py"
    src.write_text(
        "import requests\nimport yaml\n\ndef run():\n    pass\n",
        encoding="utf-8",
    )

    return tmp_project


@pytest.fixture
def project_with_orphans(tmp_project: Path) -> Path:
    """Create a project with files that should be gitignored."""
    # Create node_modules directory (should be gitignored)
    nm = tmp_project / "node_modules" / "some-package"
    nm.mkdir(parents=True)
    (nm / "index.js").write_text("module.exports = {}", encoding="utf-8")

    # Create __pycache__ (should be gitignored)
    cache = tmp_project / "__pycache__"
    cache.mkdir()
    (cache / "main.cpython-312.pyc").write_bytes(b"\x00" * 100)

    # Create venv (should be gitignored)
    venv = tmp_project / "venv" / "lib"
    venv.mkdir(parents=True)

    return tmp_project


@pytest.fixture
def project_with_zombies(tmp_project: Path) -> Path:
    """Create a project with dead functions."""
    code = tmp_project / "src" / "utils.py"
    code.write_text(
        'def used_function():\n    return "I am used"\n\n'
        'def unused_helper():\n    return "Nobody calls me"\n\n'
        'def another_unused():\n    return "Also dead"\n\n'
        "class UnusedClass:\n    pass\n",
        encoding="utf-8",
    )

    # main.py calls used_function but not the others
    main = tmp_project / "src" / "main.py"
    main.write_text(
        "from utils import used_function\n\ndef main():\n    result = used_function()\n    print(result)\n",
        encoding="utf-8",
    )

    return tmp_project


@pytest.fixture
def project_with_phantom_envs(tmp_project: Path) -> Path:
    """Create a project referencing env vars that don't exist."""
    code = tmp_project / "src" / "config.py"
    code.write_text(
        "import os\n\n"
        'DATABASE_URL = os.environ["DATABASE_URL"]\n'
        'SECRET_KEY = os.environ.get("SECRET_KEY")\n'
        'API_KEY = os.getenv("API_KEY")\n'
        'DEBUG = os.environ.get("DEBUG", "false")\n',
        encoding="utf-8",
    )

    # Create a .env file with only some of these
    env_file = tmp_project / ".env"
    env_file.write_text(
        "DATABASE_URL=postgres://localhost/db\nDEBUG=true\n",
        encoding="utf-8",
    )

    return tmp_project
