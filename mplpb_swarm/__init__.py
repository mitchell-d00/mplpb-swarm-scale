"""Swarm MPLPB — reference implementation of MPLPB-SWARM-013 v3.

Concurrent write discipline, provenance depth, federation, deployment
profiles, and health metrics for an MPLPB local web read and written by
more than one actor.

Standard library only. No network at any point in execution.

The corpus specification is MPLPB-LOCAL-008 v4; the single-reader front end
is MPLPB-SMART-011 v1. This package adds what those two do not cover, and
does not replace either.
"""

from mplpb_swarm.cite import audit, cite
from mplpb_swarm.crawl import CrawlResult, crawl
from mplpb_swarm.health import Health, ambiguity_rate, measure
from mplpb_swarm.lease import Lease, LeaseError, acquire, fence, held, release
from mplpb_swarm.origin import (
    DepthReport,
    RatificationRequired,
    check_teachable,
    depth_for,
    depth_report,
    ratify,
)
from mplpb_swarm.page import Page, load, parse
from mplpb_swarm.profiles import (
    PROFILES,
    Profile,
    ProfileViolation,
)
from mplpb_swarm.profiles import get as profile
from mplpb_swarm.registry import Decision, Entry, Registry
from mplpb_swarm.supersede import (
    Fork,
    SupersessionError,
    allocate,
    check_supersession,
    find_forks,
    head_of,
)

__version__ = "3.0.0"
__doc_id__ = "MPLPB-SWARM-013"

__all__ = [
    "Page", "parse", "load",
    "crawl", "CrawlResult",
    "acquire", "release", "fence", "held", "Lease", "LeaseError",
    "allocate", "check_supersession", "find_forks", "head_of",
    "Fork", "SupersessionError",
    "depth_for", "check_teachable", "ratify", "depth_report",
    "DepthReport", "RatificationRequired",
    "Registry", "Entry", "Decision",
    "measure", "ambiguity_rate", "Health",
    "cite", "audit",
    "Profile", "ProfileViolation", "PROFILES", "profile",
    "__version__", "__doc_id__",
]
