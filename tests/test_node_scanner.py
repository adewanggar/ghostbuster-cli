"""Tests for Node.js / TypeScript ecosystem scanning and fixing."""

from __future__ import annotations

import json
from pathlib import Path

from ghostbuster.core.dead_imports import DeadImportScanner
from ghostbuster.core.models import Ghost, GhostCategory, Severity
from ghostbuster.core.phantom_env import PhantomEnvScanner
from ghostbuster.fixers.import_fixer import ImportFixer


class TestNodeDeadImportScanner:
    """Tests for DeadImportScanner on Node.js / TypeScript projects."""

    def test_detects_unused_package_json_dependency(self, tmp_path: Path) -> None:
        """Should detect packages declared in package.json but not imported."""
        pkg_json = tmp_path / "package.json"
        pkg_json.write_text(
            json.dumps(
                {
                    "name": "my-app",
                    "dependencies": {
                        "lodash": "^4.17.21",
                        "axios": "^1.6.0",
                    },
                }
            ),
            encoding="utf-8",
        )

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "index.ts").write_text(
            'import axios from "axios";\nconsole.log(axios);\n',
            encoding="utf-8",
        )

        scanner = DeadImportScanner()
        ghosts = scanner.scan(tmp_path)

        assert len(ghosts) == 1
        assert ghosts[0].name == "lodash"
        assert ghosts[0].category == GhostCategory.DEAD_IMPORT

    def test_handles_scoped_packages_and_subpaths(self, tmp_path: Path) -> None:
        """Should recognize scoped packages (@tanstack/react-query) and subpath imports."""
        pkg_json = tmp_path / "package.json"
        pkg_json.write_text(
            json.dumps(
                {
                    "name": "my-app",
                    "dependencies": {
                        "@tanstack/react-query": "^5.0.0",
                        "lodash": "^4.17.21",
                    },
                }
            ),
            encoding="utf-8",
        )

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "App.tsx").write_text(
            """
            import { useQuery } from '@tanstack/react-query';
            import debounce from 'lodash/debounce';
            export function App() { return null; }
            """,
            encoding="utf-8",
        )

        scanner = DeadImportScanner()
        ghosts = scanner.scan(tmp_path)
        assert len(ghosts) == 0

    def test_ignores_node_tool_packages(self, tmp_path: Path) -> None:
        """Should skip build tools, linters, and type packages."""
        pkg_json = tmp_path / "package.json"
        pkg_json.write_text(
            json.dumps(
                {
                    "name": "my-app",
                    "devDependencies": {
                        "typescript": "^5.0.0",
                        "@types/node": "^20.0.0",
                        "eslint": "^8.0.0",
                        "prettier": "^3.0.0",
                        "vite": "^5.0.0",
                        "tailwindcss": "^3.0.0",
                    },
                }
            ),
            encoding="utf-8",
        )

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "index.js").write_text("console.log('clean');\n", encoding="utf-8")

        scanner = DeadImportScanner()
        ghosts = scanner.scan(tmp_path)
        assert len(ghosts) == 0


class TestNodePhantomEnvScanner:
    """Tests for PhantomEnvScanner on JS/TS files."""

    def test_detects_process_env_in_js(self, tmp_path: Path) -> None:
        """Should detect process.env and import.meta.env variables."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        (src_dir / "config.js").write_text(
            """
            const dbUrl = process.env.DATABASE_URL;
            const secret = process.env['JWT_SECRET'];
            const apiKey = import.meta.env.VITE_API_KEY;
            """,
            encoding="utf-8",
        )

        scanner = PhantomEnvScanner()
        ghosts = scanner.scan(tmp_path)

        names = {g.name for g in ghosts}
        assert "DATABASE_URL" in names
        assert "JWT_SECRET" in names
        assert "VITE_API_KEY" in names

    def test_skips_defined_env_vars(self, tmp_path: Path) -> None:
        """Should not flag env vars defined in .env or .env.local."""
        (tmp_path / ".env").write_text(
            "DATABASE_URL=postgres://localhost:5432/db\nJWT_SECRET=xyz\n",
            encoding="utf-8",
        )

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "app.ts").write_text(
            "const url = process.env.DATABASE_URL;\nconst secret = process.env.JWT_SECRET;\n",
            encoding="utf-8",
        )

        scanner = PhantomEnvScanner()
        ghosts = scanner.scan(tmp_path)
        assert len(ghosts) == 0


class TestNodeImportFixer:
    """Tests for ImportFixer on package.json."""

    def test_removes_dead_dependency_from_package_json(self, tmp_path: Path) -> None:
        """Should remove dead package from package.json cleanly."""
        pkg_json = tmp_path / "package.json"
        pkg_json.write_text(
            json.dumps(
                {
                    "name": "my-app",
                    "dependencies": {
                        "react": "^18.0.0",
                        "unused-lib": "^1.0.0",
                    },
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        ghosts = [
            Ghost(
                category=GhostCategory.DEAD_IMPORT,
                name="unused-lib",
                message="unused-lib is unused",
                file_path=pkg_json,
                severity=Severity.MEDIUM,
                fixable=True,
            ),
        ]

        fixer = ImportFixer()
        preview = fixer.preview(ghosts, tmp_path)
        assert any("unused-lib" in p for p in preview)

        applied = fixer.fix(ghosts, tmp_path)
        assert len(applied) == 1

        data = json.loads(pkg_json.read_text(encoding="utf-8"))
        assert "unused-lib" not in data["dependencies"]
        assert "react" in data["dependencies"]
