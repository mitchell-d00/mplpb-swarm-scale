"""Deployment profiles. MPLPB-DEPLOY-015."""

from __future__ import annotations

import unittest

from mplpb_swarm.page import Page
from mplpb_swarm.profiles import (
    HELPDESK_EXTERNAL, HELPDESK_INTERNAL, LAB, PROFILES, SWARM, Profile,
    ProfileViolation, get,
)


def page(depth=0, status="current", classification="", doc_id="X-1") -> Page:
    return Page(doc_id=doc_id, path="x.html", status=status,
                origin_depth=depth, classification=classification,
                origin="human" if depth == 0 else "taught")


class TestInvariant(unittest.TestCase):

    def test_no_profile_answers_without_retrieval(self):
        self.assertTrue(all(not p.answer_without_retrieval
                            for p in PROFILES.values()))

    def test_the_invariant_cannot_be_configured(self):
        with self.assertRaises(ValueError):
            Profile(name="rogue", audience="x", answer_without_retrieval=True)

    def test_fallback_must_be_a_known_setting(self):
        with self.assertRaises(ValueError):
            Profile(name="x", audience="y", fallback="semantic")

    def test_unknown_profile_names_the_available_ones(self):
        with self.assertRaises(KeyError) as caught:
            get("production")
        self.assertIn("helpdesk-external", str(caught.exception))


class TestExternalHelpdesk(unittest.TestCase):
    """The strictest profile, because a wrong answer leaves the building."""

    def test_machine_taught_pages_never_reach_a_customer(self):
        self.assertFalse(HELPDESK_EXTERNAL.may_serve(
            page(depth=1, classification="public")))

    def test_human_authored_public_pages_are_served(self):
        self.assertTrue(HELPDESK_EXTERNAL.may_serve(
            page(depth=0, classification="public")))

    def test_internal_classification_does_not_leave(self):
        self.assertFalse(HELPDESK_EXTERNAL.may_serve(
            page(classification="internal")))

    def test_retired_pages_are_withheld(self):
        self.assertFalse(HELPDESK_EXTERNAL.may_serve(
            page(status="retired", classification="public")))

    def test_teaching_is_refused_outright(self):
        ok, why = HELPDESK_EXTERNAL.may_teach_from([page()])
        self.assertFalse(ok)
        self.assertIn("does not accept taught pages", why)

    def test_guard_reports_every_reason_at_once(self):
        with self.assertRaises(ProfileViolation) as caught:
            HELPDESK_EXTERNAL.guard(
                page(depth=2, status="retired", classification="internal"))
        message = str(caught.exception)
        self.assertIn("retired", message)
        self.assertIn("origin_depth", message)
        self.assertIn("classification", message)

    def test_it_chooses_precision_over_reach(self):
        self.assertEqual(HELPDESK_EXTERNAL.fallback, "prose")

    def test_the_classification_caveat_is_stated_not_implied(self):
        self.assertTrue(any("not an access control" in n
                            for n in HELPDESK_EXTERNAL.notes))


class TestInternalHelpdesk(unittest.TestCase):

    def test_depth_one_pages_are_served_to_staff(self):
        self.assertTrue(HELPDESK_INTERNAL.may_serve(
            page(depth=1, classification="internal")))

    def test_depth_two_pages_are_not(self):
        self.assertFalse(HELPDESK_INTERNAL.may_serve(page(depth=2)))

    def test_teaching_from_human_material_is_permitted(self):
        self.assertTrue(HELPDESK_INTERNAL.may_teach_from([page(depth=0)])[0])

    def test_teaching_from_taught_material_needs_ratification(self):
        ok, why = HELPDESK_INTERNAL.may_teach_from([page(depth=1)])
        self.assertFalse(ok)
        self.assertIn("ratification", why)

    def test_it_chooses_reach_over_precision(self):
        self.assertEqual(HELPDESK_INTERNAL.fallback, "full")


class TestLab(unittest.TestCase):

    def test_retired_pages_are_served_because_history_is_a_question(self):
        self.assertTrue(LAB.serve_retired)
        self.assertTrue(LAB.may_serve(page(status="retired")))

    def test_a_higher_depth_is_tolerated(self):
        self.assertTrue(LAB.may_serve(page(depth=2)))
        self.assertFalse(LAB.may_serve(page(depth=3)))

    def test_teaching_runs_without_ceremony(self):
        self.assertTrue(LAB.may_teach_from([page(depth=1)])[0])

    def test_leases_are_long_enough_for_a_person(self):
        self.assertGreater(LAB.lease_ttl, SWARM.lease_ttl)


class TestSwarm(unittest.TestCase):

    def test_leases_are_short_because_agents_fail_fast(self):
        self.assertLessEqual(SWARM.lease_ttl, 15.0)

    def test_teaching_from_taught_material_is_gated(self):
        self.assertFalse(SWARM.may_teach_from([page(depth=1)])[0])

    def test_navigation_pages_are_dropped_by_default(self):
        self.assertTrue(SWARM.drop_navigation)


class TestOrdering(unittest.TestCase):
    """The profiles should form a sensible strictness ordering."""

    def test_served_depth_tightens_toward_the_customer(self):
        self.assertEqual(
            [p.max_served_depth for p in
             (LAB, HELPDESK_INTERNAL, HELPDESK_EXTERNAL)], [2, 1, 0])

    def test_only_the_external_profile_disables_teaching(self):
        disabled = [p.name for p in PROFILES.values() if not p.teaching_enabled]
        self.assertEqual(disabled, ["helpdesk-external"])

    def test_every_profile_drops_navigation_after_fm_l12(self):
        self.assertTrue(all(p.drop_navigation for p in PROFILES.values()))

    def test_summary_states_the_invariant_first(self):
        self.assertIn("never (invariant)", SWARM.summary())


if __name__ == "__main__":
    unittest.main()
