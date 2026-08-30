"""Corpus layer: parsing, bounded crawl, the three ingestion paths, citations."""

from __future__ import annotations

import unittest

from mplpb_swarm.cite import audit, cite
from mplpb_swarm.crawl import _resolve, crawl
from mplpb_swarm.page import parse
from tests.support import CorpusTest, SiteTest, page_source


class TestParsing(unittest.TestCase):

    def test_reads_declared_fields(self):
        page = parse(page_source(
            "Alpha", id="A-1", scope="the alpha thing", status="current",
            version="v2", origin="taught", origin_depth="1"), "a.html")
        self.assertEqual(page.doc_id, "A-1")
        self.assertEqual(page.scope, "the alpha thing")
        self.assertEqual(page.origin, "taught")
        self.assertEqual(page.origin_depth, 1)

    def test_supersedes_is_semicolon_separated(self):
        page = parse(page_source("A", id="A-2", supersedes="A-1; A-0"), "a.html")
        self.assertEqual(page.supersedes, ["A-1", "A-0"])

    def test_absent_status_defaults_current_but_absent_id_stays_empty(self):
        page = parse(page_source("A"), "a.html")
        self.assertEqual(page.status, "current")
        self.assertEqual(page.doc_id, "")

    def test_malformed_depth_is_flagged_not_corrected(self):
        page = parse(page_source("A", id="A-1", origin_depth="deep"), "a.html")
        self.assertEqual(page.origin_depth, -1)

    def test_retired_page_is_not_current(self):
        page = parse(page_source("A", id="A-1", status="retired"), "a.html")
        self.assertFalse(page.is_current)

    def test_text_extraction_drops_markup(self):
        page = parse(page_source("A", "<p>hello <b>there</b></p>", id="A-1"),
                     "a.html")
        self.assertIn("hello there", page.text)
        self.assertNotIn("<b>", page.text)

    def test_protected_is_parsed_as_a_flag(self):
        page = parse(page_source("A", id="A-1", protected="true"), "a.html")
        self.assertTrue(page.protected)


class TestResolve(unittest.TestCase):

    def test_sibling_link(self):
        self.assertEqual(_resolve("ops/_index.html", "alpha.html"),
                         "ops/alpha.html")

    def test_parent_link(self):
        self.assertEqual(_resolve("ops/alpha.html", "../index.html"),
                         "index.html")

    def test_absolute_url_is_external(self):
        self.assertIsNone(_resolve("index.html", "https://example.com/x.html"))

    def test_escape_above_root_is_refused(self):
        self.assertIsNone(_resolve("index.html", "../../secrets.html"))

    def test_fragment_only_link_is_not_a_page(self):
        self.assertIsNone(_resolve("index.html", "#section"))


class TestCrawl(CorpusTest):

    def test_graph_reaches_linked_pages(self):
        self.seed_minimal()
        result = crawl(self.root, corpus="TEST")
        self.assertEqual(result.via_graph, 3)

    def test_retired_page_is_ingested_off_graph(self):
        self.seed_minimal()
        result = crawl(self.root, corpus="TEST")
        self.assertEqual(result.via_retired, 1)
        self.assertIn("OPS-ALPHA-001", result.by_id())

    def test_retired_page_is_absent_from_current(self):
        self.seed_minimal()
        current = {p.doc_id for p in crawl(self.root).current()}
        self.assertNotIn("OPS-ALPHA-001", current)

    def test_orphan_page_is_swept(self):
        self.seed_minimal()
        self.write("ops/orphan.html", "Orphan", id="OPS-ORPHAN-009",
                   corpus="TEST", scope="unlinked", status="current",
                   origin="human", origin_depth="0")
        result = crawl(self.root, corpus="TEST")
        self.assertEqual(result.via_orphan, 1)
        self.assertIn("OPS-ORPHAN-009", result.by_id())

    def test_every_page_is_visited_once(self):
        self.seed_minimal()
        paths = [p.path for p in crawl(self.root).pages]
        self.assertEqual(len(paths), len(set(paths)))

    def test_external_link_is_recorded_not_followed(self):
        self.seed_minimal()
        self.write("ops/beta.html", "Beta",
                   '<a href="https://example.com/x.html">out</a>',
                   id="OPS-BETA-003", corpus="TEST", scope="beta",
                   status="current", origin="human", origin_depth="0")
        result = crawl(self.root, corpus="TEST")
        self.assertIn("https://example.com/x.html", result.external)
        self.assertNotIn("example.com", " ".join(p.path for p in result.pages))

    def test_corpus_id_travels_onto_every_page(self):
        self.seed_minimal()
        result = crawl(self.root, corpus="TEST")
        self.assertTrue(all(p.corpus == "TEST" for p in result.pages))

    def test_swarm_state_directory_is_not_ingested(self):
        self.seed_minimal()
        state = self.root / "_swarm"
        state.mkdir()
        (state / "note.html").write_text("<html></html>", encoding="utf-8")
        paths = [p.path for p in crawl(self.root).pages]
        self.assertFalse(any(p.startswith("_swarm/") for p in paths))


class TestCitation(CorpusTest):

    def test_citation_carries_every_provenance_field(self):
        self.seed_minimal()
        page = crawl(self.root, corpus="TEST").by_id()["OPS-ALPHA-002"]
        text = cite(page)
        for expected in ("TEST", "OPS-ALPHA-002", "ops/alpha.html", "local",
                         "current", "origin=human d0"):
            self.assertIn(expected, text)

    def test_citation_of_a_taught_page_shows_its_depth(self):
        self.seed_minimal()
        self.write("ops/gamma.html", "Gamma", id="OPS-GAMMA-004", corpus="TEST",
                   scope="gamma", status="current", origin="taught",
                   origin_depth="2")
        page = crawl(self.root, corpus="TEST").by_id()["OPS-GAMMA-004"]
        self.assertIn("origin=taught d2", cite(page))

    def test_audit_accepts_a_complete_citation(self):
        self.seed_minimal()
        page = crawl(self.root, corpus="TEST").by_id()["OPS-ALPHA-002"]
        self.assertEqual(audit(cite(page)), [])

    def test_audit_names_what_a_hand_built_citation_dropped(self):
        self.assertIn("origin/depth", audit("[CORPUS-A · A-1 · a.html · local · current]"))

    def test_ratified_page_records_its_ratifier(self):
        self.seed_minimal()
        self.write("ops/delta.html", "Delta", id="OPS-DELTA-005", corpus="TEST",
                   scope="delta", status="current", origin="human",
                   origin_depth="0", ratified_by="m.mcphetridge")
        page = crawl(self.root, corpus="TEST").by_id()["OPS-DELTA-005"]
        self.assertIn("ratified=m.mcphetridge", cite(page))


class TestShippedSite(SiteTest):

    def test_corpus_a_crawls_clean(self):
        result = crawl(self.corpus_a, corpus="CORPUS-A")
        self.assertEqual(len(result.pages), 5)
        self.assertEqual(result.via_retired, 1)

    def test_corpus_b_crawls_clean(self):
        self.assertEqual(len(crawl(self.corpus_b, corpus="CORPUS-B").pages), 3)

    def test_registry_crawls_as_an_ordinary_corpus(self):
        self.assertEqual(len(crawl(self.registry_root, corpus="REGISTRY").pages), 3)


if __name__ == "__main__":
    unittest.main()
