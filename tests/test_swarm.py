"""Concurrency layer: leases, fencing tokens, allocation, supersession."""

from __future__ import annotations

import time
import unittest

from mplpb_swarm.crawl import crawl
from mplpb_swarm.lease import LeaseError, acquire, fence, held, release
from mplpb_swarm.supersede import (
    SupersessionError,
    allocate,
    check_supersession,
    find_forks,
    head_of,
)
from tests.support import CorpusTest


class TestLeases(CorpusTest):

    def test_lease_can_be_acquired(self):
        lease = acquire(self.root, "ops", "agent-a")
        self.assertEqual(lease.owner, "agent-a")
        self.assertGreater(lease.token, 0)

    def test_second_writer_is_refused_while_the_lease_holds(self):
        acquire(self.root, "ops", "agent-a", ttl=30)
        with self.assertRaises(LeaseError):
            acquire(self.root, "ops", "agent-b")

    def test_a_different_spoke_is_not_blocked(self):
        acquire(self.root, "ops", "agent-a", ttl=30)
        other = acquire(self.root, "policy", "agent-b")
        self.assertEqual(other.spoke, "policy")

    def test_lease_is_reacquirable_after_expiry(self):
        acquire(self.root, "ops", "agent-a", ttl=0.05)
        time.sleep(0.08)
        self.assertEqual(acquire(self.root, "ops", "agent-b").owner, "agent-b")

    def test_release_frees_the_spoke(self):
        lease = acquire(self.root, "ops", "agent-a", ttl=30)
        release(self.root, lease)
        self.assertEqual(acquire(self.root, "ops", "agent-b").owner, "agent-b")

    def test_tokens_are_monotonic_across_handovers(self):
        first = acquire(self.root, "ops", "agent-a", ttl=0.05)
        time.sleep(0.08)
        second = acquire(self.root, "ops", "agent-b")
        self.assertGreater(second.token, first.token)

    def test_release_does_not_rewind_the_counter(self):
        first = acquire(self.root, "ops", "agent-a")
        release(self.root, first)
        self.assertGreater(acquire(self.root, "ops", "agent-b").token, first.token)

    def test_held_releases_on_exit(self):
        with held(self.root, "ops", "agent-a") as lease:
            self.assertEqual(lease.owner, "agent-a")
        self.assertEqual(acquire(self.root, "ops", "agent-b").owner, "agent-b")

    def test_held_releases_even_when_the_body_raises(self):
        with self.assertRaises(ValueError):
            with held(self.root, "ops", "agent-a"):
                raise ValueError("write failed")
        self.assertEqual(acquire(self.root, "ops", "agent-b").owner, "agent-b")


class TestFencing(CorpusTest):
    """FM-S4. The check must happen at the write, not at the boundary."""

    def test_current_holder_may_write(self):
        lease = acquire(self.root, "ops", "agent-a")
        fence(self.root, lease)  # must not raise

    def test_stale_writer_is_refused_after_handover(self):
        stalled = acquire(self.root, "ops", "agent-a", ttl=0.05)
        time.sleep(0.08)
        fresh = acquire(self.root, "ops", "agent-b")
        fence(self.root, fresh)
        with self.assertRaises(LeaseError) as caught:
            fence(self.root, stalled)
        self.assertIn("FM-S4", str(caught.exception))

    def test_expiry_alone_would_not_have_caught_it(self):
        """The stalled writer's own lease object looks expired, but a
        writer that only consulted that would already have written."""
        stalled = acquire(self.root, "ops", "agent-a", ttl=0.05)
        time.sleep(0.08)
        fence(self.root, acquire(self.root, "ops", "agent-b"))
        self.assertTrue(stalled.expired)
        with self.assertRaises(LeaseError):
            fence(self.root, stalled)

    def test_fencing_is_per_spoke(self):
        ops = acquire(self.root, "ops", "agent-a")
        policy = acquire(self.root, "policy", "agent-b")
        fence(self.root, ops)
        fence(self.root, policy)  # unaffected by the ops token


class TestAllocation(CorpusTest):
    """FM-S1. Identifiers are allocated, never chosen."""

    def test_allocation_is_sequential(self):
        with held(self.root, "ops", "agent-a") as lease:
            first = allocate(self.root, lease, "OPS-NOTE")
            second = allocate(self.root, lease, "OPS-NOTE")
        self.assertEqual((first, second), ("OPS-NOTE-001", "OPS-NOTE-002"))

    def test_prefixes_have_independent_counters(self):
        with held(self.root, "ops", "agent-a") as lease:
            self.assertEqual(allocate(self.root, lease, "OPS-NOTE"), "OPS-NOTE-001")
            self.assertEqual(allocate(self.root, lease, "OPS-PROC"), "OPS-PROC-001")

    def test_sequential_writers_never_collide(self):
        seen = set()
        for n in range(12):
            with held(self.root, "ops", f"agent-{n}") as lease:
                seen.add(allocate(self.root, lease, "OPS-NOTE"))
        self.assertEqual(len(seen), 12)

    def test_stale_writer_cannot_consume_an_identifier(self):
        stalled = acquire(self.root, "ops", "agent-a", ttl=0.05)
        time.sleep(0.08)
        fresh = acquire(self.root, "ops", "agent-b")
        allocate(self.root, fresh, "OPS-NOTE")
        with self.assertRaises(LeaseError):
            allocate(self.root, stalled, "OPS-NOTE")


class TestSupersession(CorpusTest):
    """FM-S2. Two current successors to one predecessor is a fork."""

    def _fork(self):
        self.seed_minimal()
        self.write("ops/alpha_alt.html", "Alpha (alt)", id="OPS-ALPHA-003",
                   corpus="TEST", scope="a competing replacement",
                   status="current", version="v2", supersedes="OPS-ALPHA-001",
                   origin="human", origin_depth="0")
        return crawl(self.root, corpus="TEST").pages

    def test_clean_corpus_has_no_forks(self):
        self.seed_minimal()
        self.assertEqual(find_forks(crawl(self.root).pages), [])

    def test_fork_is_detected(self):
        forks = find_forks(self._fork())
        self.assertEqual(len(forks), 1)
        self.assertEqual(forks[0].predecessor, "OPS-ALPHA-001")

    def test_fork_names_both_successors(self):
        self.assertEqual(find_forks(self._fork())[0].successors,
                         ("OPS-ALPHA-002", "OPS-ALPHA-003"))

    def test_head_is_unresolvable_under_a_fork(self):
        self.assertIsNone(head_of(self._fork(), "OPS-ALPHA-001"))

    def test_head_resolves_on_a_clean_corpus(self):
        self.seed_minimal()
        head = head_of(crawl(self.root).pages, "OPS-ALPHA-001")
        self.assertEqual(head.doc_id, "OPS-ALPHA-002")

    def test_retired_successors_do_not_count_as_forks(self):
        self.seed_minimal()
        self.write("_log/superseded/alpha_alt.html", "Alt (retired)",
                   id="OPS-ALPHA-003", corpus="TEST", scope="retired alt",
                   status="retired", supersedes="OPS-ALPHA-001",
                   origin="human", origin_depth="0")
        self.assertEqual(find_forks(crawl(self.root).pages), [])

    def test_superseding_an_already_superseded_page_is_refused(self):
        self.seed_minimal()
        with self.assertRaises(SupersessionError) as caught:
            check_supersession(crawl(self.root).pages, "OPS-ALPHA-001")
        self.assertIn("already superseded", str(caught.exception))

    def test_superseding_an_unknown_page_is_refused(self):
        self.seed_minimal()
        with self.assertRaises(SupersessionError):
            check_supersession(crawl(self.root).pages, "OPS-NOTHING-999")

    def test_superseding_the_current_head_is_permitted(self):
        self.seed_minimal()
        check_supersession(crawl(self.root).pages, "OPS-ALPHA-002")


if __name__ == "__main__":
    unittest.main()
