"""Bounded traversal of one corpus root.

MPLPB-LOCAL-008 2.2 specifies the crawl and 7.1 specifies three ingestion
paths: the graph, the retired directory, and the orphan sweep. Federation
does not relax the boundary (MPLPB-SWARM-013 6.1) — a link leaving the root
is external, is recorded as such, and is never followed.
"""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

from mplpb_swarm.page import Page, load

SUPERSEDED_DIR = "_log/superseded"
SWARM_DIR = "_swarm"


@dataclass
class CrawlResult:
    pages: list[Page] = field(default_factory=list)
    via_graph: int = 0
    via_retired: int = 0
    via_orphan: int = 0
    external: list[str] = field(default_factory=list)

    def by_id(self) -> dict[str, Page]:
        return {p.doc_id: p for p in self.pages if p.doc_id}

    def current(self) -> list[Page]:
        return [p for p in self.pages if p.is_current]


def _resolve(base_rel: str, href: str) -> str | None:
    """Resolve href against a page's relative path. None means external."""
    if urllib.parse.urlparse(href).scheme or href.startswith("//"):
        return None
    href = href.split("#", 1)[0].split("?", 1)[0]
    if not href:
        return None
    base = Path(base_rel).parent
    target = (base / href) if base.as_posix() != "." else Path(href)
    parts: list[str] = []
    for part in target.as_posix().split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                return None  # would escape the root
            parts.pop()
        else:
            parts.append(part)
    return "/".join(parts) if parts else None


def crawl(root: Path, corpus: str = "", entry: str = "index.html") -> CrawlResult:
    """Enumerate a corpus root by graph, then retired, then orphan sweep."""
    root = Path(root).resolve()
    result = CrawlResult()
    seen: set[str] = set()

    def ingest(rel: str) -> Page | None:
        target = root / rel
        if not target.is_file() or rel in seen:
            return None
        seen.add(rel)
        page = load(target, root, corpus=corpus)
        result.pages.append(page)
        return page

    # Path one: the graph, from the declared entry point.
    queue = [entry]
    while queue:
        rel = queue.pop(0)
        if rel in seen:
            continue
        page = ingest(rel)
        if page is None:
            continue
        result.via_graph += 1
        for href in page.links:
            resolved = _resolve(rel, href)
            if resolved is None:
                continue  # external; recorded in the post-pass below
            if resolved.startswith(SWARM_DIR + "/"):
                continue
            if resolved.endswith(".html") and resolved not in seen:
                queue.append(resolved)

    # Path two: retired pages, which the graph deliberately no longer reaches.
    retired_root = root / SUPERSEDED_DIR
    if retired_root.is_dir():
        for f in sorted(retired_root.rglob("*.html")):
            rel = f.relative_to(root).as_posix()
            if ingest(rel) is not None:
                result.via_retired += 1

    # Path three: orphan sweep. A page on disk that nothing links to still
    # exists, and a corpus that cannot see it cannot maintain it.
    for f in sorted(root.rglob("*.html")):
        rel = f.relative_to(root).as_posix()
        if rel.startswith(SWARM_DIR + "/"):
            continue
        if ingest(rel) is not None:
            result.via_orphan += 1

    # External links are recorded for every ingested page, not only for the
    # ones the graph reached. A page that leaves the corpus does so whether
    # or not anything links to it.
    external: list[str] = []
    for page in result.pages:
        for href in page.links:
            if _resolve(page.path, href) is None:
                external.append(href)
    result.external = external

    return result
