"""Tests for the Zombie Code Scanner."""

from __future__ import annotations

from pathlib import Path

from ghostbuster.core.models import GhostCategory
from ghostbuster.core.zombie_code import ZombieCodeScanner


class TestZombieCodeScanner:
    """Tests for ZombieCodeScanner."""

    def setup_method(self) -> None:
        self.scanner = ZombieCodeScanner()

    def test_empty_project(self, tmp_path: Path) -> None:
        """Should return empty list for an empty project."""
        ghosts = self.scanner.scan(tmp_path)
        assert ghosts == []

    def test_detects_unused_function(self, tmp_path: Path) -> None:
        """Should detect a function that is never called."""
        (tmp_path / "app.py").write_text(
            'def used_fn():\n    return 1\n\n'
            'def never_called():\n    return 2\n\n'
            'result = used_fn()\n',
            encoding="utf-8",
        )
        ghosts = self.scanner.scan(tmp_path)
        ghost_names = {g.name for g in ghosts}
        assert "never_called" in ghost_names
        assert "used_fn" not in ghost_names

    def test_skips_dunder_methods(self, tmp_path: Path) -> None:
        """Should not flag dunder methods like __init__."""
        (tmp_path / "app.py").write_text(
            'class MyClass:\n'
            '    def __init__(self):\n        pass\n'
            '    def __repr__(self):\n        return "MyClass"\n',
            encoding="utf-8",
        )
        ghosts = self.scanner.scan(tmp_path)
        ghost_names = {g.name for g in ghosts}
        assert "__init__" not in ghost_names
        assert "__repr__" not in ghost_names

    def test_skips_test_functions(self, tmp_path: Path) -> None:
        """Should not flag functions starting with test_."""
        (tmp_path / "test_app.py").write_text(
            'def test_something():\n    assert True\n\n'
            'def test_another():\n    assert 1 + 1 == 2\n',
            encoding="utf-8",
        )
        ghosts = self.scanner.scan(tmp_path)
        assert ghosts == []

    def test_skips_decorated_functions(self, tmp_path: Path) -> None:
        """Should not flag functions with framework decorators."""
        (tmp_path / "app.py").write_text(
            'from functools import lru_cache\n\n'
            '@property\n'
            'def my_property(self):\n    return 1\n\n'
            '@lru_cache\n'
            'def cached_fn():\n    return 2\n',
            encoding="utf-8",
        )
        ghosts = self.scanner.scan(tmp_path)
        ghost_names = {g.name for g in ghosts}
        assert "my_property" not in ghost_names
        assert "cached_fn" not in ghost_names

    def test_ghost_category(self, tmp_path: Path) -> None:
        """All ghosts should have the ZOMBIE_CODE category."""
        (tmp_path / "app.py").write_text(
            'def orphan():\n    return "dead"\n',
            encoding="utf-8",
        )
        ghosts = self.scanner.scan(tmp_path)
        assert all(g.category == GhostCategory.ZOMBIE_CODE for g in ghosts)

    def test_detects_unused_class(self, tmp_path: Path) -> None:
        """Should detect a class that is never referenced."""
        (tmp_path / "app.py").write_text(
            'class UsedClass:\n    pass\n\n'
            'class DeadClass:\n    pass\n\n'
            'obj = UsedClass()\n',
            encoding="utf-8",
        )
        ghosts = self.scanner.scan(tmp_path)
        ghost_names = {g.name for g in ghosts}
        assert "DeadClass" in ghost_names
        assert "UsedClass" not in ghost_names

    def test_skips_main_function(self, tmp_path: Path) -> None:
        """Should not flag the main() function."""
        (tmp_path / "app.py").write_text(
            'def main():\n    print("hello")\n',
            encoding="utf-8",
        )
        ghosts = self.scanner.scan(tmp_path)
        ghost_names = {g.name for g in ghosts}
        assert "main" not in ghost_names
