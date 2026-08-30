"""Shared fixtures. Every test builds its corpus in a temporary directory,
so no test can leave a defect behind for the next one to find.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SITE = REPO / "site"

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
{meta}
</head>
<body><main><h1>{title}</h1>{body}</main></body>
</html>
"""


def page_source(title: str, body: str = "<p>body text.</p>", **fields) -> str:
    meta = "\n".join(
        f'  <meta name="mplpb:{k}" content="{v}">'
        for k, v in fields.items() if v not in (None, "")
    )
    return PAGE.format(title=title, meta=meta, body=body)


class CorpusTest(unittest.TestCase):
    """A test with a writable temporary root."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="mplpb-swarm-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.root = self.tmp / "corpus"
        self.root.mkdir()

    def write(self, rel: str, title: str, body: str = "<p>body text.</p>",
              **fields) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(page_source(title, body, **fields), encoding="utf-8")
        return path

    def seed_minimal(self) -> None:
        """A root, one spoke, one page, one retired page."""
        self.write(
            "index.html", "Main Index",
            '<ul><li><a href="ops/_index.html">Operations</a></li></ul>',
            id="MAIN-000", corpus="TEST", scope="Test corpus root",
            status="current", origin="human", origin_depth="0")
        self.write(
            "ops/_index.html", "Operations",
            '<ul><li><a href="alpha.html">Alpha</a></li></ul>',
            id="OPS-INDEX-001", corpus="TEST", scope="Operational procedures",
            status="current", origin="human", origin_depth="0")
        self.write(
            "ops/alpha.html", "Alpha", "<p>alpha procedure.</p>",
            id="OPS-ALPHA-002", corpus="TEST",
            scope="The alpha procedure and its preconditions",
            status="current", version="v2", supersedes="OPS-ALPHA-001",
            origin="human", origin_depth="0")
        self.write(
            "_log/superseded/alpha_v1.html", "Alpha (retired)",
            "<p>retired alpha.</p>",
            id="OPS-ALPHA-001", corpus="TEST", scope="Superseded alpha",
            status="retired", version="v1", origin="human", origin_depth="0")


class SiteTest(unittest.TestCase):
    """A test against a disposable copy of the shipped demo site."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="mplpb-site-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.site = self.tmp / "site"
        shutil.copytree(SITE, self.site)
        self.corpus_a = self.site / "corpus-a"
        self.corpus_b = self.site / "corpus-b"
        self.registry_root = self.site / "registry"
