"""Provenance depth, federated routing, health metrics, and the falsifiers
of MPLPB-SWARM-013 12.1 through 12.4.
"""

from __future__ import annotations

import unittest

from mplpb_swarm.crawl import crawl
from mplpb_swarm.health import ambiguity_rate, measure
from mplpb_swarm.lease import held
from mplpb_swarm.origin import (
    RatificationRequired,
    check_teachable,
    depth_for,
    depth_report,
    meta_block,
    ratify,
)
from mplpb_swarm.page import Page
from mplpb_swarm.registry import Registry, terms
from mplpb_swarm.supersede import allocate, find_forks
from tests.support import CorpusTest, SiteTest


def _page(doc_id: str, origin: str = "human", depth: int = 0,
          status: str = "current") -> Page:
    return Page(doc_id=doc_id, path=f"{doc_id}.html", origin=origin,
                origin_depth=depth, status=status)


class TestDepth(unittest.TestCase):

    def test_a_page_taught_from_nothing_is_depth_one(self):
        self.assertEqual(depth_for([]), 1)

    def test_teaching_from_human_material_gives_depth_one(self):
        self.assertEqual(depth_for([_page("A"), _page("B")]), 1)

    def test_teaching_from_taught_material_climbs(self):
        self.assertEqual(depth_for([_page("A", "taught", 1)]), 2)

    def test_depth_follows_the_deepest_source(self):
        self.assertEqual(
            depth_for([_page("A"), _page("B", "taught", 3)]), 4)

    def test_default_threshold_permits_teaching_from_humans(self):
        self.assertEqual(check_teachable([_page("A")]), 1)

    def test_default_threshold_refuses_teaching_from_taught(self):
        with self.assertRaises(RatificationRequired) as caught:
            check_teachable([_page("A", "taught", 1)])
        self.assertIn("FM-S3", str(caught.exception))

    def test_refusal_names_the_deepest_source(self):
        with self.assertRaises(RatificationRequired) as caught:
            check_teachable([_page("SHALLOW"), _page("DEEP", "taught", 2)])
        self.assertIn("DEEP", str(caught.exception))

    def test_a_raised_threshold_permits_a_longer_chain(self):
        self.assertEqual(check_teachable([_page("A", "taught", 2)], threshold=3), 3)

    def test_ratification_resets_to_human_depth_zero(self):
        page = ratify(_page("A", "taught", 4), "m.mcphetridge")
        self.assertEqual((page.origin, page.origin_depth), ("human", 0))
        self.assertEqual(page.ratified_by, "m.mcphetridge")

    def test_ratification_requires_a_named_ratifier(self):
        with self.assertRaises(ValueError):
            ratify(_page("A", "taught", 2), "   ")

    def test_meta_block_renders_the_provenance_fields(self):
        block = meta_block("taught", 1, taught_from=["A-1"])
        self.assertIn('name="mplpb:origin" content="taught"', block)
        self.assertIn('name="mplpb:origin_depth" content="1"', block)
        self.assertIn('name="mplpb:taught_from" content="A-1"', block)

    def test_meta_block_refuses_an_unknown_origin(self):
        with self.assertRaises(ValueError):
            meta_block("invented", 1)


class TestDepthReport(unittest.TestCase):

    def test_histogram_counts_current_pages_by_depth(self):
        report = depth_report([_page("A"), _page("B"), _page("C", "taught", 1)])
        self.assertEqual(report.histogram, {0: 2, 1: 1})

    def test_retired_pages_are_excluded(self):
        report = depth_report([_page("A"), _page("B", status="retired")])
        self.assertEqual(report.histogram, {0: 1})

    def test_machine_fraction_is_the_non_zero_share(self):
        report = depth_report([_page("A"), _page("B", "taught", 1),
                               _page("C", "taught", 1), _page("D", "taught", 2)])
        self.assertAlmostEqual(report.machine_fraction, 0.75)

    def test_unratified_pages_above_threshold_are_counted(self):
        self.assertEqual(
            depth_report([_page("A", "taught", 3)]).unratified_beyond, 1)

    def test_a_ratified_deep_page_is_not_counted(self):
        page = _page("A", "taught", 3)
        page.ratified_by = "m.mcphetridge"
        self.assertEqual(depth_report([page]).unratified_beyond, 0)

    def test_malformed_provenance_is_named(self):
        self.assertIn("BAD", depth_report([_page("BAD", "human", -1)]).malformed)


class TestRegistry(SiteTest):

    def test_registry_loads_both_corpora(self):
        self.assertEqual(len(Registry.from_root(self.registry_root)), 2)

    def test_registry_index_is_not_itself_an_entry(self):
        ids = {e.corpus_id for e in Registry.from_root(self.registry_root).entries}
        self.assertEqual(ids, {"CORPUS-A", "CORPUS-B"})

    def test_roots_resolve_relative_to_the_registry(self):
        entry = Registry.from_root(self.registry_root).get("CORPUS-A")
        self.assertTrue((entry.root / "index.html").is_file())

    def test_a_deployment_question_routes_to_corpus_a(self):
        decision = Registry.from_root(self.registry_root).route(
            "how do we roll back a deployment")
        self.assertEqual(decision.kind, "routed")
        self.assertEqual(decision.corpus.corpus_id, "CORPUS-A")

    def test_a_records_question_routes_to_corpus_b(self):
        decision = Registry.from_root(self.registry_root).route(
            "classification of held records")
        self.assertEqual(decision.corpus.corpus_id, "CORPUS-B")

    def test_a_question_touching_both_returns_ambiguous(self):
        decision = Registry.from_root(self.registry_root).route(
            "retention of deployment logs")
        self.assertEqual(decision.kind, "ambiguous")

    def test_ambiguous_decision_quotes_both_declared_scopes(self):
        decision = Registry.from_root(self.registry_root).route(
            "retention of deployment logs")
        explanation = decision.explain()
        self.assertIn("CORPUS-A", explanation)
        self.assertIn("CORPUS-B", explanation)
        self.assertIn("narrow", explanation)

    def test_ambiguous_decision_names_no_winner(self):
        decision = Registry.from_root(self.registry_root).route(
            "retention of deployment logs")
        self.assertIsNone(decision.corpus)

    def test_an_unowned_question_is_refused_rather_than_guessed(self):
        decision = Registry.from_root(self.registry_root).route(
            "photosynthesis in coastal mangroves")
        self.assertEqual(decision.kind, "no_owner")

    def test_common_words_alone_are_not_a_match(self):
        self.assertNotIn("the", terms("the and of a build"))
        self.assertIn("build", terms("the and of a build"))

    def test_registry_drift_is_clean_on_the_shipped_site(self):
        self.assertEqual(Registry.from_root(self.registry_root).drift(), [])

    def test_registry_drift_reports_a_missing_root(self):
        import shutil
        shutil.rmtree(self.corpus_b)
        drift = Registry.from_root(self.registry_root).drift()
        self.assertTrue(any("CORPUS-B" in problem for problem in drift))


class TestHealth(CorpusTest):

    def test_clean_corpus_reports_no_problems(self):
        self.seed_minimal()
        health = measure(crawl(self.root, corpus="TEST"), self.root, corpus="TEST")
        self.assertEqual(health.problems(), [])

    def test_fork_appears_in_problems(self):
        self.seed_minimal()
        self.write("ops/alpha_alt.html", "Alt", id="OPS-ALPHA-003",
                   corpus="TEST", scope="alt", status="current",
                   supersedes="OPS-ALPHA-001", origin="human", origin_depth="0")
        health = measure(crawl(self.root, corpus="TEST"), self.root)
        self.assertTrue(any("FM-S2" in p for p in health.problems()))

    def test_unratified_depth_appears_in_problems(self):
        self.seed_minimal()
        self.write("ops/deep.html", "Deep", id="OPS-DEEP-007", corpus="TEST",
                   scope="deep", status="current", origin="taught",
                   origin_depth="3")
        health = measure(crawl(self.root, corpus="TEST"), self.root)
        self.assertTrue(any("FM-S3" in p for p in health.problems()))

    def test_retired_mismatch_is_zero_when_the_retired_path_runs(self):
        self.seed_minimal()
        health = measure(crawl(self.root, corpus="TEST"), self.root)
        self.assertEqual(health.retired_mismatch, 0)

    def test_maintenance_rate_is_writes_over_reads(self):
        self.seed_minimal()
        health = measure(crawl(self.root), self.root, reads=1000, writes=4)
        self.assertAlmostEqual(health.maintenance_rate, 0.004)

    def test_maintenance_rate_is_none_without_read_counts(self):
        self.seed_minimal()
        self.assertIsNone(measure(crawl(self.root), self.root).maintenance_rate)

    def test_ratification_median_detects_theatre(self):
        self.seed_minimal()
        health = measure(crawl(self.root), self.root,
                         ratification_latencies=[3.0, 4.0, 3.5, 4.5])
        self.assertLess(health.ratification_median, 5.0)

    def test_ambiguity_rate_over_decisions(self):
        class D:
            def __init__(self, kind):
                self.kind = kind
        self.assertAlmostEqual(
            ambiguity_rate([D("routed"), D("ambiguous"), D("routed"), D("routed")]),
            0.25)

    def test_report_renders_without_a_corpus_name(self):
        self.seed_minimal()
        self.assertIn("pages", measure(crawl(self.root), self.root).report())


class TestFalsifiers(SiteTest, CorpusTest):
    """MPLPB-SWARM-013 12.1-12.4, run rather than described."""

    def setUp(self):
        SiteTest.setUp(self)
        CorpusTest.setUp(self)

    def test_121_concurrency_yields_no_collisions_or_forks(self):
        """Many writers, one corpus. If identifiers collide or supersession
        forks, the discipline in section 4 does not do what it claims."""
        self.seed_minimal()
        allocated = []
        for n in range(25):
            with held(self.root, "ops", f"agent-{n}") as lease:
                allocated.append(allocate(self.root, lease, "OPS-NOTE"))
        self.assertEqual(len(set(allocated)), 25)
        self.assertEqual(find_forks(crawl(self.root).pages), [])

    def test_122_laundering_is_contained_at_the_threshold(self):
        """An invented claim taught in at depth 1 cannot silently spawn a
        second generation, and its depth is visible wherever it is cited."""
        seeded = _page("INVENTED-001", "taught", 1)
        with self.assertRaises(RatificationRequired):
            check_teachable([seeded])
        from mplpb_swarm.cite import cite
        self.assertIn("origin=taught d1", cite(seeded))

    def test_123_federation_boundary_holds(self):
        """No page outside a crawled root enters that root's index."""
        for root, name in ((self.corpus_a, "CORPUS-A"), (self.corpus_b, "CORPUS-B")):
            result = crawl(root, corpus=name)
            for page in result.pages:
                self.assertFalse(page.path.startswith(".."), page.path)
                self.assertTrue((root / page.path).is_file())

    def test_124_ambiguity_is_returned_not_merged(self):
        """A query answerable from two corpora stops rather than blending."""
        decision = Registry.from_root(self.registry_root).route(
            "retention of deployment logs")
        self.assertEqual(decision.kind, "ambiguous")
        self.assertIsNone(decision.corpus)
        self.assertEqual(len(decision.touched), 2)

    def test_135_ablation_is_still_open(self):
        """Recorded, not run. Open since MPLPB-LOCAL-008 section 14 Test 4.

        Asserts only that the shipped paper makes no claim of having run
        it. A marker, not evidence.
        """
        from pathlib import Path
        docs = Path(__file__).resolve().parents[1] / "docs"
        text = (docs / "MPLPB_Swarm_Scale.md").read_text(encoding="utf-8")
        self.assertIn("structure has not been shown to beat storage", text)
        self.assertNotIn("the ablation has been run", text.lower())
        self.assertNotIn("closes the ablation", text.lower())

    def test_paper_declares_what_it_supersedes(self):
        """v3 absorbs three drafts. They are retained, not deleted."""
        from pathlib import Path
        repo = Path(__file__).resolve().parents[1]
        text = (repo / "docs" / "MPLPB_Swarm_Scale.md").read_text(encoding="utf-8")
        self.assertIn("MPLPB-DEPLOY-015 v1", text)
        self.assertIn("MPLPB-TEST-014 v2", text)
        superseded = repo / "docs" / "superseded"
        self.assertTrue((superseded / "MPLPB_Deployment_Profiles.md").is_file())
        self.assertTrue((superseded / "MPLPB_Ablation_Partial.md").is_file())


if __name__ == "__main__":
    unittest.main()
