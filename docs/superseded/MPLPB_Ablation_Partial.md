Category: Test / Trial Ledger
Subcategory: Knowledge Infrastructure / Ablation
Document ID: MPLPB-TEST-014
Last Updated: 2026-08-30T15:10Z v2
Owner: Mitchell D. McPhetridge, Independent Researcher
Status: current
Supersedes: MPLPB-TEST-014 v1 (2026-08-30T14:30Z)

---

# A Partial Ablation

### Two Runs, One Broken Instrument, and What the Second One Measured

Mitchell D. McPhetridge
Independent Researcher

---

| Field | Value |
| --- | --- |
| Document ID | MPLPB-TEST-014 |
| Category | Test / Trial Ledger |
| Updated | 2026-08-30T15:10Z v2 |
| Owner | Mitchell D. McPhetridge, Independent Researcher |
| Status | current |
| Scope | Two runs of the mechanical half of the ablation named open in MPLPB-LOCAL-008 §14 Test 4, MPLPB-COST-012 §12.2, and MPLPB-SWARM-013 §12.5; the design error that invalidated the first; what the second measured and what it still cannot; the retrieval trade-off it uncovered |
| When to use | Assessing what the ablation has and has not established; designing a valid run; before citing any MPLPB paper as though the ablation had been closed |
| Supersedes | MPLPB-TEST-014 v1 (2026-08-30T14:30Z) |

**Related.** MPLPB as a Local Web (MPLPB-LOCAL-008 v4) §14 Test 4 — the original statement of the test. MPLPB and the Cost of Visibility (MPLPB-COST-012 v2) §12.2 and §4.1 — the restatement and the pre-registration discipline. MPLPB at Swarm and Enterprise Scale (MPLPB-SWARM-013 v1.2) §12.5. Deployment Profiles (MPLPB-DEPLOY-015 v1) §5 — where the §9 trade-off becomes a configuration decision.

**Back to.** Main Index > Test / Trial Ledger Sub-Index

---

## 1. This Is Still Not the Ablation

The test is stated the same way in three documents: duplicate the corpus, strip metadata, indexes, and typed links, flatten and randomize it, then score both copies on the same probe set in randomized order with a blind scorer.

Four requirements remain unmet across both runs.

**No blind scorer.** Corpus, probes, expected answers, and scoring code were written by the same author. MPLPB-COST-012 §4.1 is explicit that evidence class is set by who selected the query and who scored the result. This is the weakest class available and no number of probes changes it.

**No naive probe author.** MPLPB-COST-012 §12.3 requires probes written by somebody who has not read the corpus. These were written by somebody who had just generated it.

**Retrieval only, not reconstruction.** The test asks whether *the framework's rules and relationships come back intact* — a reasoner reconstructing from retrieved material. Both runs score retrieval: which document came back, at what rank, with what declared status. A corpus could retrieve identically under both arms and reconstruct differently, and nothing here would see it.

**Synthetic corpus.** Seventy-nine generated pages, not the real corpus.

Neither run closes §12.5. What follows is a record of one instrument being built badly, rebuilt, and then producing a result that is real but narrower than it looks.

---

## 2. Run v1 and Its Design Error

v1 ran 42 pre-registered probes (`ablation/v1/`, sha256 `13c7655…`) and reported a negative result: on the two non-circular classes the structured corpus scored 87.5% against the stripped corpus's 100%.

That result is withdrawn as uninterpretable. The reason is recorded here rather than quietly corrected.

**The control arm was at its ceiling.** The stripped corpus scored 100% on both content and refusal. An instrument whose control cannot score higher can only ever detect the treatment being *worse*. It has no power to detect the treatment being better, and reporting a negative from it is close to meaningless — the negative was baked into the design.

The cause was the probe construction. Every content probe queried a page using that page's own distinctive seed term, which the body prose repeated. Lookup was therefore trivial for any lexical index over the prose, and the prose was identical in both arms.

**A second and larger error sat underneath it.** The v1 corpus carried no `mplpb:when_to_use` field. Trigger conditions are the first thing MPLPB-COST-012 §2.1 names under *locate relevant material for a query*, and the entire structure-helps-retrieval claim rests on declared text written in the language of the question rather than the language of the document. v1 stripped a corpus that did not have the mechanism, and then reported that stripping it changed little. That is not a test of the claim.

The v1 pre-registration, results, and manifest are retained under `ablation/v1/` and remain hash-verifiable. A ledger that deletes its superseded runs is a claim, not a record.

---

## 3. What v2 Changed

**Corpus.** Pages carry `mplpb:when_to_use`. Body vocabulary and trigger vocabulary are disjoint by construction — a practitioner's word for a thing and a newcomer's description of the situation share no terms. Each spoke carries a deliberate near-duplicate pair separable only by trigger.

**Probes.** 77 probes in seven classes (`ablation/v2/probes.json`, sha256 `9f9ea6e3…`, frozen 14:38Z). Three new non-circular classes: *paraphrase*, drawn from trigger vocabulary; *discriminate*, on the near-duplicate twins; and a widened *refusal* set.

**Two pre-registered self-checks**, both of which fired:

> **P0** If the stripped arm again scores 100% on any tier-1 class, that class has no headroom and is void for this run.

> **P5** The same author wrote the triggers and the probes. The harness reports median probe-to-trigger overlap. Above 0.5 the paraphrase result is substantially planted and must be discounted rather than reported as structural.

**Three declared retrieval variants** on the structured arm: A as-is; B excluding navigation pages, the FM-L12 mitigation proposed in v1 §8; C which adds a prose-only broad fallback, the second mitigation proposed in v1 §8.

---

## 4. Run v2 Result

```
class                   A         B         C  stripped
-------------------------------------------------------
lookup             100.0%    100.0%    100.0%    100.0%
paraphrase          95.8%     95.8%     95.8%      0.0%
discriminate        66.7%     75.0%     75.0%      0.0%
refusal             75.0%     75.0%    100.0%    100.0%
-------------------------------------------------------
currency           100.0%    100.0%    100.0%      0.0%   circular
supersession       100.0%    100.0%    100.0%      0.0%   circular
ambiguity          100.0%    100.0%    100.0%      0.0%   circular

tier 1 (non-circular)  88.7%   90.3%    93.5%     41.9%
```

**P0 fired on two classes.** The stripped arm scored 100% on *lookup* and 100% on *refusal*. Both are void for this run — no headroom, same defect as v1, now caught by the check rather than after publication.

**P5 fired at maximum.** Median probe-to-trigger overlap was **1.00**; median probe-to-prose overlap was 0.00. The probe's content words were wholly contained in the field being tested, because `probe_query` takes the trigger's own first words. The 95.8% against 0.0% on paraphrase is therefore a keyword-presence test, not a paraphrase test, and under the pre-registration it is discounted.

After both checks, v2's headline result is: **paraphrase and discriminate had headroom, and both were confounded.** The run needed a third stage to be worth anything.

---

## 5. Run v3: Grading the Confound

If the paraphrase win is planted vocabulary, it should vanish the moment the probe stops quoting the field. If some of it is structural, it should survive dilution.

Probes were regenerated at four controlled overlap levels, mixing trigger words with a NEUTRAL vocabulary verified absent from every body, scope, and trigger in the corpus:

```
overlap              B           C    stripped
----------------------------------------------
1.00             95.8%       95.8%        0.0%
0.50             79.2%        0.0%        0.0%
0.33             79.2%        0.0%        0.0%
0.00              0.0%        0.0%        0.0%
```

The floor check passed: at zero overlap every arm scored 0.0%, so the neutral vocabulary did not leak.

**Under variant B the advantage survives dilution.** At overlap 0.33 the probe carries one trigger word and two words that appear nowhere in the corpus, and the structured arm still returns the correct page 79.2% of the time while the stripped arm returns it 0.0% of the time. That is not purely the probe quoting the field — most of the probe is noise. It is declared text making a page reachable by vocabulary that does not appear in the page's prose, which is the mechanism MPLPB-COST-012 §2.1 asserts.

**The residual confound is not removed and cannot be, by this author.** The trigger vocabulary is mine and the probe vocabulary is mine, so what the experiment shows is that a page is findable by *the words I predicted a user would use*. Whether real users use those words is a separate question that only a non-author probe writer can answer. The effect is no longer tautological; it is not yet evidence about users.

---

## 6. What Variant C Revealed

Variant C collapses to 0.0% the moment overlap drops below 1.00.

C was my own proposed mitigation from v1 §8 — *the any-term fallback should not draw on metadata fields* — offered to fix the refusal over-match where a query matched a declared scope rather than a page. It does fix that: refusal rises from 75% to 100%.

It also destroys the entire paraphrase capability. Under a prose-only fallback, declared scope and trigger text are reachable only through the all-terms pass, which means one unfamiliar word anywhere in a user's question makes the whole declared surface unreachable.

**Reach and precision are the same dial.** Measured:

| | refusal | paraphrase at 0.33 overlap |
| --- | --- | --- |
| full fallback (B) | 75.0% | 79.2% |
| prose fallback (C) | 100.0% | 0.0% |

The v1 recommendation was wrong, and wrong in the expensive direction — it would have silently removed the thing the metadata is for while appearing to improve precision. It is withdrawn as a general recommendation and re-issued as a per-deployment setting in MPLPB-DEPLOY-015 §5, where the question becomes what a wrong answer costs that particular deployment.

This is the most useful thing either run produced, and neither run was designed to find it.

---

## 7. What FM-L12 Held Up

The v1 finding on navigation pages survives v2 and is unaffected by the confound.

Sub-index pages outrank the operational pages they list, because a Sub-Index aggregates the vocabulary of everything beneath it plus its own declared scope. Excluding navigation categories raised *discriminate* from 66.7% to 75.0% and cost nothing anywhere. The index was competing with what it indexed.

This is registered as proposed FM-L12 for MPLPB-LOCAL-008 and is now the default in every deployment profile:

> **FM-L12 — Index-as-distractor.** A Sub-Index outranks the operational pages it lists, because it aggregates their vocabulary and its own declared scope. *Detection:* score a probe set for content and check whether navigation pages appear at rank 1. *Mitigation:* exclude declared navigation categories from content retrieval; the category field needed to do this is already required.

---

## 8. What This Establishes

It does not establish:

- that the ablation has been run — §1, four requirements still unmet;
- that structure beats storage on a real corpus, with naive probes and a blind scorer;
- anything about reconstruction, which is the half §12.5 was written about;
- that real users phrase questions the way this corpus's trigger conditions do — §5, residual confound;
- that the §2.1 capability set is worth its cost. Tier 2 remains circular and says nothing either way.

It does establish, at the weakest evidence class and on one synthetic corpus:

- that declared trigger text makes pages retrievable by query vocabulary absent from their prose, with the advantage surviving dilution to one relevant word in three (79.2% against 0.0%);
- that this advantage is entirely contingent on the broad fallback reaching metadata, and disappears completely without it;
- that reach and refusal precision trade against each other on a single measurable dial, and that the trade is large — 25 points of refusal against 79 points of paraphrase;
- that navigation pages are retrieval distractors and excluding them costs nothing;
- that a control arm at ceiling produced a publishable-looking negative result in v1 that meant nothing, which is an argument for pre-registering validity checks and not only predictions.

---

## 9. What a Valid Run Needs

Named so that somebody can do it rather than admire the problem.

1. **A probe author who has not read the corpus.** This removes P5 entirely and is the single highest-value change. It requires one other person and an afternoon.
2. **A real corpus.** Templated prose is more regular than real prose and the direction of that bias is unknown.
3. **A blind scorer**, or mechanical scoring against answers fixed before the run — the second is what both runs did and it is the cheaper half of the requirement.
4. **A reconstruction stage.** Hand both arms' retrieved material to a reasoner and score whether the rules come back intact, blended, inverted, or invented, using the four-category scheme in MPLPB-COST-012 §4. This is the actual test and neither run touches it.
5. **A semantic retriever as a second condition.** Under a lexical index, overlap is effectively binary and the author's vocabulary choice determines the outcome. A semantic index would make paraphrase distance continuous and the confound measurable rather than merely acknowledged.

The harness for 1 through 3 is published and takes a seed. Items 4 and 5 need work that does not exist yet.

---

## 10. How to Re-run

```bash
python3 tools/ablation/generate_corpus.py    # 79-page structured arm
python3 tools/ablation/probes.py             # regenerate the probe set
sha256sum -c ablation/v2/probes.sha256       # verify the pre-registration
python3 tools/ablation/run_ablation.py       # three variants against stripped
python3 tools/ablation/run_graded.py         # the overlap curve
```

Deterministic under seed 20260830, no network. `unshare -rn` in front of either run command confirms that.

Editing the probe set invalidates the hash, which is the point. A run whose probes were changed after the results were seen is not pre-registered, and the hash makes that visible to somebody who was not in the room.

---

## Philosophical Note

v1 produced a clean negative result from an instrument that could not have produced a positive one.

It was pre-registered, it was reported honestly, the arithmetic was right, and it meant nothing. The checks that caught it were added afterwards, by someone rereading their own numbers and noticing that the control had nowhere to go.

Predictions are not enough. Pre-register the conditions under which the instrument is broken, and check those first.

— MDM

---

## Source note

Corpus generators, probe builders, harnesses, and results are under `tools/ablation/` and `ablation/`. Run v1 is retained at `ablation/v1/` with its original hash and remains verifiable; it is superseded, not deleted. Run v2 and the graded run are at `ablation/v2/`.

Both synthetic corpora were generated under seed 20260830 and are not the public MPLPB corpus. No result here transfers to that corpus without being re-run against it.

**Back to.** Main Index > Test / Trial Ledger Sub-Index
