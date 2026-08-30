"""Command line for Swarm MPLPB.

    python3 -m mplpb_swarm health site/corpus-a
    python3 -m mplpb_swarm route site/registry "retention of build logs"
    python3 -m mplpb_swarm forks site/corpus-a
    python3 -m mplpb_swarm depth site/corpus-a
    python3 -m mplpb_swarm cite site/corpus-a OPS-DEPLOY-002

Exits non-zero when a swarm-layer defect is found, so it drops into CI the
same way the MPLPB-LOCAL-008 validator does.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mplpb_swarm.cite import cite
from mplpb_swarm.crawl import crawl
from mplpb_swarm.health import measure
from mplpb_swarm.origin import DEFAULT_THRESHOLD, depth_report
from mplpb_swarm.profiles import PROFILES, get as get_profile
from mplpb_swarm.registry import Registry
from mplpb_swarm.supersede import find_forks


def _corpus_name(root: Path) -> str:
    from mplpb_swarm.registry import _meta_of
    return _meta_of(root / "index.html", "corpus")


def cmd_health(args) -> int:
    root = Path(args.root)
    name = _corpus_name(root)
    result = crawl(root, corpus=name)
    health = measure(result, root, corpus=name, threshold=args.threshold)
    print(health.report())
    return 1 if health.problems() else 0


def cmd_forks(args) -> int:
    root = Path(args.root)
    forks = find_forks(crawl(root, corpus=_corpus_name(root)).pages)
    if not forks:
        print("no supersession forks")
        return 0
    for fork in forks:
        print(f"FM-S2  {fork}")
    return 1


def cmd_depth(args) -> int:
    root = Path(args.root)
    report = depth_report(crawl(root, corpus=_corpus_name(root)).pages,
                          threshold=args.threshold)
    for depth, count in report.histogram.items():
        print(f"  depth {depth}  {'#' * count} ({count})")
    print(f"machine-authored share: {report.machine_fraction:.0%}")
    if report.unratified_beyond:
        print(f"FM-S3  {report.unratified_beyond} page(s) above threshold "
              f"{args.threshold} without ratification")
        return 1
    return 0


def cmd_route(args) -> int:
    registry = Registry.from_root(Path(args.registry))
    drift = registry.drift()
    for problem in drift:
        print(f"FM-S6  {problem}", file=sys.stderr)
    decision = registry.route(" ".join(args.query))
    print(decision.explain())
    return 0 if decision.kind == "routed" and not drift else 1


def cmd_cite(args) -> int:
    root = Path(args.root)
    pages = crawl(root, corpus=_corpus_name(root)).by_id()
    page = pages.get(args.doc_id)
    if page is None:
        print(f"not in this corpus: {args.doc_id}", file=sys.stderr)
        return 1
    print(cite(page))
    return 0


def cmd_profile(args) -> int:
    if args.name == "list":
        for name, profile in sorted(PROFILES.items()):
            print(f"{name:<20}{profile.audience}")
        return 0
    print(get_profile(args.name).summary())
    return 0


def cmd_serve_check(args) -> int:
    """Would this profile serve this page? Prints every reason it would not."""
    root = Path(args.root)
    profile = get_profile(args.profile)
    page = crawl(root, corpus=_corpus_name(root)).by_id().get(args.doc_id)
    if page is None:
        print(f"not in this corpus: {args.doc_id}", file=sys.stderr)
        return 1
    reasons = profile.refusals_for(page)
    if not reasons:
        print(f"{profile.name}: would serve {cite(page)}")
        return 0
    print(f"{profile.name}: would NOT serve {args.doc_id}")
    for reason in reasons:
        print(f"  - {reason}")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mplpb-swarm",
                                     description=__doc__.splitlines()[0])
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD,
                        help="origin_depth permitted without ratification")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, fn, help_text in (
        ("health", cmd_health, "all section 8 metrics for one corpus"),
        ("forks", cmd_forks, "detect supersession forks (FM-S2)"),
        ("depth", cmd_depth, "origin-depth histogram (FM-S3)"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("root")
        p.set_defaults(func=fn)

    p = sub.add_parser("route", help="route a query across registered corpora")
    p.add_argument("registry")
    p.add_argument("query", nargs="+")
    p.set_defaults(func=cmd_route)

    p = sub.add_parser("profile", help="show a deployment profile, or 'list'")
    p.add_argument("name", help="swarm | lab | helpdesk-internal | "
                                "helpdesk-external | list")
    p.set_defaults(func=cmd_profile)

    p = sub.add_parser("serve-check",
                       help="would a profile serve this page, and if not why")
    p.add_argument("profile")
    p.add_argument("root")
    p.add_argument("doc_id")
    p.set_defaults(func=cmd_serve_check)

    p = sub.add_parser("cite", help="print the full citation for a document")
    p.add_argument("root")
    p.add_argument("doc_id")
    p.set_defaults(func=cmd_cite)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
