"""The ablation harness, checked. MPLPB-TEST-014 v2.

These tests assert that the harness does what the ledger says it does.
They do not pin any result: a test that fixed the numbers would turn a
finding into a fixture.
"""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
V1 = REPO / "ablation" / "v1"
V2 = REPO / "ablation" / "v2"
sys.path.insert(0, str(REPO / "tools" / "ablation"))


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestPreRegistration(unittest.TestCase):

    def test_v2_probe_hash_matches_the_frozen_record(self):
        recorded = (V2 / "probes.sha256").read_text().split()[0]
        self.assertEqual(_hash(V2 / "probes.json"), recorded)

    def test_v1_remains_verifiable_after_supersession(self):
        """Superseded runs are retained, not deleted. A ledger that cannot
        be re-checked is a claim, not a record."""
        recorded = (V1 / "probes.sha256").read_text().split()[0]
        self.assertEqual(_hash(V1 / "probes.json"), recorded)

    def test_v2_declares_what_it_supersedes(self):
        payload = json.loads((V2 / "probes.json").read_text())
        self.assertIn("v1", payload["supersedes"])

    def test_v2_carries_the_ceiling_validity_check(self):
        payload = json.loads((V2 / "probes.json").read_text())
        self.assertTrue(any(p.startswith("P0") for p in payload["predictions"]))

    def test_v2_carries_the_confound_check(self):
        payload = json.loads((V2 / "probes.json").read_text())
        self.assertTrue(any("CONFOUND" in p for p in payload["predictions"]))

    def test_v2_adds_the_classes_v1_lacked(self):
        probes = json.loads((V2 / "probes.json").read_text())["probes"]
        kinds = {p["kind"] for p in probes}
        self.assertTrue({"paraphrase", "discriminate"}.issubset(kinds))

    def test_neither_run_claims_to_close_the_test(self):
        for version in (V1, V2):
            payload = json.loads((version / "probes.json").read_text())
            self.assertIn("NOT", payload["note"])


class TestStripping(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import run_ablation
        cls.mapping = run_ablation.strip_arm()
        cls.stripped = V2 / "arm-stripped"

    def test_stripped_arm_retains_no_metadata(self):
        for f in self.stripped.glob("*.html"):
            self.assertNotIn("mplpb:", f.read_text(encoding="utf-8"))

    def test_stripped_arm_retains_no_links(self):
        for f in self.stripped.glob("*.html"):
            self.assertNotIn("<a ", f.read_text(encoding="utf-8"))

    def test_stripped_arm_is_flat(self):
        self.assertFalse(any(p.is_dir() for p in self.stripped.iterdir()))

    def test_navigation_pages_are_absent(self):
        structured = list((V2 / "arm-structured").rglob("*.html"))
        stripped = list(self.stripped.glob("*.html"))
        self.assertEqual(len(structured) - len(stripped), 7)

    def test_prose_survives_stripping(self):
        bodies = [f.read_text(encoding="utf-8")
                  for f in self.stripped.glob("*.html")]
        self.assertTrue(any("stand on its own" in b for b in bodies))

    def test_filenames_carry_no_identifier(self):
        for name in self.mapping:
            self.assertRegex(name, r"^\d{4}\.html$")


class TestHarnessFairness(unittest.TestCase):

    def test_ranker_cannot_see_which_arm_it_reads(self):
        import inspect
        import run_ablation
        self.assertNotIn("arm", inspect.signature(run_ablation.search).parameters)
        body = inspect.getsource(run_ablation.search).split('"""')[2]
        self.assertNotIn("arm", body)

    def test_scoring_is_mechanical(self):
        """No scoring path may consult anything but declared fields and the
        expected answer frozen in the pre-registration."""
        import inspect
        import run_ablation
        source = inspect.getsource(run_ablation.score)
        for forbidden in ("input(", "random", "if probe['id']"):
            self.assertNotIn(forbidden, source)

    def test_neutral_vocabulary_does_not_appear_in_the_corpus(self):
        import run_ablation
        import run_graded
        docs = run_ablation.load_structured()
        self.assertEqual(run_graded.leak_check(docs), [])

    def test_graded_probes_span_four_overlap_levels(self):
        import run_graded
        levels = {p["level"] for p in run_graded.graded_probes()}
        self.assertEqual(levels, {"1.00", "0.50", "0.33", "0.00"})

    def test_zero_overlap_probes_share_nothing_with_the_trigger(self):
        import run_ablation
        import run_graded
        for probe in run_graded.graded_probes():
            if probe["level"] != "0.00":
                continue
            words = set(run_ablation.terms(probe["query"]))
            self.assertTrue(words.issubset(set(w.lower() for w in run_graded.NEUTRAL)))


if __name__ == "__main__":
    unittest.main()
