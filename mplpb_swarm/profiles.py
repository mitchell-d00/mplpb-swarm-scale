"""Deployment profiles (MPLPB-DEPLOY-015).

MPLPB-SMART-011 has a mode controller that decides what a front end may
answer. This is the same idea one level out: what a *deployment* may
answer, given who is asking and what happens if it is wrong.

Four profiles ship. They differ on the questions that actually vary
between deployments — whether machine-authored material may be served,
whether the corpus may be taught, which classifications leave the
building, and how the ranker trades reach against precision.

One field does not vary. ``answer_without_retrieval`` is False in every
profile and there is no constructor argument that changes it. A deployment
that wants a mode which improvises is not configuring this package.

The ``fallback`` setting is not a preference. MPLPB-TEST-014 v2 §9
measured the trade directly: a prose-only broad fallback raised correct
refusal from 75% to 100% and dropped paraphrase retrieval from 79% to 0%,
because declared scope and trigger text become reachable only when every
query term matches. Reach and precision are the same dial. Which end a
deployment wants depends on what a wrong answer costs it, and that is
exactly what distinguishes these four.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from mplpb_swarm.page import Page


class ProfileViolation(RuntimeError):
    """Raised when a page may not be served under the running profile."""


@dataclass(frozen=True)
class Profile:
    name: str
    audience: str

    # --- invariant -------------------------------------------------------
    answer_without_retrieval: bool = False

    # --- what may be served ---------------------------------------------
    max_served_depth: int = 1
    serve_retired: bool = False
    serve_classifications: tuple[str, ...] = ("", "internal")

    # --- what may be written --------------------------------------------
    teaching_enabled: bool = True
    depth_threshold: int = 1
    ratification_required: bool = True

    # --- retrieval behaviour --------------------------------------------
    fallback: str = "full"          # "full" = reach, "prose" = precision
    ambiguity_margin: float = 0.15
    drop_navigation: bool = True    # FM-L12

    # --- concurrency -----------------------------------------------------
    lease_ttl: float = 30.0

    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.answer_without_retrieval:
            raise ValueError(
                "answer_without_retrieval is an invariant, not a setting")
        if self.fallback not in ("full", "prose"):
            raise ValueError("fallback must be 'full' or 'prose'")

    # ---------------------------------------------------------------- gate

    def refusals_for(self, page: Page) -> list[str]:
        """Every reason this page may not be served. Empty means servable."""
        reasons = []
        if page.status == "retired" and not self.serve_retired:
            reasons.append("page is retired and this profile does not serve "
                           "retired material by default")
        if page.origin_depth > self.max_served_depth:
            reasons.append(
                f"origin_depth {page.origin_depth} exceeds the profile "
                f"maximum of {self.max_served_depth} (FM-S3)")
        if page.classification not in self.serve_classifications:
            reasons.append(
                f"classification {page.classification or '(none)'!r} is not "
                f"in this profile's served set — note this is a filter and "
                f"not an access control")
        return reasons

    def may_serve(self, page: Page) -> bool:
        return not self.refusals_for(page)

    def guard(self, page: Page) -> Page:
        """Serve the page or raise with every reason it was refused."""
        reasons = self.refusals_for(page)
        if reasons:
            raise ProfileViolation(
                f"{self.name}: cannot serve {page.doc_id or page.path} — "
                + "; ".join(reasons))
        return page

    def may_teach_from(self, sources: list[Page]) -> tuple[bool, str]:
        """Whether a taught write is permitted, and why not if it is not."""
        if not self.teaching_enabled:
            return False, f"{self.name} does not accept taught pages"
        depth = max((s.origin_depth for s in sources), default=0) + 1
        if depth > self.depth_threshold:
            if self.ratification_required:
                return False, (f"depth {depth} exceeds threshold "
                               f"{self.depth_threshold}; ratification required")
            return False, f"depth {depth} exceeds threshold {self.depth_threshold}"
        return True, ""

    def summary(self) -> str:
        return "\n".join([
            f"{self.name} — {self.audience}",
            f"  answers without retrieval   never (invariant)",
            f"  max served origin_depth     {self.max_served_depth}"
            f"{'  (human-authored only)' if self.max_served_depth == 0 else ''}",
            f"  retired pages               "
            f"{'served on request' if self.serve_retired else 'withheld'}",
            f"  classifications served      "
            f"{', '.join(c or '(none)' for c in self.serve_classifications)}",
            f"  teaching                    "
            f"{'enabled' if self.teaching_enabled else 'disabled'}"
            f"{f', threshold {self.depth_threshold}' if self.teaching_enabled else ''}",
            f"  ranker fallback             {self.fallback}"
            f"  ({'reach' if self.fallback == 'full' else 'precision'})",
            f"  lease ttl                   {self.lease_ttl:g}s",
        ] + [f"  note  {n}" for n in self.notes])


SWARM = Profile(
    name="swarm",
    audience="many agents reading and writing one corpus inside one team",
    max_served_depth=1,
    serve_retired=False,
    teaching_enabled=True,
    depth_threshold=1,
    ratification_required=True,
    fallback="full",
    lease_ttl=15.0,
    notes=(
        "Leases are short because agents fail fast and a 30-second lease "
        "held by a dead process is 30 seconds of stalled writes.",
        "Ratification is the bottleneck, not compute. Watch the latency "
        "median for FM-S9 before adding agents.",
    ),
)

LAB = Profile(
    name="lab",
    audience="a research group or department sharing a corpus they also author",
    max_served_depth=2,
    serve_retired=True,
    serve_classifications=("", "internal", "restricted"),
    teaching_enabled=True,
    depth_threshold=2,
    ratification_required=False,
    fallback="full",
    lease_ttl=120.0,
    notes=(
        "Readers are the authors, so a wrong retrieval is caught by someone "
        "who would notice. That is what buys the higher depth threshold.",
        "Retired pages are served because reconstructing what a method used "
        "to say is a normal research question, not a leak.",
        "Long leases suit human-paced editing; a person does not want a lock "
        "expiring mid-paragraph.",
    ),
)

HELPDESK_INTERNAL = Profile(
    name="helpdesk-internal",
    audience="an assistant answering staff from policy and operations corpora",
    max_served_depth=1,
    serve_retired=False,
    serve_classifications=("", "internal"),
    teaching_enabled=True,
    depth_threshold=1,
    ratification_required=True,
    fallback="full",
    lease_ttl=30.0,
    notes=(
        "Reach beats precision here: a staff member who gets an adjacent "
        "page recognises it and rephrases, which is cheap. A staff member "
        "who gets 'not in this corpus' for something that is in the corpus "
        "opens a ticket, which is not.",
        "Teaching stays on because the people asking are the people who "
        "know the answer, and the ticket queue is where corpus gaps surface.",
    ),
)

HELPDESK_EXTERNAL = Profile(
    name="helpdesk-external",
    audience="an assistant answering customers outside the organisation",
    max_served_depth=0,
    serve_retired=False,
    serve_classifications=("public",),
    teaching_enabled=False,
    depth_threshold=0,
    ratification_required=True,
    fallback="prose",
    lease_ttl=30.0,
    notes=(
        "max_served_depth is 0: no machine-authored page reaches a customer. "
        "A taught page is an internal convenience and an external liability, "
        "and the depth field is what makes that distinction enforceable.",
        "Teaching is off. A customer-facing loop that writes back is a "
        "corpus poisoning surface with an unauthenticated input.",
        "Prose fallback, accepting the measured cost to reach "
        "(MPLPB-TEST-014 v2 §9), because a wrong external answer is worse "
        "than a refusal and refusing is a supported outcome.",
        "The classification filter is STILL not an access control. Anything "
        "that must not leave the building needs a boundary beneath this "
        "package, not a field inside it.",
    ),
)

PROFILES = {p.name: p for p in
            (SWARM, LAB, HELPDESK_INTERNAL, HELPDESK_EXTERNAL)}


def get(name: str) -> Profile:
    try:
        return PROFILES[name]
    except KeyError:
        raise KeyError(
            f"unknown profile {name!r}; available: "
            f"{', '.join(sorted(PROFILES))}") from None


__all__ = ["Profile", "ProfileViolation", "PROFILES", "get",
           "SWARM", "LAB", "HELPDESK_INTERNAL", "HELPDESK_EXTERNAL"]
