"""Campground-first static presentation over canonical read projections."""
from math import ceil
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

from .camping_projection import PARENT_KINDS, SITE_KINDS

PAGE_SIZE = 20


def _helpers():
    # Keep the shared shell and evidence links in one place.
    from . import canonical_site as site
    return site


def camping_url(entity_id, page=1):
    suffix = '' if page == 1 else f'page-{page}/'
    return f'/knowledge/{entity_id}/campsites/{suffix}'


def summary(reads, entity):
    claims = reads.camping_claims(entity.entity_id)
    gaps = {g.gap_id: g for g in reads.knowledge_gaps_for(entity.entity_id)}
    for c in claims:
        gaps.update((g.gap_id, g) for g in reads.knowledge_gaps_for(c.claim_id))
    return {'entity': entity, 'claims': claims, 'gaps': tuple(gaps.values()),
            'hierarchy': reads.camping_hierarchy(entity.entity_id)}


def date_label(value):
    try:
        parsed = date.fromisoformat(str(value))
        return f'{parsed:%b} {parsed.day}, {parsed.year}'
    except ValueError:
        return str(value)


def source_line(reads, claim, compact=False):
    s = _helpers()
    provenance = reads.explain_claim(claim.claim_id)
    dates = sorted({str(o.retrieved_at)[:10] for o in provenance.observations if o.retrieved_at})
    accessed = ', '.join(f'<time datetime="{s._e(d)}">{s._e(date_label(d))}</time>' for d in dates) or 'date unknown'
    sources = ' · '.join(s._source_label(s._plain(x)) for x in provenance.sources)
    publishers = ' · '.join(sorted({x.publisher for x in provenance.sources if x.publisher}))
    if compact:
        return (f'<p class="meta">{s._e(publishers)} · Source accessed · {accessed} · '
                + s._record_link('claim',claim.claim_id,'Sources and dates') + '</p>')
    interval = claim.temporal_scope
    covered = (f'Dates covered: {interval.starts_on or "start unknown"} to {interval.ends_on or "end unknown"}.' if interval else 'Dates covered: unknown.')
    return (f'<p class="meta">{s._e(publishers)} · Source accessed · {accessed}</p>'
            f'<details class="camp-sources"><summary>Sources and dates</summary><p>{s._e(covered)}</p><p>{sources}</p>'
            f'{s._record_link("claim", claim.claim_id, "Compare evidence and source history")}</details>')



def comparable_field(value, time=False):
    text = str(value).strip()
    if time:
        for pattern in ('%H:%M', '%I:%M %p', '%I:%M%p', '%I %p'):
            try:
                parsed = datetime.strptime(text.upper(), pattern)
                return ('time', parsed.hour * 60 + parsed.minute)
            except ValueError:
                pass
    else:
        try:
            return ('number', Decimal(text))
        except InvalidOperation:
            pass
    return ('text', ' '.join(text.casefold().split()))


def conflict_notes(claim):
    """Compare explicitly named fields, never derive conflict from prose."""
    v = claim.value
    if not isinstance(v, dict):
        return []
    notes = []
    if claim.predicate == 'vehicle_limits':
        lengths = {comparable_field(v[k]) for k in (
            'maximum_vehicle_length_attribute_feet', 'maximum_vehicle_length_site_details_feet') if k in v}
        counts = {comparable_field(v[k]) for k in ('maximum_vehicles_attribute', 'maximum_vehicles_site_details') if k in v}
        if len(lengths) > 1 or len(counts) > 1:
            notes.append(('Vehicle limits differ', 'The source lists different vehicle limits. Ask the campground which limits apply before booking.'))
    if claim.predicate == 'arrival_departure_times':
        times = {str(v[k]) for k in ('checkout_attribute', 'checkout_site_details') if k in v}
        if len({comparable_field(t, time=True) for t in times}) > 1:
            notes.append(('Checkout times differ', 'The source lists checkout at ' + ' and '.join(sorted(times)) + '. Confirm the time with the campground.'))
    if claim.predicate == 'recreation_gov_site_profile':
        attrs = {}
        for a in v.get('published_attributes', []):
            attrs.setdefault(a.get('code'), set()).add(str(a.get('value')))
        labels = {'max_num_vehicles': 'Number of vehicles', 'max_vehicle_length': 'Vehicle length',
                  'checkout_time': 'Checkout time'}
        for group in ('equipment_details', 'site_details'):
            for key, label in labels.items():
                value = v.get(group, {}).get(key)
                if value is not None and key in attrs and {comparable_field(x, key == 'checkout_time') for x in attrs[key]} != {comparable_field(value, key == 'checkout_time')}:
                    values = sorted(attrs[key] | {str(value)})
                    unit = ' feet' if key == 'max_vehicle_length' else ''
                    notes.append((f'{label}: different limits listed' if key != 'checkout_time' else 'Checkout times differ',
                                  f'The source lists {" and ".join(values)}{unit}. Confirm with the campground before booking.'))
    return notes


def site_row(reads, child):
    s = _helpers()
    model = summary(reads, child)
    profile = next((c.value for c in model['claims'] if c.subject_id == child.entity_id
                    and c.predicate == 'recreation_gov_site_profile'), {})
    number = profile.get('site') or profile.get('name')
    title = f'Campsite {number}' if number else child.name
    notes = [n[0] for c in model['claims'] for n in conflict_notes(c)]
    detail = f'Loop {profile["loop"]}' if profile.get('loop') else ''
    return {'id': child.entity_id, 'name': title, 'detail': detail,
            'warnings': notes or (['Unresolved questions — check before booking'] if model['gaps'] else []),
            'url': f'/knowledge/{child.entity_id}/'}


def row_html(row):
    s = _helpers()
    warnings = ''.join(f'<li>{s._e(w)}</li>' for w in row['warnings'])
    return (f'<li class="camp-row" id="{s._e(row["id"])}"><h2><a data-context-link href="{s._e(row["url"])}">'
            f'{s._e(row["name"])}</a></h2><p>{s._e(row["detail"])}</p>'
            + (f'<ul class="camp-warnings">{warnings}</ul>' if warnings else '') + '</li>')


def render_inventory(reads, parent, rows, site_url, page=1):
    s = _helpers()
    pages = max(1, ceil(len(rows) / PAGE_SIZE))
    visible = rows[(page-1)*PAGE_SIZE:page*PAGE_SIZE]
    pagination = ''.join(f'<a href="{camping_url(parent.entity_id,n)}"'
                         + (' aria-current="page"' if n == page else '') + f'>{n}</a>' for n in range(1,pages+1))
    body = (s.render_primary_nav() + '<main id="main" class="camp-planning">'
            '<a data-context-back hidden></a>'
            f'<p><a data-parent-link href="/knowledge/{s._e(parent.entity_id)}/">{s._e(parent.name)}</a></p>'
            '<h1>Choose a campsite</h1><p>Compare listed sites. Availability and changing conditions need checking with the campground.</p>'
            f'<form id="camp-filter" data-index="{camping_url(parent.entity_id)}index.json">'
            '<label for="camp-query">Find a campsite by name or number</label>'
            '<input id="camp-query" name="q" type="search"><button type="submit">Find campsite</button></form>'
            f'<p id="camp-count" role="status">Showing {len(visible)} of {len(rows)} campsites · Page {page} of {pages}</p>'
            f'<ul id="camp-results" class="camp-list">{"".join(row_html(r) for r in visible)}</ul>'
            f'<nav id="camp-pages" aria-label="Campsite pages">{pagination}</nav>'
            '<noscript><p>Use the page links to browse every listed campsite. Filtering needs JavaScript.</p></noscript>'
            '</main><script src="/assets/camping.js" defer></script>')
    return s._page(f'{parent.name}: campsites — Wayproof', 'Browse campsites and their published limits.',
                   site_url+camping_url(parent.entity_id,page), body,
                   '<link rel="stylesheet" href="/assets/camping.css">')


def render_camping(reads, model, site_url):
    s = _helpers()
    entity, claims, hierarchy = model['entity'], model['claims'], model['hierarchy']
    own = [c for c in claims if c.subject_id == entity.entity_id]
    profile = next((c for c in own if c.predicate in {'recreation_gov_campground_profile','recreation_gov_site_profile'}), None)
    number = (profile.value.get('site') or profile.value.get('name')) if profile and entity.kind in SITE_KINDS else None
    title = f'Campsite {number}' if number else entity.name
    body = [s.render_primary_nav(), '<main id="main" class="camp-planning">',
            '<a data-context-back hidden></a>', '<header class="page-header">',
            f'<p class="eyebrow">{"Campground" if entity.kind == "campground" else s._e(s._human_label(entity.kind))}</p>',
            f'<h1>{s._e(title)}</h1>']
    for parent in hierarchy.parents:
        body.append(f'<p class="camp-parent"><a data-context-link href="/knowledge/{parent.entity_id}/">{s._e(parent.name)}</a></p>')
    if profile:
        value = profile.value
        setting = value.get('setting', [])
        if setting:
            body.append('<p class="tagline">' + ' · '.join(s._e(str(v).replace('_',' ')) for v in setting) + '</p>')
        # Notices can contain fit claims that disagree elsewhere: show them only
        # in full details, after the visible conflict summary.
        if entity.kind not in SITE_KINDS:
            body.append(source_line(reads,profile,compact=True))
        if value.get('loop'):
            body.append(f'<p>Loop {s._e(value["loop"])}</p>')
    if profile and entity.kind in SITE_KINDS:
        value = profile.value
        amenities = next((c.value for c in own if c.predicate == 'site_amenities'), {})
        items = []
        if amenities.get('beside_restroom'): items.append('Beside a restroom')
        if amenities.get('beside_water_spigot'): items.append('Beside a water spigot')
        if amenities.get('food_locker') or any(a.get('name') == 'Food Storage Locker' for a in value.get('amenities', [])):
            items.append('Food storage locker listed')
        capacity = value.get('listed_capacity') or value.get('site_details', {}).get('max_num_people')
        if capacity: items.append(f'Listed capacity: {capacity} people')
        if items: body.append('<ul>' + ''.join(f'<li>{s._e(x)}</li>' for x in items) + '</ul>')
        body.append(source_line(reads,profile,compact=True))
    body.append('</header>')
    handled = set()
    notices = [(c, title, text) for c in own for title, text in conflict_notes(c)]
    notices.sort(key=lambda n: 'checkout' in n[1].lower())
    if notices:
        body.append('<section class="camp-notice"><h2>Check before booking</h2>')
        for c, title, text in notices:
            body.append(f'<h3>{s._e(title)}</h3><p>{s._e(text)}</p>'
                        + s._record_link('claim',c.claim_id,'Compare the published details') + source_line(reads,c))
            handled.add(c.claim_id)
        body.append('</section>')
    # Current snapshots stay dated; never compare against the build date to
    # manufacture a closing date or an assertion of current availability.
    for c in own:
        if c.predicate == 'operating_status':
            body.append('<section class="camp-notice"><h2>Check opening before you go</h2>'
                        + planning_value(c) + '<p>This is a dated listing. Confirm current opening, road access and facility operations before travel.</p>'
                        + source_line(reads,c) + '</section>')
            handled.add(c.claim_id)
    if profile and entity.kind in SITE_KINDS:
        notes = profile.value.get('notices') or profile.value.get('details') or []
        if notes:
            body.append('<section><h2>Site notes from Recreation.gov</h2><ul>'
                        + ''.join(f'<li>{s._e(note)}</li>' for note in notes) + '</ul>'
                        + source_line(reads,profile) + '</section>')
    directions = [c for c in own if c.predicate == 'directions' and isinstance(c.value,dict)]
    distances = {str(c.value.get('distance_miles',c.value.get('distance_miles_approximate'))) for c in directions}
    same_approach = bool(directions) and all(c.value.get('from') and c.value.get('road') for c in directions) and len({(c.value.get('from'), c.value.get('road'), str(c.temporal_scope)) for c in directions}) == 1
    body.append('<div class="hero-actions">')
    if hierarchy.children:
        body.append(f'<a class="button primary" data-context-link href="{camping_url(entity.entity_id)}">Browse {len(hierarchy.children)} campsites</a>')
    if profile:
        url = profile.value.get('booking_url','')
        if urlparse(url).scheme in {'https','http'}:
            body.append(f'<a class="button" href="{s._e(url)}">Check availability on Recreation.gov</a>')
    body.append('</div>')
    child_ids = {x.entity_id for x in hierarchy.children}
    links = []
    for rel in reads.relationships_for(entity.entity_id):
        if rel.predicate in {'provides_access_to','accesses','located_in','part_of','contained_by'} and rel.evidence_ids:
            other = rel.object_id if rel.subject_id == entity.entity_id else rel.subject_id
            if other not in child_ids:
                target = reads.entity(other)
                links.append(f'<li><a data-context-link href="/knowledge/{s._e(other)}/">{s._e(target.name)}</a> '
                             + s._record_link('relationship',rel.relationship_id,'Connection and source') + '</li>')
    if links:
        body.append('<section><h2>Getting there and exploring</h2><ul>' + ''.join(links) + '</ul></section>')
    before_you_go_start = len(body)
    body.append('<section><h2>Before you go</h2><ul>')
    # Gaps stay linked without expanding every attached claim into the parent.
    for gap in model['gaps']:
        related = {c.claim_id for c, _, _ in notices}
        if related.intersection(gap.related_ids):
            label = 'Unresolved source disagreement — compare the evidence'
        else:
            label = gap.question
        explanation = '' if related.intersection(gap.related_ids) else f'<p>{s._e(gap.reason)}</p>'
        body.append('<li>' + s._record_link('gap',gap.gap_id,label) + explanation + '</li>')
    rechecks = [c for c in own if c.predicate == 'pretrip_current_conditions_recheck']
    for c in rechecks:
        topics = c.value.get('topics', []) if isinstance(c.value,dict) else []
        for topic in topics:
            body.append(f'<li>Check {s._e(str(topic).replace("_", " "))} before travel.</li>')
        handled.add(c.claim_id)
    if not rechecks:
        body.append('<li>Check current opening, access and facility information before travel.</li>')
    body.append('</ul></section>')
    before_you_go = body[before_you_go_start:]
    del body[before_you_go_start:]
    groups = {}
    for c in claims:
        if c.claim_id not in handled and c.predicate not in {'recreation_gov_campsite_inventory_snapshot', 'recreation_gov_campground_profile', 'recreation_gov_site_profile'}:
            section = {'directions':'Getting there', 'facilities':'Facilities and services',
                       'food_storage':'Facilities and services', 'site_amenities':'Facilities and services',
                       'published_elevation_feet':'Routes and geography'}.get(c.predicate, s._claim_section(c.predicate))
            groups.setdefault(section, []).append(c)
    for title in ('Getting there','Requirements and current conditions','Facilities and services','Routes and geography','More planning facts'):
        if title not in groups:
            continue
        body.append(f'<section><h2>{s._e(title)}</h2>')
        if title == 'Getting there' and same_approach and len(distances) > 1:
            body.append('<p><strong>Directions differ between sources.</strong> Compare both published distances before following the directions.</p>')
        for c in groups[title]:
            # Profiles contain technical provider maps, not visitor-facing copy.
            if c.predicate == 'recreation_gov_site_profile':
                body.append('<p>The campground listing describes this individual campsite. Confirm availability and facility operations before booking.</p>' + source_line(reads,c))
                continue
            if c.predicate == 'recreation_gov_campground_profile':
                body.append(source_line(reads,c)); continue
            subject = reads.entity(c.subject_id)
            body.append(f'<article class="camp-fact"><h3>{s._e(s._human_label(c.predicate))}</h3>'
                        + (f'<p>Applies to {s._e(subject.name)}</p>' if c.subject_id != entity.entity_id else '')
                        + planning_value(c) + source_line(reads,c) + '</article>')
        body.append('</section>')
    body.extend(before_you_go)
    body.append(f'<p><a data-context-link href="/knowledge/{entity.entity_id}/facts/">All details, sources and history</a></p>'
                '</main><script src="/assets/camping.js" defer></script>')
    return s._page(f'{entity.name} — Wayproof', f'Plan a visit to {entity.name}: campsites, access, restrictions and sources.',
                   f'{site_url}/knowledge/{entity.entity_id}/', ''.join(body),
                   '<link rel="stylesheet" href="/assets/camping.css">')


def planning_value(claim):
    """Plain-language formatting for supported fields, retaining all other fields.

    This is presentation vocabulary, not destination copy or inferred knowledge.
    """
    s = _helpers()
    value = claim.value
    if not isinstance(value, dict):
        return s._human_value(value)
    v = dict(value)
    lines = []
    def take(key, render):
        if key in v:
            lines.append(render(v.pop(key)))
    if claim.predicate == 'operating_status':
        status = v.pop('status',None)
        date = v.pop('as_of',None)
        if status is not None: lines.append(f'Listed as {status}' + (f' on {date_label(date)}.' if date else '.'))
        take('opening_and_closing',lambda x:f'Opening and closing: {x}.')
        # Year-specific keys are source vocabulary, not chosen by today's date.
        for key in list(v):
            if key.startswith('published_peak_season_') and isinstance(v[key],dict):
                season=v.pop(key)
                lines.append(f'Published peak season: {date_label(season.get("starts_on", "start unknown"))} to {date_label(season.get("ends_on", "end unknown"))}.')
    elif claim.predicate == 'directions':
        road,origin=v.pop('road',None),v.pop('from',None)
        distance=v.pop('distance_miles',None)
        approx=v.pop('distance_miles_approximate',None)
        if origin and road:
            lines.append(f'From {origin}, follow {road}' + (f' for about {approx} miles.' if approx is not None else f' for {distance} miles.' if distance is not None else '.'))
        else:
            if road: lines.append(f'Road: {road}.')
            if origin: lines.append(f'From {origin}.')
            if distance is not None: lines.append(f'Distance: {distance} miles.')
            if approx is not None: lines.append(f'Approximate distance: {approx} miles.')
        take('turn',lambda x:str(x).capitalize()+'.')
    elif claim.predicate == 'facilities':
        labels={'bear_lockers':'Food storage lockers','electrical_hookups':'Electrical hookups',
                'firewood_for_sale':'Firewood for sale','flush_toilets':'Flush toilets',
                'picnic_tables':'Picnic tables','potable_water':'Drinking water'}
        for key,label in labels.items(): take(key,lambda x,label=label:f'{label}: {"listed" if x is True else "not provided" if x is False else x}.')
        lines.append('Check whether water and restrooms are operating before travel.')
    elif claim.predicate == 'fees':
        take('campsite_usd_per_night',lambda x:f'Campsite: ${x} per night.')
        take('extra_vehicle_usd_per_night',lambda x:f'Extra vehicle: ${x} per night.')
        take('access_and_senior_pass_discount',lambda x:f'Access and Senior Pass discount: {x}.')
    elif claim.predicate == 'pet_policy':
        take('leash_required',lambda x:'Keep pets on a leash.' if x is True else f'Leash requirement: {x}.')
        take('maximum_pets',lambda x:f'Up to {x} pets.')
    elif claim.predicate == 'reservation_window':
        take('maximum_advance_months',lambda x:f'Reservations open up to {x} months ahead.')
        take('maximum_stay_nights',lambda x:f'Maximum stay: {x} nights.')
        take('minimum_stay_nights',lambda x:f'Minimum stay: {x} night(s).')
        take('some_sites_first_come_first_served',lambda x:'Some sites are first come, first served.' if x is True else f'First-come sites: {x}.')
        take('some_sites_reservable',lambda x:'Some sites accept reservations.' if x is True else f'Reservable sites: {x}.')
    elif claim.predicate == 'quiet_hours':
        start,end=v.pop('starts',None),v.pop('ends',None)
        lines.append(f'Quiet hours: {start or "start unknown"}–{end or "end unknown"}.')
    elif claim.predicate == 'food_storage':
        take('active_bear_area',lambda x:'Bears are active in this area.' if x is True else f'Active bear area: {x}.')
        take('bear_box_inches',lambda x:'Food locker dimensions (inches): '+', '.join(f'{k} {n}' for k,n in x.items())+'.')
    elif claim.predicate == 'site_amenities':
        for key,label in {'beside_restroom':'Beside a restroom', 'beside_water_spigot':'Beside a water spigot',
                          'food_locker':'Food storage locker'}.items():
            take(key,lambda x,label=label:f'{label}: {"listed" if x is True else "not listed" if x is False else x}.')
        take('campfire_allowed',lambda x:f'The listing says campfires are {"allowed" if x is True else "not allowed" if x is False else x}. Check current fire restrictions before lighting a fire.')
        take('pets_allowed',lambda x:f'The listing says pets are {"allowed" if x is True else "not allowed" if x is False else x} at this site. Check campground and land-management rules.')
        take('site_class',lambda x:f'Site size: {x}.')
    elif claim.predicate == 'driveway_profile':
        take('approach',lambda x:f'Driveway entry: {x}.')
        take('length_feet',lambda x:f'Listed driveway length: {x} feet. This is not a vehicle length limit.')
        take('surface',lambda x:f'Surface: {x}.')
    elif claim.predicate == 'permitted_equipment':
        units = v.pop('units_as_published','units unknown')
        for key,label in {'rv_maximum':'RV','trailer_maximum':'Trailer','tent_maximum':'Tent'}.items():
            take(key,lambda x,label=label:f'{label}: {x} {units} in the equipment listing.')
        lines.append('Compare all published limits before deciding whether equipment fits.')
    elif claim.predicate == 'fire_restrictions':
        take('fire_and_charcoal',lambda x:f'Wood and charcoal fires: {x}.')
        take('lpg_with_shutoff',lambda x:f'Liquefied petroleum gas devices with a shutoff valve: {x}.')
        start,end=v.pop('effective_starts_on',None),v.pop('effective_ends_on',None)
        if start or end: lines.append(f'Order dates: {start or "start unknown"}–{end or "end unknown"}.')
        take('order',lambda x:f'Order: {x}.')
        take('stage',lambda x:f'Fire restriction stage: {x}.')
        # Keep any source-specific exception visible and attributed, without
        # projecting its place name onto another campground.
    content = '<ul>' + ''.join(f'<li>{s._e(x)}</li>' for x in lines) + '</ul>' if lines else ''
    return content + (s._human_value(v) if v else '')
