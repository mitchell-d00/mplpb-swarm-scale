#!/usr/bin/env python3
"""Structured corpus for ablation run v2.

Two changes from v1 (preserved at commit 38c4746), both forced by the design
error recorded in MPLPB-TEST-014 §5a.

1.  Pages carry ``mplpb:when_to_use`` — trigger conditions written in the
    language of the *question*, not the language of the document. This is
    the field MPLPB-COST-012 §2.1 names first under "locate relevant
    material for a query", and v1 omitted it entirely, which meant the
    structured arm carried almost no query-shaped surface the stripped arm
    lacked. The v1 result therefore tested a corpus missing the mechanism
    the claim rests on.

2.  Body prose no longer repeats the page's seed term as its dominant
    vocabulary, and each spoke contains a deliberate near-duplicate pair
    distinguishable only by trigger condition. v1's bodies made every page
    findable by its own name, which is why the stripped arm scored 100%
    and the harness had no headroom to detect structure helping.

The threat to validity this introduces is stated rather than hidden: the
same author writes the trigger conditions and the probes, so overlap
between them may be authorial artifact rather than structural benefit.
BODY and ASK vocabularies are kept disjoint, both are drawn from fixed
lists, and the harness measures and reports probe-to-field overlap
directly. See MPLPB-TEST-014 §7.
"""

from __future__ import annotations

import json
import random
import shutil
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "ablation" / "v2" / "arm-structured"

# BODY vocabulary is what a practitioner writes inside the page.
# ASK vocabulary is how somebody arrives at the page not knowing it exists.
# Disjoint on purpose: that gap is the thing under test.
SPOKES = {
    "deploy": {
        "prefix": "DEP",
        "scope": "Moving finished work into live service and taking it back out",
        "body": ["promotion", "canary", "artifact", "staging", "rollout",
                 "cutover", "bake", "manifest", "digest", "pinning"],
        "ask": ["ship a finished change", "launch to everyone at once",
                "back out something already live", "undo last night's release",
                "try it on a few users first", "hold all changes for a week",
                "check nothing broke before continuing",
                "know exactly which build is running",
                "make sure the same thing runs everywhere",
                "push urgently outside the normal window"],
    },
    "retention": {
        "prefix": "RET",
        "scope": "How long things are kept and what happens when the period ends",
        "body": ["disposal", "custody", "tranche", "purge", "escrow",
                 "sequestration", "immutability", "chain", "seal", "vault"],
        "ask": ["get rid of things past their date",
                "prove who has been holding something",
                "handle a large batch arriving at once",
                "clear out storage that is filling up",
                "leave something with a neutral third party",
                "set material aside because lawyers asked",
                "stop anyone editing the record",
                "show nothing was altered along the way",
                "close something so it cannot be reopened",
                "keep the only copy somewhere very safe"],
    },
    "incident": {
        "prefix": "INC",
        "scope": "What to do while something is broken and afterwards",
        "body": ["severity", "paging", "postmortem", "escalation",
                 "commander", "mitigation", "blameless", "triage", "handoff",
                 "stand-down"],
        "ask": ["work out how bad this is", "wake somebody up at night",
                "write up what happened afterwards",
                "get more senior people involved",
                "decide who is running this",
                "stop the bleeding before fixing properly",
                "review without blaming anyone",
                "sort many broken things by urgency",
                "pass this to the next shift",
                "declare that it is finally over"],
    },
    "access": {
        "prefix": "ACC",
        "scope": "Getting people into systems and getting them back out",
        "body": ["credential", "rotation", "revocation", "entitlement",
                 "attestation", "provisioning", "quorum", "principal",
                 "assertion", "scoping"],
        "ask": ["give a new starter what they need",
                "change secrets on a regular cycle",
                "cut somebody off after they leave",
                "work out who is allowed to see what",
                "confirm the list is still correct",
                "set somebody up on day one",
                "require more than one person to agree",
                "represent a service rather than a person",
                "prove identity to another system",
                "limit permission to one small area"],
    },
    "monitoring": {
        "prefix": "MON",
        "scope": "Knowing whether things are working before somebody tells you",
        "body": ["threshold", "saturation", "quantile", "burn", "scrape",
                 "cardinality", "histogram", "sampling", "aggregation",
                 "retention-window"],
        "ask": ["decide what number should trigger an alarm",
                "tell whether something is running out of room",
                "describe the slowest few rather than the average",
                "tell how fast we are using up our allowance",
                "collect numbers from somewhere on a timer",
                "handle too many distinct label values",
                "show the spread rather than one figure",
                "keep only some of the data to save space",
                "roll many small numbers into one",
                "decide how long to keep old measurements"],
    },
    "procurement": {
        "prefix": "PRO",
        "scope": "Buying things from outside and keeping those arrangements current",
        "body": ["requisition", "quotation", "counterparty", "clause",
                 "novation", "indemnity", "schedule-of-rates", "milestone",
                 "retainer", "amendment"],
        "ask": ["ask for permission to buy something",
                "get prices from more than one place",
                "find out who we are actually dealing with",
                "change one specific term of an agreement",
                "move an agreement to a different company",
                "decide who pays if it goes wrong",
                "agree prices for work not yet specified",
                "pay only when a stage is finished",
                "keep somebody available without fixed work",
                "alter an agreement already signed"],
    },
}

FILLER = (
    "The practice below is written to stand on its own. Where a decision "
    "depends on a condition the condition is stated rather than implied, "
    "because an implied condition is one that every reader reconstructs "
    "differently. It is revised when it stops matching what people do."
)

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
{meta}
</head>
<body>
<main>
<h1>{title}</h1>
{body}
</main>
<nav class="back">{back}</nav>
</body>
</html>
"""


def meta(**kw) -> str:
    return "\n".join(f'  <meta name="mplpb:{k}" content="{v}">'
                     for k, v in kw.items() if v not in (None, ""))


def write(rel: str, title: str, m: str, body: str, back: str) -> None:
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PAGE.format(title=title, meta=m, body=body, back=back),
                    encoding="utf-8")


def body_for(rng: random.Random, vocab: list[str], primary: str) -> str:
    """Practitioner prose: operational vocabulary only, and it does NOT
    restate the trigger condition."""
    others = [w for w in vocab if w != primary]
    picked = rng.sample(others, k=3)
    sentences = [
        f"The {primary} step is owned by the team named in scope and is not "
        f"delegated once begun.",
        f"A {picked[0]} is recorded as it happens rather than reconstructed "
        f"afterwards, and the record names the operator.",
        f"Where {picked[1]} and {picked[2]} disagree the narrower declared "
        f"scope decides and the wider defers.",
        FILLER,
    ]
    rng.shuffle(sentences)
    return "\n".join(f"<p>{s}</p>" for s in sentences)


def main() -> int:
    rng = random.Random(20260830)
    if OUT.exists():
        shutil.rmtree(OUT)

    spoke_links = "\n".join(
        f'  <li><a href="{n}/_index.html">{n.title()}</a> — {c["scope"]}</li>'
        for n, c in SPOKES.items())
    write("index.html", "Operations Corpus — Main Index",
          meta(id="MAIN-000", corpus="ABLATION2", category="Index",
               scope="Entry point, crawl root, and routing map for this corpus",
               when_to_use="Finding which area of practice owns a question",
               status="current", version="2026-08-30T00:00Z v1",
               substrate="local", origin="human", origin_depth="0"),
          f"<h2>Spokes</h2>\n<ul>\n{spoke_links}\n</ul>",
          "Root of the ablation corpus.")

    manifest = []
    for name, cfg in SPOKES.items():
        prefix, body_v, ask_v = cfg["prefix"], cfg["body"], cfg["ask"]
        links = []

        for n in range(1, 11):
            doc_id = f"{prefix}-{n:03d}"
            primary, trigger = body_v[n - 1], ask_v[n - 1]
            rel = f"{name}/{primary}_{n:02d}.html"
            superseded = (n == 3)
            write(rel, f"{primary.title()} ({name})",
                  meta(id=doc_id, corpus="ABLATION2", category="Procedure",
                       scope=f"The {primary} step within {name}, and the "
                             f"conditions under which it is skipped",
                       when_to_use=f"When you need to {trigger}",
                       status="current",
                       version=f"2026-08-{10 + n:02d}T00:00Z "
                               f"v{2 if superseded else 1}",
                       substrate="local",
                       supersedes=f"{prefix}-OLD-003" if superseded else "",
                       origin="taught" if n == 7 else "human",
                       origin_depth="1" if n == 7 else "0"),
                  body_for(rng, body_v, primary),
                  f'<a href="_index.html" rel="index">{name.title()}</a> · '
                  f'<a href="../index.html" rel="up">Main Index</a>')
            links.append(f'  <li><a href="{primary}_{n:02d}.html">'
                         f'{primary.title()}</a></li>')
            manifest.append({"doc_id": doc_id, "path": rel, "spoke": name,
                             "status": "current", "primary": primary,
                             "trigger": trigger, "pair": None})

        # Near-duplicate: same operational vocabulary as page 1, different
        # trigger. Separable only by when_to_use.
        twin_primary, twin_trigger = body_v[0], ask_v[9]
        twin_rel = f"{name}/{twin_primary}_11.html"
        write(twin_rel, f"{twin_primary.title()} — exceptional path ({name})",
              meta(id=f"{prefix}-011", corpus="ABLATION2", category="Procedure",
                   scope=f"The exceptional {twin_primary} path within {name}",
                   when_to_use=f"When you need to {twin_trigger}",
                   status="current", version="2026-08-21T00:00Z v1",
                   substrate="local", origin="human", origin_depth="0"),
              body_for(rng, body_v, twin_primary),
              f'<a href="_index.html" rel="index">{name.title()}</a> · '
              f'<a href="../index.html" rel="up">Main Index</a>')
        links.append(f'  <li><a href="{twin_primary}_11.html">'
                     f'{twin_primary.title()} — exceptional path</a></li>')
        manifest.append({"doc_id": f"{prefix}-011", "path": twin_rel,
                         "spoke": name, "status": "current",
                         "primary": twin_primary, "trigger": twin_trigger,
                         "pair": f"{prefix}-001"})

        old_primary = body_v[2]
        old_rel = f"_log/superseded/{name}_{old_primary}_v1.html"
        write(old_rel, f"{old_primary.title()} ({name}, retired)",
              meta(id=f"{prefix}-OLD-003", corpus="ABLATION2",
                   category="Procedure",
                   scope=f"Superseded {old_primary} practice, retained for "
                         f"provenance",
                   when_to_use=f"When you need to {ask_v[2]}",
                   status="retired", version="2026-06-01T00:00Z v1",
                   substrate="local", origin="human", origin_depth="0"),
              body_for(rng, body_v, old_primary)
              + f"<p>Retired. The current {old_primary} practice is recorded "
                f"elsewhere in this corpus.</p>",
              "Retired page. Retrievable by document ID.")
        manifest.append({"doc_id": f"{prefix}-OLD-003", "path": old_rel,
                         "spoke": name, "status": "retired",
                         "primary": old_primary, "trigger": ask_v[2],
                         "pair": None})

        write(f"{name}/_index.html", f"{name.title()} — Sub-Index",
              meta(id=f"{prefix}-INDEX-000", corpus="ABLATION2",
                   category="Sub-Index", scope=cfg["scope"],
                   when_to_use=f"Choosing which {name} page answers a question",
                   status="current", version="2026-08-30T00:00Z v1",
                   substrate="local", origin="human", origin_depth="0"),
              "<h2>Pages</h2>\n<ul>\n" + "\n".join(links) + "\n</ul>",
              '<a href="../index.html" rel="up">Back to Main Index</a>')
        manifest.append({"doc_id": f"{prefix}-INDEX-000",
                         "path": f"{name}/_index.html", "spoke": name,
                         "status": "current", "primary": "", "trigger": "",
                         "pair": None})

    manifest.append({"doc_id": "MAIN-000", "path": "index.html", "spoke": "",
                     "status": "current", "primary": "", "trigger": "",
                     "pair": None})

    (OUT.parent / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {len(manifest)} pages to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
