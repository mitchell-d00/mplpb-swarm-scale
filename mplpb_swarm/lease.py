"""Writer leases with fencing tokens (MPLPB-SWARM-013 4.3).

A lease is a file. It names a spoke, an owner, an expiry, and a
monotonically increasing fencing token. Expiry alone is not sufficient: a
writer can acquire a lease, stall past its expiry, and wake believing it is
still authorised. The token makes that write fail where it must fail — at
the point of writing, not at the point of checking.

Granularity is the spoke, because the spoke is the unit of declared scope
and therefore the unit that has cross-document structure worth protecting.

Deliberately boring. See 4.4 for why nothing cleverer is here.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

SWARM_DIR = "_swarm"
DEFAULT_TTL = 30.0


class LeaseError(RuntimeError):
    """Raised when a lease cannot be acquired or a token is refused."""


@dataclass(frozen=True)
class Lease:
    spoke: str
    owner: str
    token: int
    expires: float

    @property
    def expired(self) -> bool:
        return time.time() >= self.expires


def _dir(root: Path) -> Path:
    d = Path(root) / SWARM_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _lease_file(root: Path, spoke: str) -> Path:
    return _dir(root) / f"lease.{spoke or '_root'}.json"


def _head_file(root: Path, spoke: str) -> Path:
    return _dir(root) / f"head.{spoke or '_root'}.json"


def _read(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def _next_token(root: Path, spoke: str) -> int:
    """Tokens are monotonic per spoke and never reused, including across
    lease handovers. The counter lives beside the head, not in the lease,
    so that releasing a lease cannot reset it."""
    head = _head_file(root, spoke)
    state = _read(head)
    issued = int(state.get("issued", 0)) + 1
    state["issued"] = issued
    state.setdefault("accepted", 0)
    _write(head, state)
    return issued


def acquire(root: Path, spoke: str, owner: str, ttl: float = DEFAULT_TTL) -> Lease:
    """Take the lease for a spoke, or raise if it is held and unexpired."""
    path = _lease_file(root, spoke)
    existing = _read(path)
    if existing and time.time() < float(existing.get("expires", 0)):
        raise LeaseError(
            f"spoke {spoke!r} is leased to {existing.get('owner')!r} "
            f"for another {float(existing['expires']) - time.time():.1f}s"
        )
    lease = Lease(spoke, owner, _next_token(root, spoke), time.time() + ttl)
    _write(path, {"spoke": spoke, "owner": owner,
                  "token": lease.token, "expires": lease.expires})
    return lease


def release(root: Path, lease: Lease) -> None:
    """Release a lease. The token counter is not rewound."""
    path = _lease_file(root, lease.spoke)
    current = _read(path)
    if current.get("token") == lease.token:
        path.unlink(missing_ok=True)


def fence(root: Path, lease: Lease) -> None:
    """Present a token for a write. Raises if a higher token already wrote.

    This is the check that must happen at write time. A caller that
    validates ``lease.expired`` and then writes has reintroduced exactly
    the race the token exists to close.
    """
    head = _head_file(root, lease.spoke)
    state = _read(head)
    accepted = int(state.get("accepted", 0))
    if lease.token < accepted:
        raise LeaseError(
            f"stale write to spoke {lease.spoke!r}: token {lease.token} "
            f"below accepted {accepted} (FM-S4)"
        )
    state["accepted"] = lease.token
    state.setdefault("issued", lease.token)
    state["issued"] = max(int(state["issued"]), lease.token)
    _write(head, state)


class held:
    """Context manager: acquire, yield, release.

    Fencing is not automatic. A write must call fence() itself, because
    the whole point is that the check happens at the write and not at the
    boundary of a block.
    """

    def __init__(self, root: Path, spoke: str, owner: str,
                 ttl: float = DEFAULT_TTL) -> None:
        self.root, self.spoke, self.owner, self.ttl = Path(root), spoke, owner, ttl
        self.lease: Lease | None = None

    def __enter__(self) -> Lease:
        self.lease = acquire(self.root, self.spoke, self.owner, self.ttl)
        return self.lease

    def __exit__(self, *exc) -> None:
        if self.lease is not None:
            release(self.root, self.lease)
