#!/usr/bin/env python3
"""Ablation harness v2.

Builds the stripped arm from the structured arm, indexes both under an
identical ranker, runs the pre-registered probe set in randomized order
with arms interleaved, scores mechanically, and reports the confound.

Three structured variants are run, all declared in the pre-registration:

    A  as-is                  everything indexed, broad fallback over all
    B  minus navigation       FM-L12 mitigation: indexes orient, not answer
    C  B + prose-only fallback  the any-term pass does not reach metadata

This is NOT MPLPB-SWARM-013 §12.5. Four of its requirements remain unmet
and are listed in MPLPB-TEST-014 §1.

    python3 tools/ablation/run_ablation.py
"""

from __future__ import annotations

import json
import random
import re
import shutil
import sqlite3
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "ablation" / "v2"
STRUCTURED = ROOT / "arm-structured"
STRIPPED = ROOT / "arm-stripped"
SEED = 20260830

STOP = {"a", "an", "and", "are", "as", "at", "be", "by", "do", "for", "from",
        "how", "i", "in", "is", "it", "of", "on", "or", "that", "the", "this",
        "to", "we", "what", "when", "where", "which", "who", "with", "you",
        "need", "your", "our", "not", "can", "has", "have", "was", "were"}

VARIANTS = {
    "A: as-is": {"drop_nav": False, "prose_fallback": False},
    "B: minus navigation": {"drop_nav": True, "prose_fallback": False},
    "C: B + prose fallback": {"drop_nav": True, "prose_fallback": True},
}


def terms(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9-]+", text.lower())
            if w not in STOP and len(w) > 2]


# ------------------------------------------------------------------ stripping

def strip_arm() -> dict[str, str]:
    """Build the stripped arm. Returns filename -> doc_id, for SCORING ONLY.

    Removes every mplpb meta tag, every index page, every anchor and rel
    attribute, and the directory tree. Prose is preserved byte for byte.
    """
    rng = random.Random(SEED)
    if STRIPPED.exists():
        shutil.rmtree(STRIPPED)
    STRIPPED.mkdir(parents=True)

    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    mapping: dict[str, str] = {}
    names = [f"{n:04d}.html" for n in range(1, len(manifest) + 1)]
    rng.shuffle(names)

    for entry in manifest:
        path = entry["path"]
        if path == "index.html" or path.endswith("_index.html"):
            continue
        source = (STRUCTURED / path).read_text(encoding="utf-8")
        source = re.sub(r'\s*<meta name="mplpb:[^>]*>\s*', "\n", source)
        source = re.sub(r"<a\s[^>]*>(.*?)</a>", r"\1", source, flags=re.S | re.I)
        source = re.sub(r'\srel="[^"]*"', "", source)
        source = re.sub(r'<nav class="back">.*?</nav>', "", source, flags=re.S)
        name = names.pop()
        (STRIPPED / name).write_text(source, encoding="utf-8")
        mapping[name] = entry["doc_id"]
    return mapping


# ------------------------------------------------------------------- indexing

@dataclass
class Doc:
    key: str
    doc_id: str = ""
    spoke: str = ""
    status: str = ""
    category: str = ""
    supersedes: str = ""
    prose: str = ""
    meta_text: str = ""

    @property
    def is_nav(self) -> bool:
        return self.category in ("Index", "Sub-Index")

    def indexed(self, prose_only: bool = False) -> str:
        return self.prose if prose_only else f"{self.prose} {self.meta_text}"


def _prose_of(html: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    body = re.sub(r"<meta[^>]*>", " ", body)
    body = re.sub(r"<[^>]+>", " ", body)
    return re.sub(r"\s+", " ", body).strip()


def load_structured() -> list[Doc]:
    docs = []
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest:
        html = (STRUCTURED / entry["path"]).read_text(encoding="utf-8")
        meta = dict(re.findall(
            r'<meta name="mplpb:([^"]+)" content="([^"]*)"', html))
        docs.append(Doc(
            key=entry["path"], doc_id=meta.get("id", ""), spoke=entry["spoke"],
            status=meta.get("status", "current"),
            category=meta.get("category", ""),
            supersedes=meta.get("supersedes", ""),
            prose=_prose_of(html),
            meta_text=" ".join([meta.get("scope", ""),
                                meta.get("when_to_use", ""),
                                meta.get("id", ""), meta.get("supersedes", "")]),
        ))
    return docs


def load_stripped() -> list[Doc]:
    return [Doc(key=f.name, prose=_prose_of(f.read_text(encoding="utf-8")))
            for f in sorted(STRIPPED.glob("*.html"))]


@dataclass
class Index:
    con: sqlite3.Connection
    by_key: dict[str, Doc] = field(default_factory=dict)
    prose_fallback: bool = False


def build(docs: list[Doc], prose_fallback: bool = False) -> Index:
    con = sqlite3.connect(":memory:")
    con.execute("CREATE VIRTUAL TABLE d USING fts5(key, full, prose)")
    con.executemany("INSERT INTO d (key, full, prose) VALUES (?, ?, ?)",
                    [(d.key, d.indexed(), d.prose) for d in docs])
    return Index(con, {d.key: d for d in docs}, prose_fallback)


def search(index: Index, query: str, limit: int = 5) -> list[str]:
    """Narrow before broad. Identical logic for every arm and variant; the
    only knob is whether the broad pass may reach metadata, which is a
    declared variant and not an arm difference."""
    words = terms(query)
    if not words:
        return []
    passes = [("full", " AND "), ("prose" if index.prose_fallback else "full", " OR ")]
    for column, joiner in passes:
        expr = joiner.join(f'"{w}"' for w in words)
        try:
            rows = index.con.execute(
                f"SELECT key FROM d WHERE {column} MATCH ? ORDER BY rank LIMIT ?",
                (expr, limit)).fetchall()
        except sqlite3.OperationalError:
            rows = []
        if rows:
            return [r[0] for r in rows]
    return []


# -------------------------------------------------------------------- scoring

def score(probe: dict, hits: list[str], index: Index, structured: bool,
          mapping: dict[str, str]) -> dict:
    """Mechanical. No judgement is exercised in this function."""

    def ident(key: str) -> str:
        return index.by_key[key].doc_id if structured else mapping.get(key, "")

    ids = [ident(k) for k in hits]
    kind = probe["kind"]
    out = {"probe": probe["id"], "kind": kind, "tier": probe["tier"],
           "hits": len(hits), "top": ids[0] if ids else None}

    if kind == "refusal":
        out["correct"] = not hits
    elif kind in ("lookup", "paraphrase"):
        out["correct"] = bool(ids) and ids[0] == probe["expect_doc"]
        out["at3"] = probe["expect_doc"] in ids[:3]
    elif kind == "discriminate":
        out["correct"] = bool(ids) and ids[0] == probe["expect_doc"]
        out["wrong_twin"] = bool(ids) and ids[0] == probe["forbid_doc"]
    elif kind == "currency":
        live = ids
        if structured:
            live = [ident(k) for k in hits
                    if index.by_key[k].status == "current"]
        out["correct"] = bool(live) and live[0] == probe["expect_doc"]
    elif kind == "supersession":
        if structured:
            succ = [d.doc_id for d in index.by_key.values()
                    if probe["query"] in d.supersedes.split(";")
                    and d.status == "current"]
            out["correct"] = succ == [probe["expect_doc"]]
        else:
            out["correct"] = False
    elif kind == "ambiguity":
        if structured:
            spokes = {index.by_key[k].spoke for k in hits if index.by_key[k].spoke}
            out["correct"] = set(probe["expect_spokes"]).issubset(spokes)
        else:
            out["correct"] = False
    else:
        out["correct"] = False
    return out


def overlap(probe: dict, docs: list[Doc]) -> dict | None:
    """P5 confound. How much of the probe's vocabulary is already in the
    target's trigger, versus in its prose? A high trigger overlap means a
    paraphrase win is planted rather than structural."""
    if "trigger_text" not in probe:
        return None
    q = set(terms(probe["query"]))
    if not q:
        return None
    target = next((d for d in docs if d.doc_id == probe["expect_doc"]), None)
    if target is None:
        return None
    return {
        "probe": probe["id"],
        "trigger": len(q & set(terms(probe["trigger_text"]))) / len(q),
        "prose": len(q & set(terms(target.prose))) / len(q),
    }


def pct(rows: list[dict]) -> float:
    return 100 * sum(bool(r["correct"]) for r in rows) / len(rows) if rows else 0.0


def main() -> int:
    rng = random.Random(SEED)
    probes = json.loads((ROOT / "probes.json").read_text(encoding="utf-8"))["probes"]
    mapping = strip_arm()
    structured_docs, stripped_docs = load_structured(), load_stripped()

    print(f"structured arm: {len(structured_docs)} documents")
    print(f"stripped arm:   {len(stripped_docs)} documents "
          f"({len(structured_docs) - len(stripped_docs)} navigation pages removed)\n")

    arms: dict[str, Index] = {"stripped": build(stripped_docs)}
    for label, cfg in VARIANTS.items():
        docs = [d for d in structured_docs
                if not (cfg["drop_nav"] and d.is_nav)]
        arms[label] = build(docs, prose_fallback=cfg["prose_fallback"])

    schedule = [(p, arm) for p in probes for arm in arms]
    rng.shuffle(schedule)

    results: dict[str, list[dict]] = defaultdict(list)
    for probe, arm in schedule:
        hits = search(arms[arm], probe["query"])
        results[arm].append(
            score(probe, hits, arms[arm], arm != "stripped", mapping))

    (ROOT / "results.json").write_text(
        json.dumps(results, indent=2, sort_keys=True), encoding="utf-8")

    tier1 = ["lookup", "paraphrase", "discriminate", "refusal"]
    tier2 = ["currency", "supersession", "ambiguity"]
    order = list(VARIANTS) + ["stripped"]

    header = f"{'class':<15}" + "".join(f"{a.split(':')[0]:>10}" for a in order)
    print(header)
    print("-" * len(header))
    for kind in tier1 + tier2:
        row = f"{kind:<15}"
        for arm in order:
            rows = [r for r in results[arm] if r["kind"] == kind]
            row += f"{pct(rows):>9.1f}%"
        print(row)
        if kind == "refusal":
            print("-" * len(header) + "   tier 2 below is circular")

    print()
    for label, kinds in (("tier 1 (non-circular)", tier1),
                         ("tier 2 (circular)", tier2)):
        row = f"{label:<25}"
        for arm in order:
            rows = [r for r in results[arm] if r["kind"] in kinds]
            row += f"{pct(rows):>9.1f}%"
        print(row)

    # P0 validity check, pre-registered.
    print("\nP0 validity check (ceiling on the control arm):")
    voided = []
    for kind in tier1:
        rows = [r for r in results["stripped"] if r["kind"] == kind]
        at_ceiling = pct(rows) >= 100.0
        if at_ceiling:
            voided.append(kind)
        print(f"  {kind:<15}stripped {pct(rows):>5.1f}%  "
              f"{'VOID — no headroom' if at_ceiling else 'headroom present'}")
    if voided:
        print(f"  classes voided by P0: {', '.join(voided)}")

    # P5 confound.
    laps = [o for p in probes if (o := overlap(p, structured_docs))]
    if laps:
        print("\nP5 confound (probe vocabulary already present in the target):")
        print(f"  median overlap with trigger text  "
              f"{statistics.median(o['trigger'] for o in laps):.2f}")
        print(f"  median overlap with page prose    "
              f"{statistics.median(o['prose'] for o in laps):.2f}")
        print(f"  n = {len(laps)} paraphrase and discriminate probes")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
