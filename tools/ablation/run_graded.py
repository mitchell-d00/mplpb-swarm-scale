#!/usr/bin/env python3
"""Run v3: graded overlap.

v2 produced a structured win on paraphrase (95.8% against 0.0%) and its own
pre-registered confound check reported median probe-to-trigger overlap of
1.00 — the probe's content words were wholly contained in the field being
tested. That is a keyword-presence test wearing a paraphrase costume, and
P5 requires it be discounted rather than reported.

v3 asks the question the confound made unanswerable: how much of the
structured advantage survives when the probe stops quoting the field?

Probes are generated at four controlled overlap levels by mixing trigger
vocabulary with NEUTRAL vocabulary that appears in no page body, no scope,
and no trigger anywhere in the corpus:

    1.00   two trigger words
    0.50   one trigger word, one neutral
    0.33   one trigger word, two neutral
    0.00   two neutral words          (floor check: both arms must score 0)

If the structured arm degrades smoothly as overlap falls, some of its
advantage is structural. If it holds flat until overlap reaches zero and
then collapses, the advantage is lexical presence and nothing else.

Pre-registered prediction, written before running:

    Q1  The curve will be a STEP, not a slope. FTS5 is lexical and the
        ranker falls back from all-terms to any-term, so any nonzero
        overlap is sufficient for a match and zero overlap is impossible.
        If that is what comes back, the conclusion is about the TEST and
        not about the corpus: §12.5 cannot be run as a retrieval
        experiment by a single author with a lexical index, because the
        author's vocabulary choices determine the result entirely.

    Q2  The floor check must return 0.0% for BOTH arms. Anything else means
        the neutral vocabulary leaked into the corpus and v3 is void.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import generate_corpus as corpus  # noqa: E402
from run_ablation import (  # noqa: E402
    ROOT, SEED, build, load_stripped, load_structured, search, strip_arm, terms,
)

# Words appearing in no body, no scope, and no trigger anywhere in the corpus.
NEUTRAL = ["lantern", "orchard", "basalt", "trombone", "quilt", "meridian",
           "walnut", "cistern", "plover", "gantry", "sorrel", "kiln"]

LEVELS = [("1.00", 2, 0), ("0.50", 1, 1), ("0.33", 1, 2), ("0.00", 0, 2)]


def graded_probes() -> list[dict]:
    rng = random.Random(SEED)
    probes = []
    for spoke, cfg in corpus.SPOKES.items():
        prefix, ask_v = cfg["prefix"], cfg["ask"]
        for n in (2, 5, 8, 9):
            trigger_words = terms(ask_v[n - 1])
            for label, n_trig, n_neut in LEVELS:
                words = (trigger_words[:n_trig]
                         + rng.sample(NEUTRAL, k=n_neut))
                probes.append({
                    "id": f"graded-{spoke}-{n}-{label}",
                    "level": label,
                    "query": "how do I " + " ".join(words),
                    "expect_doc": f"{prefix}-{n:03d}",
                })
    return probes


def leak_check(docs) -> list[str]:
    """Q2 precondition: neutral vocabulary must appear nowhere in the corpus."""
    corpus_text = " ".join(d.indexed().lower() for d in docs)
    return [w for w in NEUTRAL if w in corpus_text]


def main() -> int:
    mapping = strip_arm()
    structured_docs, stripped_docs = load_structured(), load_stripped()

    leaked = leak_check(structured_docs)
    if leaked:
        print(f"VOID — neutral vocabulary leaked into the corpus: {leaked}")
        return 1
    print(f"neutral vocabulary clean ({len(NEUTRAL)} words, none in corpus)\n")

    # Both structured fallback variants are run, because v2's proposed
    # mitigation turned out to be the dominant term. See the ledger §9.
    live = [d for d in structured_docs if not d.is_nav]
    arms = {
        "B: full fallback": build(live, prose_fallback=False),
        "C: prose fallback": build(live, prose_fallback=True),
        "stripped": build(stripped_docs, prose_fallback=False),
    }

    probes = graded_probes()
    rng = random.Random(SEED)
    schedule = [(p, a) for p in probes for a in arms]
    rng.shuffle(schedule)

    scored: dict[tuple[str, str], list[bool]] = {}
    for probe, arm in schedule:
        hits = search(arms[arm], probe["query"])
        if arm == "stripped":
            ids = [mapping.get(k, "") for k in hits]
        else:
            ids = [arms[arm].by_key[k].doc_id for k in hits]
        ok = bool(ids) and ids[0] == probe["expect_doc"]
        scored.setdefault((probe["level"], arm), []).append(ok)

    names = list(arms)
    header = f"{'overlap':<10}" + "".join(f"{a.split(':')[0]:>12}" for a in names)
    print(header)
    print("-" * len(header))
    curve = {}
    for label, _, _ in LEVELS:
        row = f"{label:<10}"
        for arm in names:
            vals = scored[(label, arm)]
            p = 100 * sum(vals) / len(vals)
            curve.setdefault(arm, []).append(p)
            row += f"{p:>11.1f}%"
        print(row)

    floor_ok = all(curve[a][-1] == 0.0 for a in names)
    print(f"\nQ2 floor check at zero overlap: "
          f"{'PASS — every arm scored 0.0%' if floor_ok else 'VOID'}")

    print("\nQ1 shape, per structured variant:")
    for arm in names:
        if arm == "stripped":
            continue
        top, mid = curve[arm][0], curve[arm][1]
        retained = 100 * mid / top if top else 0.0
        shape = "CLIFF" if retained < 20 else ("STEP" if retained > 90 else "SLOPE")
        print(f"  {arm:<20}{top:.1f}% -> {mid:.1f}% at half overlap "
              f"({retained:.0f}% retained)  {shape}")

    print("\n  A CLIFF means the advantage was lexical presence of the "
          "author's own\n  words and nothing more. Retention at reduced "
          "overlap means declared\n  text is reachable by query vocabulary "
          "absent from the page body,\n  which is the mechanism "
          "MPLPB-COST-012 §2.1 claims. Neither reading\n  removes the "
          "residual confound: the author chose the vocabulary.")

    (ROOT / "results_graded.json").write_text(json.dumps(
        {"levels": [l for l, _, _ in LEVELS], "curve": curve,
         "floor_ok": floor_ok, "neutral_words": NEUTRAL}, indent=2,
        sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
