"""Citation format (MPLPB-SWARM-013 6.4).

The citation is built from the hit object's own fields. There is no code
path that renders a page reference by assembling a string from parts, which
is how the corpus identifier gets dropped and a foreign page starts
reading as a local one (FM-S10, and FM-L10 one level down).

The format is longer than anyone wants:

    [CORPUS-B · POL-004 · policy/retention.html · v3 · local · current · origin=human d0]

That is deliberate. A taught note cited as an authored one reads better
than the truth, which is exactly what makes that failure quiet. There is
no shorter form on offer.
"""

from __future__ import annotations

from mplpb_swarm.page import Page

SEP = " \u00b7 "


def cite(page: Page) -> str:
    """Full provenance for one page. Every field is required."""
    parts = []
    if page.corpus:
        parts.append(page.corpus)
    parts.append(page.doc_id or "UNIDENTIFIED")
    parts.append(page.path)
    if page.version:
        parts.append(page.version)
    parts.append(page.substrate)
    parts.append(page.status)
    parts.append(f"origin={page.origin} d{page.origin_depth}")
    if page.ratified_by:
        parts.append(f"ratified={page.ratified_by}")
    return "[" + SEP.join(parts) + "]"


def audit(citation: str) -> list[str]:
    """Report what a citation string is missing.

    Used by tests and by anyone checking a render path they did not write.
    """
    missing = []
    if not (citation.startswith("[") and citation.endswith("]")):
        missing.append("not a citation")
        return missing
    body = citation[1:-1].split(SEP)
    if not any(part.startswith("origin=") for part in body):
        missing.append("origin/depth")
    if not any(part in ("local", "public") for part in body):
        missing.append("substrate")
    if not any(part in ("current", "retired", "draft") for part in body):
        missing.append("status")
    return missing
