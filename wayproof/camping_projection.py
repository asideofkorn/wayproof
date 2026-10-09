"""Explicit camping hierarchy for consumers; never infer containment from location."""
from dataclasses import dataclass
from typing import Tuple

from .schema import Entity, Claim, Relationship

SITE_KINDS = frozenset({'campsite', 'family_campsite', 'group_campsite',
                       'cabin_campsite', 'equestrian_campsite', 'equestrian_group_campsite'})
PARENT_KINDS = frozenset({'campground', 'backcountry_camp', 'equestrian_campsite_area'})


@dataclass(frozen=True)
class CampingHierarchy:
    parents: Tuple[Entity, ...]
    children: Tuple[Entity, ...]
    relationships: Tuple[Relationship, ...]


def camping_hierarchy(reads, entity_id):
    entity = reads.entity(entity_id)
    parents, children, links = {}, {}, []
    for rel in reads.relationships_for(entity_id):
        if not rel.evidence_ids:
            continue
        if rel.predicate in {'part_of', 'contained_by'}:
            child_id, parent_id = rel.subject_id, rel.object_id
        elif rel.predicate == 'contains':
            child_id, parent_id = rel.object_id, rel.subject_id
        else:
            continue
        child, parent = reads.entity(child_id), reads.entity(parent_id)
        if child.kind not in SITE_KINDS or parent.kind not in PARENT_KINDS:
            continue
        links.append(rel)
        if child_id == entity.entity_id:
            parents[parent_id] = parent
        else:
            children[child_id] = child
    key = lambda e: (e.name.casefold(), e.entity_id)
    return CampingHierarchy(tuple(sorted(parents.values(), key=key)),
                            tuple(sorted(children.values(), key=key)), tuple(links))


def camping_claims(reads, entity_id) -> Tuple[Claim, ...]:
    """Keep campground/scoped rules; do not promote another campsite's facts.

    Child facts remain on that child's own page and in the unchanged complete
    entity payload. A sibling scoped to the campground is not a campground fact.
    """
    return tuple(c for c in reads.scoped_claims_for(entity_id)
                 if c.subject_id == entity_id or reads.entity(c.subject_id).kind not in SITE_KINDS)
