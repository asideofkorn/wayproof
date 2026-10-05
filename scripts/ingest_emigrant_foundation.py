#!/usr/bin/env python3
"""Prepare batch 1 from reviewed USFS sources; never publish or fetch live data.

Run against a base without this batch, or pass --base to a clean main checkout
when regenerating the same unmerged ChangeSet. See docs/ingestion/emigrant.md.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wayproof.canonical_storage import RECORD_SPECS, load_canonical, write_candidate
from wayproof.schema import (
    CanonicalRecords, ChangeAction, ChangeOperation, ChangeSet, Claim, Condition,
    DerivedResult, Entity, Evidence, KnowledgeGap, Observation, Relationship,
    Requirement, Rule, Source, SpatialScope, TemporalScope,
)
from wayproof.write_service import ChangeSetWriteService, InMemoryCanonicalRepository

ROOT = Path(__file__).resolve().parents[1]
CHANGE_ID = 'wp-20261005-emigrant-foundation'
LAND = 'wilderness-emigrant'
SCOPE = 'scope-emigrant-wilderness'
RETRIEVED = datetime(2026, 10, 5, 22, 9, 18, tzinfo=timezone.utc)
ORDER_TIME = TemporalScope(date(2026, 7, 8), date(2029, 6, 30))
FS = 'https://www.fs.usda.gov'
SOURCES = {
    'overview': '/r05/stanislaus/wilderness/emigrant-wilderness',
    'access': '/r05/stanislaus/recreation/emigrant-wilderness-highway-108-access',
    'permits': '/r05/stanislaus/permits/wilderness-permits',
    'order': '/r05/stanislaus/alerts/renewal-emigrant-wilderness-use-rules',
    'signed-order': '/sites/nfs/files/r05/stanislaus/publication/alerts/STF-16-2026-08%20Emigrant%20Wilderness%20Restrictions%20%28Order%29%20.pdf',
    'regulations': '/sites/nfs/files/r05/stanislaus/publication/ECI-ROG.pdf',
    'trailheads': '/sites/nfs/files/r05/stanislaus/publication/emigrant-wilderness-trailheads.pdf',
    'conditions': '/r05/stanislaus/conditions',
    'alerts': '/r05/stanislaus/alerts',
}
ACCESS = (
    ('bell-meadow', 'Bell Meadow Trailhead', ['Bell Meadow'], 'plenty of informal parking'),
    ('bourland-meadow', 'Bourland Meadow Trailhead', ['Bourland Meadow'], 'limited parking'),
    ('box-springs', 'Box Springs Trailhead', ['Box Springs', 'Box Spring'], 'limited parking'),
    ('crabtree', 'Crabtree Trailhead', ['Crabtree', 'Crabtree Camp'], 'large paved parking area'),
    ('coyote-meadow', 'Coyote Meadow Trailhead', ['Coyote Meadow', 'Cooper Pocket', 'Coyote Meadows'], 'limited parking'),
    ('eagle-meadow', 'Eagle Meadow Trailhead', ['Eagle Meadow'], 'limited parking'),
    ('gianelli', 'Gianelli Cabin Trailhead', ['Gianelli', 'Gianelli Cabin', 'Burst Rock Trailhead'], 'limited parking'),
    ('kennedy-meadows', 'Kennedy Meadows Trailhead (Stanislaus)', ['Kennedy Meadows'], None),
    ('waterhouse', 'Waterhouse Trailhead', ['Waterhouse'], 'limited parking'),
    ('sonora-pass', 'Sonora Pass Trailhead', ['Sonora Pass'], 'limited parking'),
)
ORDER_EXEMPTIONS = [
    'Forest Service permit specifically authorizing the otherwise prohibited act',
    'Federal, State, local officer or organized rescue/firefighting force performing official duty',
]


def build_records():
    r = CanonicalRecords()
    r.entities.append(Entity(LAND, 'wilderness', 'Emigrant Wilderness'))
    r.spatial_scopes.append(SpatialScope(SCOPE, 'wilderness', LAND))
    for key, path in SOURCES.items():
        r.sources.append(Source('source-usfs-emigrant-' + key, FS + path,
                                'USDA Forest Service, Stanislaus National Forest'))

    def claim(key, source, content, predicate, value, subject=LAND, scopes=(SCOPE,), time=None):
        cid, oid, eid = ('claim-emigrant-' + key, 'observation-emigrant-' + key,
                         'evidence-emigrant-' + key)
        r.observations.append(Observation(
            oid, 'source-usfs-emigrant-' + source, content,
            retrieved_at=RETRIEVED, observer='Wayproof primary-source review',
        ))
        r.evidence.append(Evidence(eid, oid, cid))
        r.claims.append(Claim(cid, subject, predicate, value, (eid,), time, scopes))
        return cid

    def gap(key, question, reason, *related):
        gid = 'gap-emigrant-' + key
        r.gaps.append(KnowledgeGap(gid, question, (LAND, *related), reason))
        return gid

    def rule(key, cid, consequence, conditions=(), time=None):
        rid = 'rule-emigrant-' + key
        r.rules.append(Rule(rid, cid, consequence, conditions, (SCOPE,), time))
        r.requirements.append(Requirement('requirement-emigrant-' + key, rid, consequence))

    claim('identity', 'overview',
          'Overview: Emigrant Wilderness lies entirely in Stanislaus National Forest and Tuolumne County; the page describes 113,000 acres and roughly 25 by 15 miles.',
          'managed_land_description', {'forest': 'Stanislaus National Forest',
          'county': 'Tuolumne County', 'published_area_acres': 113000,
          'approximate_dimensions_miles': [25, 15]})
    for key, name, aliases, parking in ACCESS:
        entity = 'trailhead-emigrant-' + key
        scope = 'scope-emigrant-' + key
        r.entities.append(Entity(entity, 'trailhead', name))
        r.spatial_scopes.append(SpatialScope(scope, 'access_point', entity))
        cid = claim('access-' + key, 'access',
                    f'Highway 108 Access, overview access list: {aliases[0]} is explicitly listed as access to Emigrant Wilderness.',
                    'wilderness_access', LAND, entity, (scope,))
        r.relationships.append(Relationship('relationship-emigrant-access-' + key,
                               entity, 'accesses', LAND, ('evidence-emigrant-access-' + key,)))
        # These are names on the current access page and the reviewed 2012 guide/diagram.
        # Keep alias provenance attached to the actual naming source below.
        alias_source = 'access' if key == 'kennedy-meadows' else 'trailheads'
        guide_aliases = {'box-springs': ['Box Springs'],
                         'gianelli': ['Gianelli Cabin', 'Burst Rock'],
                         'coyote-meadow': ['Coyote Meadow', 'Cooper Pocket']}
        aliases = guide_aliases.get(key, aliases)
        claim('aliases-' + key, alias_source,
              f'The source labels this access point {name}; alternate source labels: {", ".join(aliases)}.',
              'aliases', aliases, entity, (scope,))
        if parking:
            claim('parking-' + key, 'trailheads',
                  f'ROG 16-26, April 2012, {aliases[0]} entry: {parking}. This is a historical guide description, not a current availability observation.',
                  'parking_description', {'description': parking, 'source_edition': '2012-04',
                  'current_availability': 'unknown', 'requires_current_check': True}, entity, (scope,))

    permit = claim('overnight-permit-order', 'signed-order',
        'STF-16-2026-08, page 1, item 1 requires a valid wilderness permit for overnight camping at any time of year. Effective July 8, 2026 through June 30, 2029; the order lists special-authorization and official-duty exemptions.',
        'overnight_permit_required', {'required': True, 'season': 'year-round',
        'order': 'STF-16-2026-08', 'exemptions': ORDER_EXEMPTIONS}, time=ORDER_TIME)
    rule('overnight-wilderness-permit', permit,
         'Obtain and carry a valid Emigrant wilderness permit for overnight camping. STF-16-2026-08 has special-authorization and official-duty exemptions; confirm these with the Forest Service. Seasonal web wording conflicts with the year-round order; recheck with the issuing station.',
         (Condition('activity.overnight', 'equals', True),), ORDER_TIME)
    seasonal = claim('permit-season-access-page', 'access',
        'Highway 108 Access, Current Conditions says permits are required April 15-November 15; its Restrictions and Passes and Permits sections require a permit for overnight visits without a seasonal qualification.',
        'wilderness_permit_season', {'current_conditions_season': 'April 15-November 15',
        'restrictions_section': 'valid permit for overnight trips without seasonal qualification'})
    permit_conflict = gap('permit-season-conflict', 'Does the seasonal webpage exempt winter overnight trips?',
        'Conflict: the access page gives April 15-November 15 but also unqualified overnight wording; the signed order requires overnight permits year-round through June 30, 2029. Do not infer a winter exemption; confirm current requirements with the issuing ranger station.', permit, seasonal)
    fee = claim('permit-fee', 'access', 'Fee Site and Info: wilderness and campfire permits are issued free; this does not establish fees for outside-agency permits or guide services.',
                'wilderness_permit_fee', {'usd': 0, 'scope': 'Stanislaus-issued wilderness permit'})
    claim('permit-quota', 'permits', 'Wilderness Permits, introduction: Emigrant has no quota or reservation system; permits for trips originating in another forest or park come from that agency.',
          'wilderness_permit_quota', {'quota': False, 'reservation_system': False,
                                     'scope': 'Emigrant, not neighboring Yosemite or other-agency entry'})
    acquisition = claim('permit-acquisition', 'permits',
        'Where to Acquire: Sugar Pine issues in person during office hours and by kiosk when closed; Calaveras issues in person, with closed-office kiosks at Calaveras or Lake Alpine; Sonora Supervisor office issues in person. Outside-Stanislaus travel cannot use self-issue; call or visit, with phone/email issuance up to seven days ahead.',
        'wilderness_permit_process', {
            'sugar_pine': 'in person during office hours; kiosk when closed',
            'calaveras': 'in person during office hours; kiosks at Calaveras or Lake Alpine when closed',
            'sonora_supervisor_office': 'in person during office hours',
            'outside_stanislaus_self_issue_allowed': False,
            'outside_stanislaus_channel': 'visit or call ranger station; phone/email up to 7 days ahead',
            'other_agency_origin': 'obtain permit from agency managing entry trailhead',
            'sugar_pine_phone': '209-965-3434',
        })
    claim('groveland-acquisition', 'permits',
        'Where to Acquire: Groveland issues by phone or in person no more than 24 hours in advance, up to three days for holiday weekends; Yosemite Kibbie/Eleanor entries have separate quotas and instructions.',
        'wilderness_permit_process', {'station': 'Groveland', 'phone': '209-962-7825',
        'advance_hours_max': 24, 'holiday_weekend_advance_days_max': 3,
        'yosemite_entries': 'separate quotas and itinerary-specific requirements; verify with station'})

    people = claim('group-limit-order', 'signed-order',
        'STF-16-2026-08 page 1, item 4 prohibits groups larger than 15; order exemptions apply.',
        'wilderness_group_size_limit', {'maximum_persons': 15, 'exemptions': ORDER_EXEMPTIONS}, time=ORDER_TIME)
    rule('group-limit', people, 'Keep the traveling, camping or gathering group to 15 people or fewer, unless specifically exempt under STF-16-2026-08.', time=ORDER_TIME)
    claim('affiliated-groups', 'permits', 'Group Size Limits: affiliated groups must camp and travel separately, remaining at least one mile apart.',
          'affiliated_group_separation', {'minimum_miles': 1})
    food = claim('food-storage', 'regulations',
        'ROG 16-23, June 2024, Food Storage and Bear Safety: food, trash and scented items must be inaccessible to wildlife; a properly used bear-resistant container is most effective, and a proper bear hang is permissible but unreliable on the Stanislaus.',
        'wilderness_food_storage', {'required': 'food, trash and scented items inaccessible to wildlife',
        'bear_container': 'recommended most effective method', 'proper_hang': 'permissible but unreliable',
        'scope': 'Stanislaus; neighboring jurisdictions have separate requirements'})
    rule('food-storage', food, 'Secure food, trash and scented items so wildlife cannot access them; use a properly used bear-resistant container or proper hang. Confirm current storage rules and separate requirements when crossing jurisdictions.')
    claim('dispersed-camping', 'regulations',
          'ROG 16-23, June 2024, Campsite Selection says these wilderness areas have no designated campsites; visitors identify sites meeting the guidelines.',
          'camping_inventory', {'type': 'dispersed wilderness camping', 'designated_campsites': False,
                               'scope': 'wilderness interior, not developed approach campgrounds'})
    claim('camp-setback-order', 'signed-order',
          'STF-16-2026-08 page 1, item 2 prohibits camping within 100 feet of lakes, streams and trails or where posted; order exemptions apply.',
          'camping_setback', {'minimum_feet': 100, 'from': ['lakes', 'streams', 'trails'],
                             'posted_restrictions_also_apply': True, 'exemptions': ORDER_EXEMPTIONS}, time=ORDER_TIME)
    lake_names = ['Camp', 'Bear', 'Grouse', 'Powell', 'Waterhouse']
    night_order = claim('lake-night-limit-order', 'signed-order',
        'STF-16-2026-08 page 1, item 8 prohibits camping for more than one consecutive night at Camp, Bear, Grouse, Powell or Waterhouse Lakes.',
        'lake_camping_limit', {'maximum_nights': 1, 'basis': 'consecutive',
        'lakes': lake_names, 'exemptions': ORDER_EXEMPTIONS}, time=ORDER_TIME)
    night_page = claim('lake-night-limit-guidance', 'access',
        'Highway 108 Access, Restrictions: one night per trip camping limits apply at Grouse, Camp, Bear, Powell and Waterhouse lakes.',
        'lake_camping_limit', {'maximum_nights': 1, 'basis': 'per trip', 'lakes': lake_names})
    night_gap = gap('lake-night-limit-conflict', 'Can a trip return for a nonconsecutive night at these lakes?',
        'Conflict: the signed order says one consecutive night while the access page and June 2024 regulations guide say one night per trip. Preserve both; confirm before planning a return camp.', night_order, night_page)
    waste_order = claim('sanitation-order', 'signed-order',
        'STF-16-2026-08 page 1, item 3 prohibits disposal of body waste or wash water within 100 feet of any water source.',
        'sanitation_setback', {'minimum_feet': 100, 'from': ['water'], 'exemptions': ORDER_EXEMPTIONS}, time=ORDER_TIME)
    waste_page = claim('sanitation-guidance', 'access',
        'Highway 108 Access Restrictions requires human and canine waste and wash water disposal more than 200 feet from water, trails and campsites.',
        'sanitation_setback', {'more_than_feet': 200, 'from': ['water', 'trails', 'campsites']})
    waste_gap = gap('sanitation-conflict', 'Which sanitation setback applies?',
        'Conflict in stated minima: the order and permit page state 100 feet from water; access guidance says more than 200 feet from water, trails and campsites. This may distinguish legal minima from stricter guidance; it is not silently reconciled.', waste_order, waste_page)
    stock_order = claim('stock-tie-order', 'signed-order',
        'STF-16-2026-08 page 1, item 6 prohibits tying stock to trees or within 200 feet of lakes, streams, trails and campsites except loading/unloading.',
        'stock_tying_setback', {'minimum_feet': 200, 'from': ['lakes', 'streams', 'trails', 'campsites'],
        'trees_prohibited': True, 'exception': 'loading/unloading', 'order_exemptions': ORDER_EXEMPTIONS}, time=ORDER_TIME)
    stock_page = claim('stock-tie-permit-page', 'permits',
        'Stock Holding and Grazing assigns a 100-foot tying setback in Emigrant and Carson-Iceberg, except loading/unloading.',
        'stock_tying_setback', {'minimum_feet': 100, 'exception': 'loading/unloading'})
    stock_gap = gap('stock-setback-conflict', 'Is the stock tying setback 100 or 200 feet?',
        'Conflict: signed 2026 order uses 200 feet; permit page uses 100 feet for Emigrant. Recheck with the district and retain both sources.', stock_order, stock_page)
    claim('stock-group-order', 'signed-order', 'STF-16-2026-08 page 1, item 7 caps pack and saddle stock at 25 head; exemptions apply.',
        'stock_group_limit', {'maximum_head': 25, 'exemptions': ORDER_EXEMPTIONS}, time=ORDER_TIME)
    claim('stock-overnight-exclusion-order', 'signed-order',
        'STF-16-2026-08 page 1, item 7b prohibits overnight grazing/holding stock within a quarter mile of Camp, Bear, Grouse, Powell, Wood, Deer and Waterhouse Lakes.',
        'stock_overnight_restriction', {'prohibited_within_miles': 0.25,
        'lakes': ['Camp', 'Bear', 'Grouse', 'Powell', 'Wood', 'Deer', 'Waterhouse'], 'exemptions': ORDER_EXEMPTIONS}, time=ORDER_TIME)
    claim('stock-overnight-cap-order', 'signed-order',
        'STF-16-2026-08 page 1, item 7c limits overnight grazing/holding within a quarter mile of Gem, Jewelry, Long, Maxwell, Pingree, Piute and Rosasco Lakes to four stock.',
        'stock_overnight_restriction', {'maximum_head': 4, 'within_miles': 0.25,
        'lakes': ['Gem', 'Jewelry', 'Long', 'Maxwell', 'Pingree', 'Piute', 'Rosasco'], 'exemptions': ORDER_EXEMPTIONS}, time=ORDER_TIME)
    fire_order = claim('campfire-order', 'signed-order',
        'STF-16-2026-08 page 1, item 5 prohibits campfires above 9,000 feet or within half a mile of Emigrant Lake.',
        'campfire_restriction', {'above_elevation_feet': 9000, 'within_miles_of_emigrant_lake': 0.5,
        'exemptions': ORDER_EXEMPTIONS}, time=ORDER_TIME)
    fire_page = claim('stove-fire-permit-page', 'permits',
        'Campfires section introduces a list prohibiting a campfire or stove fire under listed conditions, including above 9,000 feet or within half a mile of Emigrant Lake; the signed order item 5 only says campfire.',
        'stove_fire_restriction', {'scope_wording': 'campfire or stove fire',
        'above_elevation_feet': 9000, 'within_miles_of_emigrant_lake': 0.5})
    fire_gap = gap('stove-scope-conflict', 'Does the elevation/lake fire restriction include a regulated gas stove?',
        'Scope disagreement: permit webpage introduces campfire or stove fire; signed order says campfire and the June 2024 guide encourages regulated gas stoves. Confirm stove treatment and current fire orders; do not infer permission from a campfire permit.', fire_order, fire_page)
    claim('campfire-permit', 'regulations',
        'ROG 16-23 June 2024, Stoves and Fires requires a free California Campfire Permit for all stoves and fires and compliance with current fire restrictions.',
        'campfire_permit_required', {'uses': ['stoves', 'fires'], 'required': True,
        'issuer': 'CAL FIRE', 'does_not_override_restrictions': True})
    claim('dogs', 'access', 'Pet Information: dogs must be under direct control and Tuolumne County has a leash ordinance.',
        'pet_policy', {'direct_control_required': True, 'county_leash_ordinance': 'Tuolumne County; verify details'})
    claim('mechanized-use', 'regulations',
        'ROG 16-23 June 2024 Regulations and Guidelines prohibits mechanized/motorized equipment and drones while explicitly allowing non-motorized mobility devices.',
        'wilderness_transport_restriction', {'mechanized_motorized_equipment': 'prohibited',
        'drones': 'prohibited', 'exception': 'non-motorized mobility devices may be utilized'})
    claim('pack-out', 'regulations', 'ROG 16-23 June 2024 requires packing out trash and food scraps, without burning or burying.',
        'waste_pack_out', {'trash_and_food_scraps': 'pack out; do not burn or bury'})

    conditions = claim('conditions-recheck', 'conditions',
        'Current Conditions links to current fire restrictions, fire/smoke, avalanche forecasts and regional snow depth. These are pre-trip checking sources, not an observation of open roads or safe trails.',
        'pretrip_current_conditions_recheck', {'required': True,
        'topics': ['fire restrictions', 'smoke', 'snow', 'weather and avalanche conditions']}, scopes=(SCOPE,))
    alerts = claim('alerts-recheck', 'alerts',
        'Alerts index reviewed October 5, 2026 includes fire restrictions, occupancy limits and road closure orders, including a portion of 4N12 and Cherry access road 1N98. Exact applicability and current status require individual order/map review.',
        'pretrip_current_conditions_recheck', {'required': True,
        'topics': ['road closures and seasonal access', 'current fire orders', 'occupancy rules'],
        'current_route_access': 'unknown'}, scopes=(SCOPE,))
    access_recheck = claim('access-recheck', 'access',
        'Operational Hours directs visitors to check conditions and weather before travel; named access points do not establish that a road, parking space, water supply or facility will be available.',
        'pretrip_current_conditions_recheck', {'required': True,
        'topics': ['access roads', 'parking', 'trail conditions', 'water and facilities', 'issuing station operations']}, scopes=(SCOPE,))
    access_inputs = []
    for key, name, _, _ in ACCESS:
        access_inputs.append(claim('approach-recheck-' + key, 'alerts',
            f'The forest alert index contains dynamic road and fire orders. Current applicability to {name} needs individual order and map review; its named access relationship is not an open-status observation.',
            'pretrip_current_conditions_recheck', {'required': True,
            'topics': ['road and trail status', 'fire restrictions', 'parking and facility availability'],
            'status': 'unknown'}, subject='trailhead-emigrant-' + key,
            scopes=('scope-emigrant-' + key,)))
    dynamic_gap = gap('current-conditions', 'Are the selected approach and facilities usable on the trip date?',
        'Current road, trail, snow, crossing, water, fire and facility status is unknown. Individual alerts and mapped closures need route-specific matching; the Site Open banner is not route-level clearance.', conditions, alerts, access_recheck, *access_inputs)
    boundary = gap('boundary-geometry', 'Where is the reviewed designated wilderness boundary?',
        'Authoritative boundary geometry has not yet been matched. A published map exists but no polygon is traced from it. Boundary review belongs to a later batch.', access_recheck)
    topology = gap('route-topology', 'How do the selected trailheads connect to lakes, passes and each other?',
        'Ten explicit access identities are published, but no route segments, directionality, distances, alternatives or facility spurs are asserted. The 2012 mileage table and 2021 diagram differ (for example Gianelli-Powell); reconcile maps and editions before modeling traversal.', access_recheck)
    inventory = gap('facility-inventory', 'What camps, toilets, water sources and parking are available along the approach?',
        'Dispersed camping is represented, but individual lake sites, trailhead facilities, Kennedy/Aspen operators and developed approach campgrounds are deferred. Historical parking descriptions are not live inventory.', access_recheck)
    cross = gap('cross-boundary-permits', 'What applies when entering from another agency or continuing to Yosemite or Hoover?',
        'Entry-agency issuance and the no-self-issue exception are preserved; specific cross-boundary routes, quotas, permit products and food/dog rules require separate agency review. Do not extend Emigrant no-quota/free-permit claims across boundaries.', acquisition)
    dates = claim('order-dates-permit-page', 'permits',
        'The permit-page introduction labels current Forest Orders effective July 8, 2025-June 30, 2029, while its linked Emigrant order is STF-16-2026-08, effective July 8, 2026-June 30, 2029.',
        'published_order_effective_dates', {'summary_start': '2025-07-08', 'linked_order_start': '2026-07-08', 'end': '2029-06-30'})
    date_gap = gap('order-date-conflict', 'Which effective start belongs to STF-16-2026-08?',
        'Conflict: permit summary says 2025; signed order and alert say 2026. Executable order-backed rules use the signed 2026 interval, with the disagreement exposed.', permit, dates)
    inputs = [conditions, alerts, access_recheck, acquisition, fee, permit, seasonal,
              night_order, night_page, waste_order, waste_page, stock_order, stock_page,
              fire_order, fire_page, dates, food]
    gaps = [permit_conflict, night_gap, waste_gap, stock_gap, fire_gap, dynamic_gap,
            boundary, topology, inventory, cross, date_gap]
    r.derived_results.append(DerivedResult(
        'result-emigrant-pretrip-recheck', 'pretrip_recheck',
        {'required': True, 'topics': ['access and current conditions', 'permit acquisition and seasonal conflict',
         'camping and sanitation conflicts', 'stock and stove restrictions', 'cross-boundary requirements']},
        tuple(inputs + access_inputs + gaps), 'Project source conflicts and operational unknowns onto Emigrant wilderness trips; access-only contexts receive road and facility rechecks without implying wilderness entry.',
    ))
    return r


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, default=ROOT)
    args = parser.parse_args()
    records = build_records()
    operations = []
    for kind, (collection, identifier, _) in RECORD_SPECS.items():
        for record in getattr(records, collection):
            rid = getattr(record, identifier)
            operations.append(ChangeOperation(
                ChangeAction.ADD, kind, rid, f'canonical/v0/{collection}/{rid}.json',
                'Establish source-backed Emigrant planning foundation with explicit uncertainty.',
                evidence_refs=getattr(record, 'evidence_ids', ()),
                knowledge_gap_refs=(rid,) if kind == 'gap' else (),
            ))
    change = ChangeSet(CHANGE_ID, records,
        summary='Establish Emigrant Wilderness access and overnight planning foundation; preserve USFS conflicts and current-condition gaps.',
        operations=tuple(operations))
    writes = ChangeSetWriteService(InMemoryCanonicalRepository(load_canonical(args.base)))
    writes.propose(change, 'emigrant-source-ingestion')
    errors = writes.validate(CHANGE_ID, 'emigrant-validator')
    if errors:
        raise RuntimeError('\n'.join(errors))
    candidate = writes.prepare(CHANGE_ID, 'emigrant-candidate-builder')
    write_candidate(args.output, candidate, writes.get(CHANGE_ID))
    print(f'Prepared {len(operations)} records in {CHANGE_ID}; not published.')


if __name__ == '__main__':
    main()
