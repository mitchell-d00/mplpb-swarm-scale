"""Provenance class and origin depth (MPLPB-SWARM-013 5).

The failure this addresses is not detectable. An agent answers without
retrieval, teaches the corpus its answer, and the corpus converts an
unsourced assertion into a page with an identifier, a scope, a status, and
correct provenance. A second agent then retrieves it legitimately. Every
structural check passes, because the structure is impeccable and the
problem is in the world.

What is available is to count the generations and refuse to let the count
run unattended past a threshold. That is containment, not detection, and
5.4 says so at length. A human who ratifies without reading defeats it
entirely; see FM-S9 and the latency detector in health.py.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from mplpb_swarm.page import ORIGINS, Page

DEFAULT_THRESHOLD = 1


class RatificationRequired(RuntimeError):
    """Raised when a taught write would exceed the configured depth."""


def depth_for(sources: list[Page]) -> int:
    """Depth of a page taught from these sources: one more than the deepest.

    A page taught from nothing is depth 1, not 0. Depth 0 means a human
    wrote or signed it, and the teaching loop cannot award that to itself.
    """
    if not sources:
        return 1
    return max(s.origin_depth for s in sources) + 1


def check_teachable(sources: list[Page], threshold: int = DEFAULT_THRESHOLD) -> int:
    """Return the depth a taught page would have, or refuse.

    The default threshold of 1 permits teaching from human-authored
    material and refuses teaching from taught material. A deployment that
    raises it has decided to accept that many generations of machine
    authorship between human checks, and the number belongs in the corpus
    where an auditor can see it.
    """
    depth = depth_for(sources)
    if depth > threshold:
        deepest = max(sources, key=lambda s: s.origin_depth) if sources else None
        raise RatificationRequired(
            f"taught page would have origin_depth {depth}, above threshold "
            f"{threshold}"
            + (f"; deepest source {deepest.doc_id} is at depth "
               f"{deepest.origin_depth}" if deepest else "")
            + " — a human must ratify (FM-S3)"
        )
    return depth


def ratify(page: Page, ratifier: str) -> Page:
    """Sign a page: origin human, depth 0, ratifier recorded.

    This is a signature and not a compliment. The corpus records that a
    named person took responsibility; it records nothing about whether
    they read anything.
    """
    if not ratifier.strip():
        raise ValueError("ratification requires a named ratifier")
    page.origin = "human"
    page.origin_depth = 0
    page.ratified_by = ratifier.strip()
    return page


@dataclass(frozen=True)
class DepthReport:
    histogram: dict[int, int]
    max_depth: int
    unratified_beyond: int
    malformed: tuple[str, ...]

    @property
    def machine_fraction(self) -> float:
        total = sum(self.histogram.values())
        if not total:
            return 0.0
        return 1.0 - (self.histogram.get(0, 0) / total)


def depth_report(pages: list[Page],
                 threshold: int = DEFAULT_THRESHOLD) -> DepthReport:
    """The histogram of MPLPB-SWARM-013 8, over current pages."""
    current = [p for p in pages if p.is_current]
    histogram = Counter(p.origin_depth for p in current if p.origin_depth >= 0)
    malformed = tuple(sorted(
        p.doc_id for p in current
        if p.origin_depth < 0 or p.origin not in ORIGINS
    ))
    beyond = sum(
        1 for p in current
        if p.origin_depth > threshold and not p.ratified_by
    )
    return DepthReport(
        histogram=dict(sorted(histogram.items())),
        max_depth=max(histogram) if histogram else 0,
        unratified_beyond=beyond,
        malformed=malformed,
    )


def meta_block(origin: str, depth: int, taught_from: list[str] | None = None,
               ratified_by: str = "") -> str:
    """Render the provenance meta tags for a page being written."""
    if origin not in ORIGINS:
        raise ValueError(f"origin must be one of {ORIGINS}, got {origin!r}")
    lines = [
        f'  <meta name="mplpb:origin" content="{origin}">',
        f'  <meta name="mplpb:origin_depth" content="{depth}">',
    ]
    if taught_from:
        lines.append('  <meta name="mplpb:taught_from" content="'
                     + "; ".join(taught_from) + '">')
    if ratified_by:
        lines.append(f'  <meta name="mplpb:ratified_by" content="{ratified_by}">')
    return "\n".join(lines)


__all__ = [
    "depth_for", "check_teachable", "ratify", "depth_report", "meta_block",
    "DepthReport", "RatificationRequired", "DEFAULT_THRESHOLD",
]
