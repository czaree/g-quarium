"""
docs drift test: fails if a setting's environment variable is missing from
docs/configuration.md, or a relative link in README.md or docs/ is broken.
"""

import re
from pathlib import Path

from gquarium.core.config import ENV_VARS

REPO = Path(__file__).resolve().parents[2]
DOCS = [REPO / "README.md", *sorted((REPO / "docs").glob("*.md"))]
LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)\)")
HEADER = re.compile(r"Last updated for phase \d")


def test_every_env_var_is_documented():
    """
    validate docs/configuration.md mentions every environment variable the app reads
    """
    text = (REPO / "docs" / "configuration.md").read_text()
    missing = [v.name for v in ENV_VARS if f"`{v.name}`" not in text]
    assert not missing, f"undocumented in docs/configuration.md: {missing}"


def test_relative_links_resolve():
    """
    validate every relative link in README.md and docs/ points at a real file
    """
    broken = []
    for doc in DOCS:
        for target in LINK.findall(doc.read_text()):
            if re.match(r"[a-z]+:", target) or target.startswith("#"):
                continue
            if not (doc.parent / target.split("#")[0]).resolve().exists():
                broken.append(f"{doc.relative_to(REPO)} -> {target}")
    assert not broken, broken
