"""Page records and the metadata contract.

A page is an ordinary HTML file. Everything the swarm layer needs to know
about it is declared in ``<meta name="mplpb:*">`` tags, extending the
contract in MPLPB-LOCAL-008 5.1 with the two fields MPLPB-SWARM-013 5.3
adds: ``mplpb:origin`` and ``mplpb:origin_depth``.

Nothing here infers. A field that is absent is absent, and the validator
decides whether that is a defect. Inferring a missing status is how a
retired page becomes current by accident.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

ORIGINS = ("human", "taught", "derived")


class _Meta(HTMLParser):
    """Collect mplpb meta tags, the title, and internal hrefs."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.links: list[str] = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list) -> None:
        a = dict(attrs)
        if tag == "meta":
            name = (a.get("name") or "").strip()
            if name.startswith("mplpb:"):
                self.meta[name[6:]] = (a.get("content") or "").strip()
        elif tag == "a":
            href = (a.get("href") or "").strip()
            if href:
                self.links.append(href)
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data.strip()


@dataclass
class Page:
    """One crawled page, with the provenance that must travel with it."""

    doc_id: str
    path: str
    title: str = ""
    scope: str = ""
    status: str = "current"
    version: str = ""
    spoke: str = ""
    corpus: str = ""
    substrate: str = "local"
    origin: str = "human"
    origin_depth: int = 0
    supersedes: list[str] = field(default_factory=list)
    taught_from: list[str] = field(default_factory=list)
    ratified_by: str = ""
    classification: str = ""
    protected: bool = False
    links: list[str] = field(default_factory=list)
    text: str = ""

    @property
    def is_current(self) -> bool:
        return self.status == "current"

    def as_dict(self) -> dict:
        d = dict(self.__dict__)
        d.pop("text", None)
        return d


def _split_ids(raw: str) -> list[str]:
    """`mplpb:supersedes` is a semicolon-separated list (LOCAL-008 5.1)."""
    return [part.strip() for part in raw.split(";") if part.strip()]


def _text_of(html_source: str) -> str:
    without_tags = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html_source,
                          flags=re.S | re.I)
    without_tags = re.sub(r"<[^>]+>", " ", without_tags)
    return re.sub(r"\s+", " ", without_tags).strip()


def parse(html_source: str, path: str, spoke: str = "", corpus: str = "") -> Page:
    """Build a Page from HTML source. Missing fields stay missing."""
    parser = _Meta()
    parser.feed(html_source)
    m = parser.meta

    depth_raw = m.get("origin_depth", "0").strip()
    try:
        depth = int(depth_raw)
    except ValueError:
        depth = -1  # flagged by the validator rather than silently corrected

    origin = m.get("origin", "human").strip().lower()

    return Page(
        doc_id=m.get("id", ""),
        path=path,
        title=parser.title or m.get("id", ""),
        scope=m.get("scope", ""),
        status=m.get("status", "").strip().lower() or "current",
        version=m.get("version", ""),
        spoke=spoke,
        corpus=corpus or m.get("corpus", ""),
        substrate=m.get("substrate", "local"),
        origin=origin,
        origin_depth=depth,
        supersedes=_split_ids(m.get("supersedes", "")),
        taught_from=_split_ids(m.get("taught_from", "")),
        ratified_by=m.get("ratified_by", ""),
        classification=m.get("classification", ""),
        protected=m.get("protected", "").strip().lower() in ("1", "true", "yes"),
        links=parser.links,
        text=_text_of(html_source),
    )


def load(path: Path, root: Path, corpus: str = "") -> Page:
    rel = path.relative_to(root).as_posix()
    spoke = rel.split("/")[0] if "/" in rel else ""
    return parse(path.read_text(encoding="utf-8"), rel, spoke=spoke, corpus=corpus)
