#!/usr/bin/env python3
"""Emit the demo site: two federated corpora and a registry corpus."""
from pathlib import Path

SITE = Path(__file__).resolve().parents[1] / "site"

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <link rel="stylesheet" href="{css}">
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


def meta(**kw):
    out = []
    for k, v in kw.items():
        if v is None or v == "":
            continue
        out.append(f'  <meta name="mplpb:{k}" content="{v}">')
    return "\n".join(out)


def write(rel, title, css, m, body, back):
    path = SITE / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PAGE.format(title=title, css=css, meta=m, body=body, back=back),
                    encoding="utf-8")
    print("wrote", rel)


STYLE = """/* Swarm MPLPB demo corpora. Deliberately plain: the corpus is the
   artifact, and a stylesheet that mattered would be a dependency. */
body { font: 16px/1.55 Georgia, 'Times New Roman', serif; color: #12171c;
       max-width: 42rem; margin: 3rem auto; padding: 0 1.25rem; }
h1 { font-size: 1.5rem; border-bottom: 1px solid #d3dae1; padding-bottom: .4rem; }
h2 { font-size: 1.1rem; margin-top: 1.8rem; }
code { background: #eff2f4; padding: .1em .35em; border-radius: 3px;
       font: .9em ui-monospace, Menlo, Consolas, monospace; }
nav.back { margin-top: 2.5rem; padding-top: .8rem; border-top: 1px solid #d3dae1;
           font-size: .9rem; color: #5a6672; }
dl dt { font-weight: bold; margin-top: .7rem; }
"""

for name in ("corpus-a", "corpus-b", "registry"):
    (SITE / name).mkdir(parents=True, exist_ok=True)
    (SITE / name / "style.css").write_text(STYLE, encoding="utf-8")

# ---------------------------------------------------------------- corpus A
write(
    "corpus-a/index.html", "Build Operations — Main Index", "style.css",
    meta(id="OPS-MAIN-000", corpus="CORPUS-A", category="Index",
         scope="Deployment, rollback, and release operations for the build pipeline",
         status="current", version="2026-08-30T00:00Z v1", substrate="local",
         origin="human", origin_depth="0", owner="Platform Group"),
    """<p>Entry point and crawl root for the build operations corpus. Every
internal link below is relative; nothing here leaves this root.</p>
<h2>Spokes</h2>
<ul>
  <li><a href="ops/_index.html">Operations</a> — deployment, rollback, release</li>
</ul>
<p>Retired pages are not reachable from this graph by design. They are
ingested by the retired path and remain retrievable by document ID.</p>""",
    "Root of CORPUS-A.")

write(
    "corpus-a/ops/_index.html", "Operations — Sub-Index", "../style.css",
    meta(id="OPS-INDEX-001", corpus="CORPUS-A", category="Sub-Index",
         scope="Operational procedures for deploying and rolling back the pipeline",
         status="current", version="2026-08-30T00:00Z v1", substrate="local",
         origin="human", origin_depth="0"),
    """<h2>Pages</h2>
<ul>
  <li><a href="deploy.html">Deployment procedure</a></li>
  <li><a href="rollback.html">Rollback procedure</a></li>
</ul>""",
    '<a href="../index.html" rel="up">Back to Main Index</a>')

write(
    "corpus-a/ops/deploy.html", "Deployment Procedure", "../style.css",
    meta(id="OPS-DEPLOY-002", corpus="CORPUS-A", category="Procedure",
         scope="How a release is promoted from staging to production",
         status="current", version="2026-08-30T00:00Z v2", substrate="local",
         supersedes="OPS-DEPLOY-001", origin="human", origin_depth="0"),
    """<p>Promotion is gated on a green pipeline and a held release lease.
The lease is presented at the point of promotion, not at the point of
checking, so that a stalled promoter cannot complete a write it was no
longer authorised to make.</p>
<p>Supersedes <code>OPS-DEPLOY-001</code>, retained under
<code>_log/superseded/</code>.</p>""",
    '<a href="_index.html" rel="index">Operations</a> · '
    '<a href="../index.html" rel="up">Main Index</a>')

write(
    "corpus-a/ops/rollback.html", "Rollback Procedure", "../style.css",
    meta(id="OPS-ROLLBACK-003", corpus="CORPUS-A", category="Procedure",
         scope="How a promoted release is withdrawn and the prior release restored",
         status="current", version="2026-08-30T00:00Z v1", substrate="local",
         origin="taught", origin_depth="1", taught_from="OPS-DEPLOY-002"),
    """<p>Withdrawal reverses the promotion described in the deployment
procedure and restores the prior release.</p>
<p>This page is machine-authored at depth 1, taught from
<code>OPS-DEPLOY-002</code>. The depth travels in every citation of it.
A page taught from <em>this</em> page would be depth 2 and is refused
without ratification under the default threshold.</p>""",
    '<a href="_index.html" rel="index">Operations</a> · '
    '<a href="../index.html" rel="up">Main Index</a>')

write(
    "corpus-a/_log/superseded/deploy_v1.html",
    "Deployment Procedure (retired)", "../../style.css",
    meta(id="OPS-DEPLOY-001", corpus="CORPUS-A", category="Procedure",
         scope="Superseded promotion procedure, retained for provenance",
         status="retired", version="2026-07-02T00:00Z v1", substrate="local",
         origin="human", origin_depth="0"),
    """<p>Retired. Superseded by <code>OPS-DEPLOY-002</code>.</p>
<p>Retained rather than deleted: a corpus that cannot answer what a
document previously said has lost its own history, and that loss is
invisible to every other check.</p>""",
    "Retired page. Retrievable by document ID.")

# ---------------------------------------------------------------- corpus B
write(
    "corpus-b/index.html", "Records Policy — Main Index", "style.css",
    meta(id="POL-MAIN-000", corpus="CORPUS-B", category="Index",
         scope="Data retention, classification, and records policy",
         status="current", version="2026-08-30T00:00Z v1", substrate="local",
         origin="human", origin_depth="0", owner="Records Office"),
    """<p>Entry point and crawl root for the records policy corpus. A
different owner, a different classification regime, and a different
retention cadence from CORPUS-A — which is why it is a separate root
rather than a spoke.</p>
<h2>Spokes</h2>
<ul>
  <li><a href="policy/_index.html">Policy</a> — retention and classification</li>
</ul>""",
    "Root of CORPUS-B.")

write(
    "corpus-b/policy/_index.html", "Policy — Sub-Index", "../style.css",
    meta(id="POL-INDEX-001", corpus="CORPUS-B", category="Sub-Index",
         scope="Retention schedules and classification levels for held records",
         status="current", version="2026-08-30T00:00Z v1", substrate="local",
         origin="human", origin_depth="0"),
    """<h2>Pages</h2>
<ul><li><a href="retention.html">Retention schedule</a></li></ul>""",
    '<a href="../index.html" rel="up">Back to Main Index</a>')

write(
    "corpus-b/policy/retention.html", "Retention Schedule", "../style.css",
    meta(id="POL-RETENTION-004", corpus="CORPUS-B", category="Policy",
         scope="How long each class of record is held before disposal",
         status="current", version="2026-08-30T00:00Z v3", substrate="local",
         origin="human", origin_depth="0", classification="internal"),
    """<p>Records are held for the period set against their classification
and disposed of on schedule.</p>
<p>The <code>classification</code> field on this page is a declaration that
travels with the page. It is not an access control. The substrate beneath
this corpus enforces access; this field records what was declared, so that
an audit can reconstruct the decision.</p>""",
    '<a href="_index.html" rel="index">Policy</a> · '
    '<a href="../index.html" rel="up">Main Index</a>')

# ---------------------------------------------------------------- registry
write(
    "registry/index.html", "Corpus Registry", "style.css",
    meta(id="REG-MAIN-000", corpus="REGISTRY", category="Index",
         scope="Registered corpora, their roots, owners, and declared scopes",
         status="current", version="2026-08-30T00:00Z v1", substrate="local",
         origin="human", origin_depth="0"),
    """<p>The registry is itself an MPLPB corpus. It validates with the same
validator, supersedes with the same discipline, and is crawled by the same
crawler. A registry kept as a configuration file would be a second kind of
object with a second set of failure modes and no janitor.</p>
<h2>Registered corpora</h2>
<ul>
  <li><a href="corpus-a.html">CORPUS-A</a> — build operations</li>
  <li><a href="corpus-b.html">CORPUS-B</a> — records policy</li>
</ul>""",
    "Root of the registry corpus.")

write(
    "registry/corpus-a.html", "CORPUS-A — Build Operations", "style.css",
    meta(id="REG-A-001", corpus="CORPUS-A", root="../corpus-a",
         category="Registry Entry",
         scope="Deployment, rollback, and release operations for the build pipeline",
         status="current", version="2026-08-30T00:00Z v1", substrate="local",
         owner="Platform Group", origin="human", origin_depth="0"),
    """<dl>
  <dt>Root</dt><dd><code>../corpus-a</code></dd>
  <dt>Owner</dt><dd>Platform Group</dd>
  <dt>Substrate</dt><dd>local</dd>
</dl>
<p>A link to this corpus from another corpus is an external link and is
never followed by a crawl. The boundary is what makes the scope claimable.</p>""",
    '<a href="index.html" rel="up">Back to Registry</a>')

write(
    "registry/corpus-b.html", "CORPUS-B — Records Policy", "style.css",
    meta(id="REG-B-002", corpus="CORPUS-B", root="../corpus-b",
         category="Registry Entry",
         scope="Data retention, classification, and records policy",
         status="current", version="2026-08-30T00:00Z v1", substrate="local",
         owner="Records Office", origin="human", origin_depth="0"),
    """<dl>
  <dt>Root</dt><dd><code>../corpus-b</code></dd>
  <dt>Owner</dt><dd>Records Office</dd>
  <dt>Substrate</dt><dd>local</dd>
</dl>
<p>A query touching both retention and deployment scores against both
declared scopes and returns <code>ambiguous</code>. It does not merge:
merging across owners produces an answer nobody is accountable for.</p>""",
    '<a href="index.html" rel="up">Back to Registry</a>')
