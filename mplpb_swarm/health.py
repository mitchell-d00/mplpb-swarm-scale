"""Corpus health as a measured quantity (MPLPB-SWARM-013 8).

At one author's scale, corpus condition is assessed by looking. At swarm
scale nobody looks, so the condition has to be a number or it is nothing.

Thresholds are deliberately absent. A tolerable ambiguity rate depends on
how finely a deployment has drawn its spokes, and a number invented at
specification time would carry an authority the corpus has not earned.
What is supplied is the measurement.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from pathlib import Path

from mplpb_swarm.crawl import SUPERSEDED_DIR, CrawlResult
from mplpb_swarm.origin import DEFAULT_THRESHOLD, DepthReport, depth_report
from mplpb_swarm.supersede import Fork, find_forks


@dataclass
class Health:
    corpus: str
    pages: int
    current: int
    retired: int
    forks: list[Fork] = field(default_factory=list)
    depth: DepthReport | None = None
    retired_on_disk: int = 0
    ambiguity_rate: float | None = None
    maintenance_rate: float | None = None
    ratification_latencies: list[float] = field(default_factory=list)

    @property
    def retired_mismatch(self) -> int:
        """FM-L11 / FM-S8 input: indexed retired records versus files on disk.

        A corpus missing its own history still validates, still crawls, and
        still answers current questions correctly. This is the only check
        that sees it.
        """
        return self.retired_on_disk - self.retired

    @property
    def ratification_median(self) -> float | None:
        """FM-S9. Latency is a proxy for attention and a poor one; it is
        used because it is observable and quality is not."""
        if not self.ratification_latencies:
            return None
        return statistics.median(self.ratification_latencies)

    def problems(self) -> list[str]:
        out = []
        if self.forks:
            out.append(f"{len(self.forks)} supersession fork(s) (FM-S2)")
            out.extend(f"  {fork}" for fork in self.forks)
        if self.retired_mismatch:
            out.append(
                f"retired mismatch: {self.retired} indexed against "
                f"{self.retired_on_disk} on disk (FM-L11)")
        if self.depth and self.depth.malformed:
            out.append("malformed provenance on: "
                       + ", ".join(self.depth.malformed))
        if self.depth and self.depth.unratified_beyond:
            out.append(
                f"{self.depth.unratified_beyond} page(s) above the depth "
                f"threshold without ratification (FM-S3)")
        return out

    def report(self) -> str:
        lines = [f"corpus {self.corpus or '(unnamed)'}",
                 f"  pages          {self.pages} "
                 f"({self.current} current, {self.retired} retired)"]
        if self.depth:
            hist = ", ".join(f"d{d}={n}" for d, n in self.depth.histogram.items())
            lines.append(f"  depth          {hist or 'none'}")
            lines.append(f"  machine share  {self.depth.machine_fraction:.0%}")
        lines.append(f"  forks          {len(self.forks)}")
        if self.ambiguity_rate is not None:
            lines.append(f"  ambiguity      {self.ambiguity_rate:.0%}")
        if self.maintenance_rate is not None:
            lines.append(f"  writes/read    {self.maintenance_rate:.3f}")
        if self.ratification_median is not None:
            lines.append(f"  ratify median  {self.ratification_median:.1f}s")
        problems = self.problems()
        lines.append("  OK  no swarm-layer defects" if not problems else "")
        lines.extend(f"  !!  {p}" for p in problems)
        return "\n".join(line for line in lines if line)


def measure(result: CrawlResult, root: Path, corpus: str = "",
            threshold: int = DEFAULT_THRESHOLD,
            reads: int = 0, writes: int = 0,
            ratification_latencies: list[float] | None = None) -> Health:
    """Compute the five quantities of section 8 from crawl records."""
    retired_dir = Path(root) / SUPERSEDED_DIR
    on_disk = len(list(retired_dir.rglob("*.html"))) if retired_dir.is_dir() else 0
    retired = sum(1 for p in result.pages if p.status == "retired")

    return Health(
        corpus=corpus,
        pages=len(result.pages),
        current=len(result.current()),
        retired=retired,
        forks=find_forks(result.pages),
        depth=depth_report(result.pages, threshold=threshold),
        retired_on_disk=on_disk,
        maintenance_rate=(writes / reads) if reads else None,
        ratification_latencies=list(ratification_latencies or []),
    )


def ambiguity_rate(decisions: list) -> float:
    """Routing decisions returning ambiguous over total. Section 8, row 1."""
    if not decisions:
        return 0.0
    return sum(1 for d in decisions if d.kind == "ambiguous") / len(decisions)
