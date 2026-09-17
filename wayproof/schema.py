"""Which vocabulary governs which stored column.

A fact about the data rather than about any one caller, so it lives in the
package. Guarded by ``tests/test_schema_integrity.py``.
"""

from __future__ import annotations

from typing import List, Tuple

from . import booking, camping, permits
from .access import _VALID_STATUSES
from .advisories import _VALID_KINDS, _VALID_SEVERITY
from .regulations import _VALID_SCOPES

#: ``(csv, column, allowed values, multi-valued)``. Every vocabulary that
#: governs stored data belongs here, whether or not its loader also checks it --
#: `permit_source_log.csv:verdict` is the case that does not.
#:
#: `campgrounds.csv:campsite_type` is absent on purpose: it has no vocabulary to
#: bind to. See CLAUDE.md's Known list.
BOUND: List[Tuple[str, str, set, bool]] = [
    ("campgrounds.csv", "access_mode", camping._VALID_ACCESS_MODES, True),
    ("campgrounds.csv", "coord_precision", camping._VALID_COORD_PRECISION, False),
    ("campgrounds.csv", "unit_level", camping._VALID_UNIT_LEVELS, False),
    ("campgrounds.csv", "pets_marker", camping._VALID_PETS_MARKERS, False),
    ("campgrounds.csv", "pets_animals", camping._VALID_PETS_ANIMALS, True),
    ("campsites.csv", "site_type", camping._VALID_SITE_TYPES, False),
    ("booking_channels.csv", "applies_to", booking._VALID_APPLIES_TO, False),
    ("booking_channels.csv", "scope_type", _VALID_SCOPES, False),
    ("regulations.csv", "scope_type", _VALID_SCOPES, False),
    ("advisories.csv", "scope_type", _VALID_SCOPES, False),
    ("advisories.csv", "kind", _VALID_KINDS, False),
    ("advisories.csv", "severity", _VALID_SEVERITY, False),
    ("approaches.csv", "status", _VALID_STATUSES, False),
    ("permit_source_log.csv", "verdict", permits._VALID_VERDICTS, False),
]

#: Vocabularies that guard a function argument or a derived value rather than a
#: stored column. Listed so the coverage test cannot pass by forgetting one.
NOT_STORED = {
    "_VALID_CONFIDENCE", "_VALID_STATUS",   # reports.py, set at submit time
    "_VALID_ROLES",                          # provenance.py
    "_VALID_MECHANISMS", "_VALID_SEASONS",   # release_policy.py, parsed from prose
}
