"""Identifier allocation and supersession ordering.

Two rules from MPLPB-SWARM-013 4:

  4.1  Identifiers are allocated, never chosen. An agent that constructs
       an identifier from a prefix and a count it read a moment ago has
       built a race.

  4.2  Supersession of a given identifier is linearizable. Two writers
       superseding the same predecessor produce a fork: two documents,
       both current, both valid, and a corpus that is ambiguous about its
       own history. No check in MPLPB-LOCAL-008 11 catches this.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from mplpb_swarm.lease import Lease, LeaseError, fence
from mplpb_swarm.page import Page

SWARM_DIR = "_swarm"


class SupersessionError(RuntimeError):
    """Raised when a supersession would fork or skip the current head."""


def _counter_file(root: Path) -> Path:
    d = Path(root) / SWARM_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d / "ids.json"


def _read(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def allocate(root: Path, lease: Lease, prefix: str) -> str:
    """Allocate the next identifier for a prefix, under lease.

    The fence happens before the counter advances, so a stale writer
    cannot consume an identifier it will not be allowed to use.
    """
    fence(root, lease)
    path = _counter_file(root)
    state = _read(path)
    nxt = int(state.get(prefix, 0)) + 1
    state[prefix] = nxt
    _write(path, state)
    return f"{prefix}-{nxt:03d}"


@dataclass(frozen=True)
class Fork:
    predecessor: str
    successors: tuple[str, ...]

    def __str__(self) -> str:
        return (f"{self.predecessor} has {len(self.successors)} current "
                f"successors: {', '.join(self.successors)}")


def find_forks(pages: list[Page]) -> list[Fork]:
    """Detect FM-S2. Group current pages by what they claim to supersede."""
    claims: dict[str, list[str]] = defaultdict(list)
    for page in pages:
        if not page.is_current:
            continue
        for predecessor in page.supersedes:
            claims[predecessor].append(page.doc_id)
    return [
        Fork(pred, tuple(sorted(succ)))
        for pred, succ in sorted(claims.items())
        if len(succ) > 1
    ]


def head_of(pages: list[Page], doc_id: str) -> Page | None:
    """The current page that supersedes doc_id, if exactly one does."""
    successors = [p for p in pages if p.is_current and doc_id in p.supersedes]
    if len(successors) == 1:
        return successors[0]
    return None


def check_supersession(pages: list[Page], predecessor: str,
                       lease: Lease | None = None) -> None:
    """Refuse a supersession that would fork or that targets a retired page.

    Called before the write, and the write is still fenced. Both checks
    are needed: this one gives a readable error, the fence gives the
    guarantee.
    """
    by_id = {p.doc_id: p for p in pages if p.doc_id}
    target = by_id.get(predecessor)
    if target is None:
        raise SupersessionError(f"{predecessor} is not in this corpus")
    if not target.is_current:
        existing = head_of(pages, predecessor)
        raise SupersessionError(
            f"{predecessor} is already superseded"
            + (f" by {existing.doc_id}" if existing else "")
        )
    already = [p.doc_id for p in pages if p.is_current and predecessor in p.supersedes]
    if already:
        raise SupersessionError(
            f"supersession fork: {predecessor} already superseded by "
            f"{', '.join(sorted(already))} (FM-S2)"
        )


__all__ = [
    "allocate", "find_forks", "head_of", "check_supersession",
    "Fork", "SupersessionError", "LeaseError",
]
