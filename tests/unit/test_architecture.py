"""
enforces the plan's package rules (section 3.1) so they can't rot:
imports only flow downward, and only core/config.py and bootstrap.py read the environment.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "gquarium"

# package -> what it may import (see docs/architecture.md). a "pkg.module" entry allows only
# that module; a bare "pkg" entry allows the whole package.
ALLOWED: dict[str, set[str]] = {
    "core": set(),
    "library": {"core"},
    "scene": {"core", "library.models"},
    "media": {"core", "library", "scene.base"},
    "streaming": {"core", "library", "media", "scene"},
    "web": {"core", "streaming", "library.models"},
}
ENV_READERS = {Path("core/config.py"), Path("bootstrap.py")}


def modules():
    for path in sorted(ROOT.rglob("*.py")):
        rel = path.relative_to(ROOT)
        if rel.parts[0] != path.name:  # inside a package (not top-level files)
            yield rel.parts[0], rel, path


def imported_gquarium_modules(path: Path):
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("gquarium."):
            yield node.module.removeprefix("gquarium.")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("gquarium."):
                    yield alias.name.removeprefix("gquarium.")


def permitted(package: str, target: str) -> bool:
    top = target.split(".")[0]
    if top == package:
        return True
    return any(target == a or target.startswith(a + ".") for a in ALLOWED[package])


def test_imports_only_flow_downward():
    """
    validate no package imports anything outside its allowed list
    """
    violations = [
        f"{rel}: imports gquarium.{target}"
        for package, rel, path in modules()
        for target in imported_gquarium_modules(path)
        if not permitted(package, target)
    ]
    assert not violations, "\n".join(violations)


def test_scene_never_imports_media():
    """
    validate the overlay stays decoupled from the pipeline
    """
    for package, rel, path in modules():
        if package == "scene":
            assert not any(t.startswith("media") for t in imported_gquarium_modules(path)), rel


def test_only_config_and_bootstrap_read_the_environment():
    """
    validate no other module touches os.environ or os.getenv
    """
    offenders = []
    for path in sorted(ROOT.rglob("*.py")):
        rel = path.relative_to(ROOT)
        if rel in ENV_READERS:
            continue
        text = path.read_text()
        if "os.environ" in text or "getenv" in text:
            offenders.append(str(rel))
    assert not offenders, offenders


def test_no_hardcoded_logger_names():
    """
    validate every module gets its logger from get_logger(__name__)
    """
    offenders = [
        str(path.relative_to(ROOT)) for path in sorted(ROOT.rglob("*.py"))
        if "logging.getLogger(" in path.read_text() and path.name != "log.py"
    ]
    assert not offenders, offenders
