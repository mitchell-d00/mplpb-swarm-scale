# Swarm MPLPB

Concurrency, federation, provenance depth, and deployment profiles for an
MPLPB local web read and written by more than one actor.

Standard library only — no `pip install`, no server, no network at any
point in execution.

**Paper:** MPLPB-SWARM-013 v3 ·
[md](docs/MPLPB_Swarm_Scale.md) ·
[txt](docs/MPLPB_Swarm_Scale.txt) ·
[pdf](docs/MPLPB_Swarm_Scale.pdf)

The corpus specification is
[MPLPB as a Local Web](https://github.com/mitchell-d00/-The-Local-Mirror-MPLPB-as-a-Self-Contained-Offline-Site)
(MPLPB-LOCAL-008 v4). The single-reader front end is
[Smart Local MPLPB](https://github.com/mitchell-d00/SMART-LOCAL-MPLPB-A-Retrieval-Bounded-Front-End-for-a-Local-Web)
(MPLPB-SMART-011 v1). This replaces neither.

---

## The problem

Those specifications assume one writer. Supersession is described as a
sequence — retire, replace, log — and a sequence has one actor. The loop
that writes a page back into the corpus is a person at a keyboard.

Add writers, add corpora, and add an audience that is not the author, and
three things break that no existing check sees.

**Ordering.** Two actors superseding the same document produce two current
successors. Both validate. The corpus is ambiguous about its own history
and stays that way.

**Provenance.** An actor answers from prior knowledge, teaches the corpus,
and the corpus converts an unsourced assertion into a page with an
identifier, a scope, a status, and accurate provenance. A second actor
retrieves it legitimately. Every structural check passes, because the
structure is impeccable and the problem is in the world.

**Audience.** A research group tolerates a wrong retrieval because someone
would notice. A customer does not notice, and cannot.

---

## What this does about it

| Failure | Mechanism | § |
| --- | --- | --- |
| Identifier collision (FM-S1) | Identifiers allocated under lease, never chosen | 4.1 |
| Supersession fork (FM-S2) | Linearized writes; forks detected after the fact | 4.2 |
| Epistemic laundering (FM-S3) | `origin_depth` counter, ratification gate | 5 |
| Stale-lease write (FM-S4) | Fencing token checked at the write | 4.3 |
| Cross-corpus collision (FM-S5) | Declared-scope precedence, `ambiguous` not merge | 6.3 |
| Registry drift (FM-S6) | The registry is itself a validated corpus | 6.2 |
| Federated provenance loss (FM-S10) | Corpus ID is a field of the hit object | 6.4 |
| Profile drift (FM-S11–S14) | Four declared deployment profiles | 10 |
| Index-as-distractor (FM-L12) | Navigation excluded from content retrieval | 11.4 |

The depth counter is the one that matters. It does not detect laundering —
nothing does, because validation reads structure and the structure is fine.
It counts machine generations, exposes the count in every citation, and
refuses to let the chain run unattended past a threshold. Containment, not
detection, and §5.4 says so.

---

## Install and run

Nothing to install. Clone and run.

```bash
python3 -m mplpb_swarm health site/corpus-a
python3 -m mplpb_swarm depth  site/corpus-a
python3 -m mplpb_swarm forks  site/corpus-a
python3 -m mplpb_swarm cite   site/corpus-a OPS-ROLLBACK-003
python3 -m mplpb_swarm route  site/registry "how do we roll back a deployment"
python3 -m mplpb_swarm profile list
python3 -m mplpb_swarm serve-check helpdesk-external site/corpus-a OPS-ROLLBACK-003
```

For the `mplpb-swarm` entry point: `pip install -e .`

Python 3.9 or newer. The package imports nothing outside the standard
library. `tools/make_paper.py` requires `reportlab` to render the paper as
PDF; that is a documentation dependency, is not imported by the package,
and is not needed to run anything.

Directory names are lowercase and every command above matches the
directories on disk exactly.

---

## What it looks like

```
$ python3 -m mplpb_swarm health site/corpus-a
corpus CORPUS-A
  pages          5 (4 current, 1 retired)
  depth          d0=3, d1=1
  machine share  25%
  forks          0
  OK  no swarm-layer defects
```

```
$ python3 -m mplpb_swarm cite site/corpus-a OPS-ROLLBACK-003
[CORPUS-A · OPS-ROLLBACK-003 · ops/rollback.html · 2026-08-30T00:00Z v1 · local · current · origin=taught d1]
```

Longer than anyone wants, deliberately. A taught note cited as an authored
one reads better than the truth, which is what makes that failure quiet.
There is no shorter form on offer.

```
$ python3 -m mplpb_swarm route site/registry "retention of deployment logs"
ambiguous — more than one corpus declares this:
  CORPUS-A (0.33) — Deployment, rollback, and release operations for the build pipeline
  CORPUS-B (0.33) — Data retention, classification, and records policy
narrow the question, or name a corpus.
```

It stops rather than merging. Two corpora with different owners produce an
answer neither owner is accountable for.

---

## Deployment profiles

The same corpus, read four ways. What changes is how much of the machine's
own writing anybody is willing to stand behind.

```
                       swarm     lab   internal   external
max served depth           1       2          1          0
retired served            no     yes         no         no
teaching                 yes     yes        yes         no
fallback                full    full       full      prose
lease ttl                15s    120s        30s        30s
```

```
$ python3 -m mplpb_swarm serve-check helpdesk-external site/corpus-a OPS-ROLLBACK-003
helpdesk-external: would NOT serve OPS-ROLLBACK-003
  - origin_depth 1 exceeds the profile maximum of 0 (FM-S3)
  - classification '(none)' is not in this profile's served set — note this
    is a filter and not an access control
```

`answer_without_retrieval` is False in every profile and passing `True`
raises. It is an invariant, not a setting.

`max_served_depth: 0` on the external profile is where the provenance
machinery stops being bookkeeping: an organisation can state that no
machine-authored page reaches a customer and have it be checkable.

---

## Experiments

The evidence in §11 is reproducible from this repository.

```bash
python3 tools/ablation/generate_corpus.py    # 79-page structured arm
python3 tools/ablation/probes.py             # regenerate the probe set
sha256sum -c ablation/v2/probes.sha256       # verify the pre-registration
python3 tools/ablation/run_ablation.py       # three variants against stripped
python3 tools/ablation/run_graded.py         # the overlap curve
```

A structured corpus against a stripped copy: prose byte-identical, metadata
and links and navigation removed, flattened, filenames randomized.
Identical ranker. Probes hashed before the run, shuffled, arms interleaved,
scoring mechanical.

Probes are graded by how much of their vocabulary already appears in the
declared field, using neutral words verified absent from the whole corpus:

```
overlap with the declared field      structured    stripped
1.00  (probe quotes the field)            95.8%        0.0%
0.50  (one relevant word in two)          79.2%        0.0%
0.33  (one relevant word in three)        79.2%        0.0%
0.00  (no relevant words)                  0.0%        0.0%
```

At one relevant word in three, declared trigger text finds the right page
79.2% of the time where prose alone finds it 0.0%. Most of that probe is
noise, so it is not the probe quoting the field.

The same run measures the trade behind the `fallback` profile setting:

| | correct refusal | retrieval at 0.33 overlap |
| --- | --- | --- |
| `fallback: full` | 75.0% | 79.2% |
| `fallback: prose` | 100.0% | 0.0% |

Reach and precision are one dial.

Two validity checks are pre-registered alongside the predictions and both
fired: a ceiling check that voids any class where the control arm scores
100%, and a confound check that discounts any result where the probe
vocabulary is already contained in the field under test. Appendix A gives
the full protocol.

**This does not close the ablation.** It is retrieval, not reconstruction;
the corpus is synthetic; the probes were written by the author. §13.5 lists
what a valid run needs, and the highest-value item is one other person and
an afternoon. Until then the correct statement remains that structure has
not been shown to beat storage.

---

## Tests

```bash
python3 -m unittest discover -s tests -t .
```

145 tests, standard library `unittest`, no network. Falsifiers §13.1–§13.4
are executed rather than described: concurrency produces no collisions or
forks, laundering is contained at the threshold, no page outside a crawled
root enters that root's index, and no path serves a page above a profile's
depth limit.

To confirm the no-network claim rather than take it on trust:

```bash
unshare -rn python3 -m unittest discover -s tests -t .
```

---

## Layout

```
docs/            the paper, in md, txt, and pdf
docs/superseded/ three drafts this consolidates, retained not deleted
mplpb_swarm/     crawl, lease, supersede, origin, registry, health, cite, profiles
site/            three demo corpora and their registry
ablation/        pre-registrations, hashes, and results for both runs
tests/           145 tests, standard library, no network
tools/           site builder, paper renderer, ablation harness
```

---

## Licence

MIT for code, CC BY 4.0 for documentation. See `LICENSE`.
