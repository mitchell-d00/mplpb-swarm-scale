#!/usr/bin/env python3
"""Pre-registration for ablation run v2.

Written and hashed BEFORE the harness was run. v1's pre-registration is
preserved at ablation/v1/ and its design error is recorded in
MPLPB-TEST-014 §5a: the stripped arm scored 100% on both non-circular
classes, so the harness had no headroom to detect structure helping and
could only ever detect it hurting. A ceiling on the control arm is a broken
instrument, not a finding.

v2 adds three probe classes that neither arm can pass by naming the page,
and one pre-registered validity check that voids the run if the ceiling
recurs.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import generate_corpus as corpus

OUT = Path(__file__).resolve().parents[2] / "ablation" / "v2" / "probes.json"

STOP = {"a", "an", "and", "are", "as", "at", "be", "by", "do", "for", "from",
        "how", "i", "in", "is", "it", "of", "on", "or", "that", "the", "this",
        "to", "we", "what", "when", "where", "which", "who", "with", "you",
        "need", "your", "our", "not", "can", "has", "have", "was", "were"}


def content(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9-]+", text.lower())
            if w not in STOP and len(w) > 2]


PREDICTIONS = [
    "P0  VALIDITY CHECK, pre-registered. If the stripped arm again scores "
    "100% on any tier-1 class, the instrument still has no headroom on that "
    "class and the class is void for this run. v1 failed exactly here and the "
    "failure was only noticed after reporting.",

    "P1  Lookup will be near parity. Both arms hold identical body prose and "
    "the query is drawn from it. This class exists as a baseline and to make "
    "P0 checkable, not to discriminate.",

    "P2  Paraphrase is the class the whole claim rests on. Queries are drawn "
    "from trigger vocabulary, which the structured arm indexes as "
    "when_to_use and the stripped arm does not hold at all. If structure "
    "does not win here it does not win anywhere, and the correct conclusion "
    "would be that declared scope is decoration for retrieval purposes.",

    "P3  Discriminate: the near-duplicate twins share all body vocabulary and "
    "differ only in trigger. The stripped arm should sit near chance, around "
    "50%. A stripped arm scoring well above chance would mean the twins are "
    "separable from prose alone and the class is badly built.",

    "P4  Refusal may still favour the stripped arm. Declared scope and "
    "trigger text are additional indexable surface and therefore additional "
    "false-positive surface under an any-term fallback. Two mitigations are "
    "run as declared variants: excluding navigation categories (FM-L12) and "
    "excluding metadata fields from the broad fallback pass.",

    "P5  CONFOUND, to be measured not argued. The same author wrote the "
    "trigger conditions and the probes, so a paraphrase win may be authorial "
    "artifact. The harness reports median probe-to-trigger and probe-to-body "
    "overlap. If probe-to-trigger overlap exceeds 0.5, the P2 result is "
    "substantially planted and must be discounted in the ledger rather than "
    "reported as a structural finding.",
]


def probe_query(trigger: str, take: int = 2) -> str:
    """Build a probe from a trigger mechanically: take the first `take`
    content words and add a fixed question frame. Deterministic, so the
    probe cannot be hand-tuned to the target after seeing results."""
    words = content(trigger)[:take]
    return "how do I " + " ".join(words)


def build() -> list[dict]:
    probes: list[dict] = []

    for spoke, cfg in corpus.SPOKES.items():
        prefix, body_v, ask_v = cfg["prefix"], cfg["body"], cfg["ask"]

        # lookup — body vocabulary, easy baseline
        for n in (2, 5, 9):
            probes.append({
                "id": f"lookup-{spoke}-{n}", "kind": "lookup", "tier": 1,
                "query": f"{body_v[n - 1]} step in {spoke}",
                "expect_doc": f"{prefix}-{n:03d}", "expect_answer": True,
            })

        # paraphrase — trigger vocabulary, the class the claim rests on
        for n in (2, 5, 8, 9):
            probes.append({
                "id": f"paraphrase-{spoke}-{n}", "kind": "paraphrase", "tier": 1,
                "query": probe_query(ask_v[n - 1]),
                "expect_doc": f"{prefix}-{n:03d}", "expect_answer": True,
                "trigger_text": ask_v[n - 1], "body_text": body_v[n - 1],
            })

        # discriminate — near-duplicate twins, separable only by trigger
        probes.append({
            "id": f"discriminate-{spoke}-twin", "kind": "discriminate", "tier": 1,
            "query": probe_query(ask_v[9]),
            "expect_doc": f"{prefix}-011", "forbid_doc": f"{prefix}-001",
            "expect_answer": True, "trigger_text": ask_v[9],
            "body_text": body_v[0],
        })
        probes.append({
            "id": f"discriminate-{spoke}-base", "kind": "discriminate", "tier": 1,
            "query": probe_query(ask_v[0]),
            "expect_doc": f"{prefix}-001", "forbid_doc": f"{prefix}-011",
            "expect_answer": True, "trigger_text": ask_v[0],
            "body_text": body_v[0],
        })

        # tier 2, circular by construction, reported and discounted
        probes.append({
            "id": f"currency-{spoke}", "kind": "currency", "tier": 2,
            "query": f"{body_v[2]} step in {spoke}",
            "expect_doc": f"{prefix}-003",
            "forbid_doc": f"{prefix}-OLD-003", "expect_answer": True,
        })
        probes.append({
            "id": f"supersession-{spoke}", "kind": "supersession", "tier": 2,
            "query": f"{prefix}-OLD-003", "expect_doc": f"{prefix}-003",
            "expect_answer": True,
        })

    for a, b in [("deploy", "retention"), ("incident", "monitoring"),
                 ("access", "procurement")]:
        probes.append({
            "id": f"ambiguity-{a}-{b}", "kind": "ambiguity", "tier": 2,
            "query": f"{corpus.SPOKES[a]['body'][0]} and "
                     f"{corpus.SPOKES[b]['body'][0]} responsibilities",
            "expect_spokes": sorted([a, b]), "expect_answer": True,
        })

    for n, q in enumerate([
        "photosynthesis in coastal mangrove seedlings",
        "tax treatment of employee stock options",
        "seismic retrofit standards for masonry chimneys",
        "dental coverage under the staff benefits plan",
        "migration routes of arctic terns",
        "fermentation temperature for saison yeast",
        "tuning a harpsichord after transport",
        "diagnosing blight in tomato seedlings",
    ], 1):
        probes.append({
            "id": f"refusal-{n}", "kind": "refusal", "tier": 1, "query": q,
            "expect_doc": None, "expect_answer": False,
        })

    return probes


def main() -> int:
    probes = build()
    payload = {
        "document": "Ablation run v2 — MPLPB-TEST-014 v2",
        "note": "NOT MPLPB-SWARM-013 §12.5. Four requirements remain unmet; "
                "see the ledger §1.",
        "supersedes": "ablation/v1/probes.json (ceiling error, ledger §5a)",
        "predictions": PREDICTIONS,
        "probes": probes,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {len(probes)} probes to {OUT}")
    counts: dict[str, int] = {}
    for p in probes:
        counts[p["kind"]] = counts.get(p["kind"], 0) + 1
    for kind in ("lookup", "paraphrase", "discriminate", "refusal",
                 "currency", "supersession", "ambiguity"):
        print(f"  {kind:<14}{counts.get(kind, 0):>3}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
