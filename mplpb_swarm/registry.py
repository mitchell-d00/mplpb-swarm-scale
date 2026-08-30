"""The corpus registry and cross-corpus routing (MPLPB-SWARM-013 6).

The registry is itself an MPLPB corpus: HTML pages with metadata blocks,
one per registered corpus. This is not decorative symmetry. It means the
registry validates with the same validator, supersedes with the same
discipline, and is crawled by the same crawler. A registry kept as a config
file is a second kind of object with a second set of failure modes and no
janitor.

Routing between corpora is the MPLPB-SEP-007 precedence rule with corpora
in place of spokes. A tie inside the margin returns ambiguous, names the
corpora, quotes their declared scopes, and stops. It does not merge:
merging across owners produces an answer nobody is accountable for.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from mplpb_swarm.crawl import crawl
from mplpb_swarm.page import Page

MARGIN = 0.15

_STOP = {
    "a", "an", "and", "are", "as", "at", "be", "by", "do", "for", "from",
    "how", "i", "in", "is", "it", "of", "on", "or", "that", "the", "this",
    "to", "we", "what", "when", "where", "which", "who", "with", "you",
}


def terms(text: str) -> set[str]:
    """Content terms. A shared ordinary word is not a match."""
    return {w for w in re.findall(r"[a-z0-9]+", text.lower())
            if w not in _STOP and len(w) > 2}


@dataclass(frozen=True)
class Entry:
    corpus_id: str
    root: Path
    scope: str
    owner: str = ""
    substrate: str = "local"
    classification: str = ""

    def score(self, query: str) -> float:
        q = terms(query)
        if not q:
            return 0.0
        return len(q & terms(self.scope)) / len(q)


@dataclass
class Decision:
    kind: str                       # routed | ambiguous | no_owner
    query: str
    corpus: Entry | None = None
    touched: list[tuple[Entry, float]] = field(default_factory=list)

    def explain(self) -> str:
        if self.kind == "routed" and self.corpus:
            return f"routed to {self.corpus.corpus_id}: {self.corpus.scope}"
        if self.kind == "ambiguous":
            lines = ["ambiguous — more than one corpus declares this:"]
            for entry, score in self.touched:
                lines.append(f"  {entry.corpus_id} ({score:.2f}) — {entry.scope}")
            lines.append("narrow the question, or name a corpus.")
            return "\n".join(lines)
        return "no registered corpus declares scope over this question."


class Registry:
    """A registry loaded from its own corpus root."""

    def __init__(self, entries: list[Entry]) -> None:
        self.entries = entries

    def __len__(self) -> int:
        return len(self.entries)

    def get(self, corpus_id: str) -> Entry | None:
        for entry in self.entries:
            if entry.corpus_id == corpus_id:
                return entry
        return None

    @classmethod
    def from_root(cls, registry_root: Path) -> "Registry":
        """Load registry entries from the registry corpus.

        Roots are resolved relative to the registry root, so a registry and
        the corpora it names move together.
        """
        registry_root = Path(registry_root).resolve()
        result = crawl(registry_root, corpus="REGISTRY")
        entries = []
        for page in result.current():
            source = registry_root / page.path
            raw_root = _meta_of(source, "root")
            corpus_id = _meta_of(source, "corpus")
            if not raw_root or not corpus_id:
                continue  # the registry index itself declares no root
            entries.append(Entry(
                corpus_id=corpus_id,
                root=(registry_root / raw_root).resolve(),
                scope=page.scope,
                owner=_meta_of(source, "owner"),
                substrate=page.substrate,
                classification=page.classification,
            ))
        return cls(sorted(entries, key=lambda e: e.corpus_id))

    def route(self, query: str, margin: float = MARGIN) -> Decision:
        """Score the query against every declared scope and decide."""
        scored = sorted(
            ((entry, entry.score(query)) for entry in self.entries),
            key=lambda pair: pair[1], reverse=True,
        )
        hits = [(entry, score) for entry, score in scored if score > 0]
        if not hits:
            return Decision("no_owner", query, touched=[])
        top = hits[0][1]
        contenders = [(e, s) for e, s in hits if top - s <= margin]
        if len(contenders) > 1:
            return Decision("ambiguous", query, touched=contenders)
        return Decision("routed", query, corpus=hits[0][0], touched=hits[:1])

    def drift(self) -> list[str]:
        """FM-S6. Registered roots that are missing or no longer validate."""
        problems = []
        for entry in self.entries:
            if not entry.root.is_dir():
                problems.append(f"{entry.corpus_id}: root {entry.root} does not exist")
                continue
            if not (entry.root / "index.html").is_file():
                problems.append(f"{entry.corpus_id}: root has no index.html")
        return problems


def _meta_of(path: Path, name: str) -> str:
    """Read one mplpb meta value straight from a file."""
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    match = re.search(
        rf'<meta\s+name="mplpb:{name}"\s+content="([^"]*)"', source, re.I)
    return match.group(1).strip() if match else ""
