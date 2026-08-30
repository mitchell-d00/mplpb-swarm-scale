Category: Specification / Architecture
Subcategory: Knowledge Infrastructure / Deployment
Document ID: MPLPB-DEPLOY-015
Last Updated: 2026-08-30T15:20Z v1
Owner: Mitchell D. McPhetridge, Independent Researcher
Status: current
Supersedes: —

---

# Deployment Profiles

### Four Places an MPLPB Corpus Gets Deployed, and What Changes Between Them

Mitchell D. McPhetridge
Independent Researcher

---

| Field | Value |
| --- | --- |
| Document ID | MPLPB-DEPLOY-015 |
| Category | Specification / Architecture |
| Subcategory | Knowledge Infrastructure / Deployment |
| Updated | 2026-08-30T15:20Z v1 |
| Owner | Mitchell D. McPhetridge, Independent Researcher |
| Status | current |
| Scope | What a deployment is permitted to serve and to write, given who is asking and what a wrong answer costs; the four shipped profiles and the reasoning behind each setting; the one field that is not configurable |
| When to use | Deploying MPLPB beyond a single author; choosing settings for an agent swarm, a research group, an internal assistant, or a customer-facing one; deciding what may leave the building |
| Supersedes | — |

**Related.** MPLPB at Swarm and Enterprise Scale (MPLPB-SWARM-013 v1.2) — the concurrency and federation layer these profiles configure. Smart Local MPLPB (MPLPB-SMART-011 v1) §7 — the mode controller this generalises. A Partial Ablation (MPLPB-TEST-014 v2) §6 — the measured trade-off behind the `fallback` setting. MPLPB and the Cost of Visibility (MPLPB-COST-012 v2) §10 — who the architecture is for.

**Back to.** Main Index > Specification / Architecture Sub-Index

---

## Abstract

MPLPB-SMART-011 has a mode controller deciding what a front end may answer. This document is the same idea one level out: what a *deployment* may answer, given who is asking and what happens when it is wrong.

Four profiles ship. They differ on four questions that genuinely vary between deployments — whether machine-authored material may be served, whether the corpus may be taught, which classifications leave the building, and how the ranker trades reach against precision. They agree on one thing that does not vary.

The last of those four is not a preference. MPLPB-TEST-014 v2 §6 measured it: a prose-only broad fallback raises correct refusal from 75% to 100% and drops paraphrase retrieval from 79.2% to 0.0%, because declared scope and trigger text become unreachable the moment a user's question contains one unfamiliar word. Reach and precision are the same dial. Which end a deployment wants is determined by what a wrong answer costs it, and that is precisely what separates a research group from a customer-facing assistant.

---

## 1. The Invariant

`answer_without_retrieval` is False in every profile, and there is no constructor argument that changes it. Passing `True` raises rather than warns.

The asymmetry justifying this is unchanged from MPLPB-SMART-011 §2. A system that occasionally says *I don't have that* is mildly annoying. A system that occasionally invents a confident answer indistinguishable from a retrieved one is corrosive, because after a few undetected instances the provenance on every other answer stops meaning anything.

Scale makes this worse rather than better. At one reader, an improvised answer is one wrong answer. In a deployment where readers teach the corpus, an improvised answer becomes a document — which is the laundering path in MPLPB-SWARM-013 §5, and is why the profiles below spend most of their settings on what may be *written* rather than what may be read.

A deployment that wants a mode which improvises is not configuring this package.

---

## 2. What Varies

| Setting | Question it answers |
| --- | --- |
| `max_served_depth` | How many machine generations may reach this audience |
| `serve_retired` | Is corpus history a normal question here, or a leak |
| `serve_classifications` | What leaves the building |
| `teaching_enabled` | May this audience write to the corpus at all |
| `depth_threshold` | How far may a taught chain run before a human is asked |
| `ratification_required` | Is the human ask enforced or advisory |
| `fallback` | Reach or precision — see §5 |
| `lease_ttl` | Machine-paced writers or human-paced ones |
| `drop_navigation` | FM-L12; on everywhere, kept configurable to be falsifiable |

---

## 3. The Four Profiles

```
                       swarm     lab   internal   external
max served depth           1       2          1          0
retired served            no     yes         no         no
teaching                 yes     yes        yes         no
depth threshold            1       2          1          0
ratification              yes      no        yes        yes
fallback                full    full       full      prose
lease ttl                15s    120s        30s        30s
```

### 3.1 swarm — many agents, one corpus, one team

Leases are short, at fifteen seconds. Agents fail fast and a thirty-second lease held by a dead process is thirty seconds of stalled writes. Humans do not have this problem, which is why the lab profile does the opposite.

Depth threshold is 1 and ratification is enforced. This is the profile where MPLPB-SWARM-013 §9's ceiling bites hardest: the constraint on how many agents can usefully run is not compute, it is how many ratification decisions the human population can make per unit time. Watch the FM-S9 latency median before adding agents. A ratification population with a four-second median is not ratifying.

### 3.2 lab — a research group or department

The loosest profile, and the reasoning is that readers are the authors. A wrong retrieval is caught by somebody who would notice, which is what buys a depth threshold of 2 and ratification being advisory rather than enforced.

Retired pages are served, because *what did this method used to say* is an ordinary research question rather than a disclosure. This is the only profile where corpus history is routinely visible, and it is the profile where losing it would hurt most — a lab that cannot reconstruct its own superseded practice has lost the thing the `_log/superseded/` directory exists for.

Leases run to two minutes because a person does not want a lock expiring mid-paragraph.

This is the constituency MPLPB-COST-012 §10 identified: two to twenty people, a shared corpus, no retrieval engineer, no budget line for one.

### 3.3 helpdesk-internal — an assistant answering staff

Reach beats precision here, and the reasoning is about what each failure costs. A staff member who receives an adjacent page recognises it and rephrases, which costs seconds. A staff member who receives *not in this corpus* for something that is in the corpus opens a ticket, which costs a person. The full fallback is chosen deliberately with §5's refusal cost accepted.

Teaching stays on because the people asking are frequently the people who know the answer, and the ticket queue is where corpus gaps surface first. Depth threshold 1 with ratification enforced: staff may teach from authored material, and a chain of assistants teaching each other stops until somebody signs.

Classification is filtered to public and internal. This filters retrieval; it does not authenticate. See §4.

### 3.4 helpdesk-external — an assistant answering customers

The strictest profile, because a wrong answer leaves the building.

`max_served_depth` is 0. **No machine-authored page reaches a customer.** A taught page is an internal convenience and an external liability, and the depth field is what makes that distinction enforceable rather than aspirational. This is the clearest payoff from the provenance machinery in MPLPB-SWARM-013 §5: without a depth counter there is no mechanical way to state this policy, let alone check it.

Teaching is off entirely. A customer-facing loop that writes back to the corpus is a poisoning surface with an unauthenticated input, and no ratification threshold makes that acceptable.

Only `public` classification is served, and retired pages are withheld.

`fallback` is `prose`, accepting the measured cost in §5. A wrong external answer is worse than a refusal, and refusal is a supported outcome that says what the corpus does cover.

---

## 4. Access Control Is Still Declined

MPLPB-SWARM-013 §7 declines to implement access control and this document does not reverse that. The temptation is strongest exactly here, in the profile that faces customers, which is why it is restated rather than assumed.

`serve_classifications` is a retrieval filter. It is not authentication and it is not authorization. Anything that must not leave the building needs a boundary beneath this package — filesystem permissions, repository access, an identity provider, a network boundary — and those are solved problems that are not improved by being reimplemented in a crawler.

What the corpus layer adds is that the classification travels with the page rather than living in a separate list that drifts from it, and that a served result records which classification was used to decide it was servable, so an audit can reconstruct the decision.

The distinction is not pedantic. A filter that quietly omits a page produces the same user experience as a corpus that lacks it, and an operator who believes the filter is a gate will eventually put something behind it that needed a gate.

---

## 5. The Fallback Setting Is a Measured Trade

Every other setting here is a judgement. This one has numbers.

MPLPB-SMART-011 §4 specifies narrow before broad: require every content term, and fall back to any term only if that returns nothing. The open question was whether the broad pass should reach declared metadata or only page prose.

MPLPB-TEST-014 v2 §6 measured both:

| | correct refusal | paraphrase retrieval at 0.33 overlap |
| --- | --- | --- |
| `fallback: full` | 75.0% | 79.2% |
| `fallback: prose` | 100.0% | 0.0% |

Restricting the fallback to prose gives perfect refusal and removes the entire benefit of declared scope, because under a prose-only fallback the declared surface is reachable only through the all-terms pass — so one unfamiliar word in a user's question makes it unreachable.

An earlier draft of the ablation ledger recommended the prose-only fallback as a general fix for over-matching. That recommendation was wrong in the expensive direction: it would have removed the thing the metadata exists for while appearing to improve precision. It is withdrawn as a default and re-issued here as a per-deployment decision, because it is one.

The decision rule is short. **If a wrong answer is cheap and a missed answer is expensive, take reach. If a wrong answer is expensive and a refusal is acceptable, take precision.** Staff can absorb a wrong answer. Customers cannot.

Both figures come from one synthetic corpus with an author-written probe set and should be treated as a direction, not a constant. §9 of the ledger lists what a run would need to make them trustworthy.

---

## 6. Using a Profile

```python
from mplpb_swarm import profile, crawl

deployment = profile("helpdesk-external")
page = crawl("site/corpus-a").by_id()["OPS-ROLLBACK-003"]

for reason in deployment.refusals_for(page):
    print(reason)
```

```bash
python3 -m mplpb_swarm profile list
python3 -m mplpb_swarm profile helpdesk-external
python3 -m mplpb_swarm serve-check helpdesk-external site/corpus-a OPS-ROLLBACK-003
```

`serve-check` exits non-zero when a page would be refused and prints every reason, not the first one. A gate that stops at the first failure teaches operators to fix one thing at a time and re-run, which is how a page ends up served after three rounds of adjustment that nobody recorded.

---

## 7. Failure Modes

**FM-D1 — Profile drift.** A deployment edits settings until the assistant stops refusing, arriving somewhere no profile describes. *Detection:* record the profile name and its settings hash with each served answer; compare against the shipped profile.

**FM-D2 — Depth policy without depth data.** A profile sets `max_served_depth: 0` over a corpus whose pages never declared `origin`, so every page reads as depth 0 by default and the policy filters nothing. *Detection:* count current pages with no declared origin field; a corpus of all-default provenance is a corpus with no provenance.

**FM-D3 — Filter mistaken for gate.** §4, restated as a failure mode because stating it once in prose is how it gets missed. *Detection:* not mechanical. The nearest check is whether any page's classification claims a level the substrate beneath it does not enforce.

**FM-D4 — Fallback chosen by default rather than decision.** A deployment inherits `full` because it is the common setting and serves customers with it. *Detection:* profile name against audience; an external-facing deployment running a reach-optimised fallback is a mismatch worth an alert.

**FM-D5 — Ratification saturation.** Enough agents that the human ratification queue never empties, so writes either stall or get signed unread. *Detection:* MPLPB-SWARM-013 §8's ratification latency median together with queue depth. This is FM-S9 seen from the deployment side, and it is the ceiling in §9 of that paper arriving in practice.

---

## 8. Falsifiers

**8.1** If any shipped profile can be constructed with `answer_without_retrieval: True`, the invariant in §1 is documentation rather than a mechanism.

**8.2** If a page above a profile's `max_served_depth` can be served through any code path — library, console, or citation render — the depth policy is advisory and §3.4's external guarantee is void.

**8.3** If `refusals_for` returns fewer than all applicable reasons, §6's claim about first-failure gates applies to this implementation too.

**8.4 (open)** Whether the §5 trade-off holds on a real corpus with naive probes. Both figures come from MPLPB-TEST-014's synthetic corpus. If the trade is smaller than measured, the profile split on `fallback` is over-engineered; if larger, the external profile is losing more reach than this document admits.

**8.5 (open)** Whether these four profiles cover the deployments that exist. Four was chosen by enumerating the audiences the prior papers already named, not by surveying anybody. A deployment that fits none of them is evidence against the taxonomy and should be reported rather than forced into the nearest one.

---

## 9. Conclusion

The settings that vary between deployments are not the interesting ones. Lease durations and classification lists are bookkeeping.

The two that matter are `max_served_depth` and `fallback`, and they matter for opposite reasons. The first is a policy the corpus can finally enforce, because provenance depth is a number that travels with the page — an organisation can now state *no machine-written material reaches customers* and have it be checkable rather than aspirational. The second is a trade the corpus cannot resolve for you, because reach and precision are one dial and where to set it depends on a cost only the deployment knows.

Everything else in this document is an attempt to write those two decisions down where somebody auditing later can see what was chosen and why.

---

## Philosophical Note

The same corpus, read four ways.

What changes between a research group and a customer-facing assistant is not the documents. It is how much of the machine's own writing anybody is willing to stand behind.

— MDM

---

## Source note

The reference implementation is `mplpb_swarm/profiles.py`, released MIT with CC BY 4.0 documentation. The four profiles are declared objects with no I/O; the tests in `tests/test_profiles.py` assert the invariant, the strictness ordering, and that the external profile refuses machine-authored material through every path.

The §5 figures are from MPLPB-TEST-014 v2 §6, run 2026-08-30 under seed 20260830 against a synthetic corpus. They are a direction and not a constant.

**Back to.** Main Index > Specification / Architecture Sub-Index
