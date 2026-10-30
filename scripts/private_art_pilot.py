#!/usr/bin/env python3
"""Validate and stage the bounded PUBLIC-source private art museum layer.

generate(root, version) reads only its container and the three schema files. It
returns bytes and tables, never writes files, queries a network, connects to a
database, or adds records to the public museum baseline. Original source hashes
are declared evidence, not a claim that this exporter reread the original files.
"""
import csv
import hashlib
import io
import json
import math
import re
import unicodedata
import ipaddress
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit

SCOPE = 'private_art_museum_pilot'
TABLE_KEYS = {
    'private_art_observations': ('observations', 'observation_id'),
    'private_art_sources': ('sources', 'source_id'),
    'private_art_body_reviews': ('body_reviews', 'review_id'),
    'private_art_scope_notes': ('scope_notes', 'note_id'),
}
BODY_STATUSES = {
    'numeric_observations_verified', 'body_read_no_eligible_quantity_located',
    'annual_scope_not_separable', 'outside_selected_scope',
}
PRIVATE_CONTENT = re.compile(
    r'/users(?:/|\b)|/home/|/volumes/|[a-z]:[\\/]users[\\/]|file:/{2}|'
    r'drive\.google\.com|docs\.google\.com|localhost|127\.0\.0\.1|'
    r'\bcredential\w*\b|\b(?:password|passwd|secret|authorization|api[_-]?key|'
    r'access[_-]?token|refresh[_-]?token)\s*[=:]|'
    r'\bbearer\s+[a-z0-9._-]+|\bAIza[\w-]{20,}|'
    r'\bgh[pousr]_[a-z0-9]{20,}|\bsk-(?:proj-|ant-)?[a-z0-9_-]{20,}|'
    r'\bAKIA[A-Z0-9]{16}\b|-----BEGIN [A-Z ]*PRIVATE KEY-----', re.I)
SENSITIVE_QUERY_KEY = re.compile(
    r'password|passwd|secret|credential|authorization|api[-_]?key|'
    r'access[-_]?token|refresh[-_]?token|^token$', re.I)
EXCLUDED_METRIC = re.compile(
    r'財務|營收|薪資|人事|員工|人員|人力|廠商|企業委託|公司委託|商業委託|'
    r'financial|revenue|salary|personnel|employee|vendor|corporate[_ -]?commission', re.I)


class ValidationError(ValueError):
    """A candidate cannot be staged; no existing artifact was modified."""


def require(condition, code, *context):
    if not condition:
        raise ValidationError((code,) + context)


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       indent=2, allow_nan=False) + '\n').encode('utf-8')


def compact(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def _load(path):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate_json_key', key)
            result[key] = value
        return result
    def reject_number(value):
        raise ValidationError(('nonfinite_json_number', value))
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs,
                      parse_constant=reject_number)


def _resolved_schema(root):
    """Resolve only the two existing local record schemas; no remote loading."""
    allowed = {'observation.schema.json', 'body_review.schema.json'}
    def resolve(value):
        if isinstance(value, list):
            return [resolve(item) for item in value]
        if not isinstance(value, dict):
            return value
        if '$ref' in value:
            require(set(value) == {'$ref'} and value['$ref'] in allowed,
                    'unsupported_schema_reference')
            return resolve(_load(root / 'schema' / value['$ref']))
        return {key: resolve(item) for key, item in value.items()}
    return resolve(_load(root / 'schema/private_art_pilot.schema.json'))


def _public_text(value):
    """Reject hidden paths/secrets too, without printing their original value."""
    if isinstance(value, str):
        text = unicodedata.normalize('NFKC', value)
        for _ in range(3):
            decoded = unquote(text)
            if decoded == text:
                break
            text = decoded
        require(not PRIVATE_CONTENT.search(text), 'prohibited_public_content')
    elif isinstance(value, dict):
        for key, item in value.items():
            _public_text(key)
            _public_text(item)
    elif isinstance(value, list):
        for item in value:
            _public_text(item)
    elif isinstance(value, float):
        require(math.isfinite(value), 'nonfinite_number')


def _public_url(value, nullable=False):
    if value is None:
        require(nullable, 'missing_public_url')
        return
    require(isinstance(value, str) and value.strip() == value and value,
            'bad_public_url')
    _public_text(value)
    require(not re.search(r'[\s\\\x00-\x1f\x7f]', value), 'bad_public_url')
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or '').rstrip('.').lower()
        port = parsed.port
    except ValueError as error:
        raise ValidationError('bad_public_url') from error
    require(parsed.scheme in {'https', 'http'} and host and
            parsed.username is None and parsed.password is None, 'bad_public_url')
    require('.' in host or ':' in host, 'nonpublic_url_host')
    require(not host.endswith(('.local', '.localhost', '.internal', '.test', '.invalid')),
            'nonpublic_url_host')
    require(host not in {'drive.google.com', 'docs.google.com'}, 'nonpublic_url_host')
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        require(not re.fullmatch(r'[0-9.]+', host), 'ambiguous_ip_host')
    else:
        require(address.is_global, 'nonpublic_url_host')
    require(port is None or 1 <= port <= 65535, 'bad_public_url_port')
    require(not any(SENSITIVE_QUERY_KEY.search(key)
                    for key, _ in parse_qsl(parsed.query, keep_blank_values=True)),
            'credential_query')


def _ids(rows, key):
    values = [row[key] for row in rows]
    require(len(set(values)) == len(values), 'duplicate_id', key)
    for value in values:
        require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', value), 'invalid_id', key)
        require(not re.search(r'(?:^|-)(?:BASE|SUPP|FAC)-', value),
                'public_namespace_in_private_layer', key)
    return {row[key]: row for row in rows}


def _unique_strings(values, context):
    require(len(values) == len(set(values)), 'duplicate_reference', context)


def _pages(values, source, context):
    require(values == sorted(set(values)), 'pages_not_sorted_unique', context)
    if source['original_file_type'] == 'HTML':
        require(not values, 'html_cannot_have_pdf_pages', context)
    else:
        maximum = source.get('original_file_pdf_pages')
        require(type(maximum) is int and maximum > 0, 'pdf_page_bound_missing', context)
        require(all(type(page) is int and 1 <= page <= maximum for page in values),
                'pdf_page_out_of_bounds', context)


def _year_contains(observation, year):
    if observation['data_year'] is not None:
        return observation['data_year'] == year
    return observation['data_year_start'] <= year <= observation['data_year_end']


def _components(row, source_number):
    """Bound existing flexible component fields without creating new fields."""
    for key in ('source_components', 'dual_unit_quantities'):
        for component in row.get(key, []):
            require(isinstance(component, dict), 'component_not_object', key)
            allowed = ({'category_raw', 'quantity_numeric', 'quantity_raw', 'unit_raw',
                        'raw_unit', 'raw_value', 'value', 'role'} if key == 'source_components'
                       else {'quantity_numeric', 'quantity_raw', 'unit'})
            require(set(component) <= allowed, 'component_extra_field', key)
            raw_key, numeric_key = ('raw_value', 'value') if 'raw_value' in component else ('quantity_raw', 'quantity_numeric')
            require(numeric_key in component, 'component_numeric_field_missing', key)
            value = component[numeric_key]
            require(value is None or (type(value) in (int, float) and math.isfinite(value) and value >= 0),
                    'component_numeric_type', key)
            if raw_key in component:
                require(component[raw_key] is None or isinstance(component[raw_key], str),
                        'component_raw_type', key)
                require(numeric_key in component and source_number(component[raw_key]) == component[numeric_key],
                        'component_quantity_conversion', key)
    if 'derivation' not in row:
        require(row['numeric_origin'] != 'controller_derived', 'derived_components_missing')
        return
    derivation = row['derivation']
    require(set(derivation) <= {'method', 'assumption', 'components', 'formula'},
            'derivation_extra_field')
    require(row['numeric_origin'] == 'controller_derived', 'unexpected_derivation')
    parts = derivation.get('components', [])
    require(parts and isinstance(parts, list), 'derived_components_missing')
    for component in parts:
        require(isinstance(component, dict) and
                set(component) == {'category_raw', 'quantity_numeric', 'quantity_raw', 'unit_raw'},
                'derived_component_shape')
        require(isinstance(component['quantity_raw'], str) and
                type(component['quantity_numeric']) in (int, float) and
                source_number(component['quantity_raw']) is not None and
                source_number(component['quantity_raw']) == component['quantity_numeric'],
                'derived_component_quantity_conversion')
    require({part['unit_raw'] for part in parts} == {row['unit_as_reported']},
            'derived_mixed_units')
    require(sum(part['quantity_numeric'] for part in parts) == row['quantity_numeric'],
            'derived_quantity_conversion')


def _validate(data, root, version):
    # Lazy import prevents a circular module import when the public build calls us.
    from build_exports import validate_review_shape, source_number, facets, current_reviews
    try:
        validate_review_shape(data, _resolved_schema(root), SCOPE)
    except AssertionError as error:
        raise ValidationError(('schema_validation', str(error))) from error
    require(data['dataset_version'] == version and re.fullmatch(r'\d+\.\d+\.\d+', version),
            'dataset_version_mismatch')
    _public_text(data)
    organizations = _ids(data['institutions'], 'organization_id')
    sources = _ids(data['sources'], 'source_id')
    observations = _ids(data['observations'], 'observation_id')
    reviews = _ids(data['body_reviews'], 'review_id')
    _ids(data['scope_notes'], 'note_id')
    owners = {source_id: set() for source_id in sources}

    def organization(row):
        ident = row['organization_id']
        require(ident in organizations, 'organization_outside_private_container')
        if 'organization_name' in row:
            require(row['organization_name'] == organizations[ident]['organization_name'],
                    'organization_name_mismatch')
        return ident

    def reference_source(source_id, owner):
        require(source_id in sources, 'source_missing_from_private_layer')
        owners[source_id].add(owner)

    for ident, institution in organizations.items():
        require(re.fullmatch(r'PRIV-\d{3}', ident), 'private_organization_namespace')
        require(all(institution[key].strip() for key in
                    ('organization_name', 'ownership_type')), 'empty_institution_field')
        _public_url(institution['official_url'])
    for source in sources.values():
        sha = source['original_file_sha256']
        require(re.fullmatch(r'[a-f0-9]{64}', sha), 'invalid_source_sha256')
        require(source['source_id'] == 'src-' + sha[:16], 'source_id_sha_mismatch')
        _public_url(source['official_file_url'])
        _public_url(source['official_landing_url'], nullable=True)
        if source['original_file_type'] == 'PDF':
            require(type(source.get('original_file_pdf_pages')) is int and
                    source['original_file_pdf_pages'] > 0, 'pdf_page_bound_missing')
        else:
            require(source.get('original_file_pdf_pages') is None, 'html_has_pdf_page_bound')
        require(source['title'].strip() and source['rights_basis'].strip() and
                source['verified_at'].strip(), 'empty_source_evidence')
    for row in observations.values():
        owner = organization(row)
        reference_source(row['source_id'], owner)
        source = sources[row['source_id']]
        if row['data_year'] is None:
            require(row.get('year_assignment_status') == 'multi_year_not_allocated' and
                    bool(row.get('reporting_period_raw')), 'multi_year_period_missing')
            start, end = row.get('data_year_start'), row.get('data_year_end')
            require(type(start) is int and type(end) is int and 1900 <= start < end <= 2100,
                    'invalid_multi_year_period')
        else:
            require(row.get('year_assignment_status') != 'multi_year_not_allocated',
                    'multi_year_assigned_to_single_year')
            require(all(row.get(key) in (None, row['data_year']) for key in
                        ('data_year_start', 'data_year_end')), 'conflicting_single_year_period')
        if source.get('data_year') is not None:
            require(_year_contains(row, source['data_year']), 'source_observation_year_mismatch')
        if source['original_file_type'] == 'PDF':
            _pages([row['pdf_page_1_based']], source, row['observation_id'])
            _pages(row.get('additional_pdf_pages_1_based', []), source, row['observation_id'])
        else:
            require(row['pdf_page_1_based'] is None and row['printed_page'] is None and
                    not row.get('additional_pdf_pages_1_based'), 'html_observation_fake_pdf_page')
            require(isinstance(row.get('source_locator'), str) and row['source_locator'].strip(),
                    'html_observation_locator_missing')
        require(bool(row['metric_as_reported'].strip()), 'empty_metric')
        require(not EXCLUDED_METRIC.search(' '.join(row[key] for key in
                    ('metric_as_reported', 'metric_label', 'metric_class', 'subject_scope'))),
                'metric_outside_private_art_scope')
        require(row['unit_as_reported'] is not None or row['unit_status'] == 'not_stated_in_source',
                'missing_unit_status')
        for key, value in facets(row).items():
            require(row[key] == value, 'query_facet_mismatch', row['observation_id'], key)
        raw, value = row['quantity_raw'], row['quantity_numeric']
        if row['numeric_origin'] == 'source_reported':
            require(source_number(raw) == value, 'quantity_conversion', row['observation_id'])
        else:
            require(raw is None and value is not None, 'derived_quantity_origin')
        _components(row, source_number)
    for row in reviews.values():
        owner = organization(row)
        year = row['target_data_year']
        require(1900 <= year <= 2100, 'review_year_out_of_bounds')
        _unique_strings(row['source_ids'], row['review_id'])
        _unique_strings(row['observation_ids'], row['review_id'])
        if row['review_status'] in BODY_STATUSES:
            require(bool(row['source_ids']), 'body_review_without_source')
        if row['review_status'] == 'numeric_observations_verified':
            require(bool(row['observation_ids']), 'numeric_review_without_observation')
        if row['review_status'] in {'body_read_no_eligible_quantity_located', 'source_not_located_in_this_search'}:
            require(not row['observation_ids'], 'no_quantity_review_has_observation')
        for source_id in row['source_ids']:
            reference_source(source_id, owner)
            require(sources[source_id].get('data_year') in (None, year),
                    'review_source_year_mismatch')
        for observation_id in row['observation_ids']:
            require(observation_id in observations, 'review_observation_missing_from_private_layer')
            observation = observations[observation_id]
            require(observation['organization_id'] == owner and _year_contains(observation, year),
                    'review_observation_scope_year_mismatch')
            require(observation['source_id'] in row['source_ids'], 'review_observation_source_mismatch')
        if row.get('official_entry_url') is not None:
            _public_url(row['official_entry_url'])
        reviewed_by_source = {}
        for detail in row['source_page_reviews']:
            source_id = detail['source_id']
            require(source_id in row['source_ids'], 'review_page_source_mismatch')
            require(source_id not in reviewed_by_source, 'duplicate_source_page_review')
            _pages(detail['pdf_pages_1_based'], sources[source_id], row['review_id'])
            reviewed_by_source[source_id] = set(detail['pdf_pages_1_based'])
            for key in ('text_read_pdf_pages_1_based', 'image_viewed_pdf_pages_1_based'):
                pages = detail.get(key, [])
                _pages(pages, sources[source_id], row['review_id'])
                require(set(pages) <= reviewed_by_source[source_id], 'review_evidence_outside_reviewed_pages')
        require(row['reviewed_pdf_pages_1_based'] == sorted(set().union(*reviewed_by_source.values())),
                'review_page_union_mismatch')
        html_locators = set()
        for locator in row.get('source_locators', []):
            require(isinstance(locator, dict) and
                    {'source_id', 'locator'} <= set(locator) <=
                    {'source_id', 'locator', 'locator_type', 'review_scope'}, 'source_locator_shape')
            require(all(isinstance(value, str) for value in locator.values()),
                    'source_locator_field_type')
            require(locator['source_id'] in row['source_ids'] and
                    isinstance(locator['locator'], str) and locator['locator'].strip(),
                    'review_locator_source_mismatch')
            html_locators.add(locator['source_id'])
        if row['review_status'] in BODY_STATUSES:
            for source_id in row['source_ids']:
                if sources[source_id]['original_file_type'] == 'HTML':
                    require(source_id in html_locators, 'html_review_locator_missing')
                else:
                    require(bool(reviewed_by_source.get(source_id)), 'pdf_body_review_pages_missing')
            for observation_id in row['observation_ids']:
                observation = observations[observation_id]
                if sources[observation['source_id']]['original_file_type'] == 'PDF':
                    observation_pages = {observation['pdf_page_1_based']} | set(observation.get('additional_pdf_pages_1_based', []))
                    require(observation_pages <= reviewed_by_source.get(observation['source_id'], set()),
                            'review_observation_page_outside_review')
    try:
        current_reviews(data['body_reviews'])
    except AssertionError as error:
        raise ValidationError(('review_extension_invalid', str(error))) from error
    for note in data['scope_notes']:
        owner = organization(note)
        require(bool(note['note'].strip()), 'empty_scope_note')
        _unique_strings(note['source_ids'], note['note_id'])
        _unique_strings(note['observation_ids'], note['note_id'])
        for source_id in note['source_ids']:
            reference_source(source_id, owner)
        for observation_id in note['observation_ids']:
            require(observation_id in observations, 'scope_note_observation_missing')
            observation = observations[observation_id]
            require(observation['organization_id'] == owner, 'scope_note_organization_mismatch')
            require(observation['source_id'] in note['source_ids'], 'scope_note_source_mismatch')
    require(all(len(value) <= 1 for value in owners.values()), 'source_crosses_private_institutions')


def _flat(value):
    if isinstance(value, (dict, list)):
        return compact(value)
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return value


def _csv(rows):
    fields = sorted({key for row in rows for key in row}) if rows else ['dataset_scope', 'record_json']
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows({key: _flat(value) for key, value in row.items()} for row in rows)
    return buffer.getvalue().encode('utf-8-sig')


def generate(root: Path, version: str) -> dict:
    """Return deterministic outputs, private-prefixed tables and a bounded summary.

    No mutation occurs, including on invalid input. Empty arrays are supported;
    an absent input file is an error, never a silently invented empty dataset.
    """
    root = Path(root)
    container_path = root / 'data/private_art_pilot.json'
    data = _load(container_path)
    _validate(data, root, version)
    tables, outputs = {}, {}
    for name, (key, identity) in TABLE_KEYS.items():
        rows = [dict(row, dataset_scope=SCOPE, record_json=compact(row))
                for row in sorted(data[key], key=lambda row: row[identity])]
        tables[name] = rows
        outputs['data/' + name + '.csv'] = _csv(rows)
        outputs['data/' + name + '.jsonl'] = ''.join(compact(row) + '\n' for row in rows).encode('utf-8')
    summary = {
        'schema_version': data['schema_version'], 'dataset_version': version,
        'dataset_scope': SCOPE, 'public_baseline_eligible': False,
        'automatic_numeric_aggregation_allowed': False,
        'public_private_denominators_separate': True,
        'national_repaired_object_total': None,
        'national_inference_allowed': False,
        'institution_records': len(data['institutions']),
        'observation_records': len(data['observations']),
        'source_records': len(data['sources']),
        'body_review_records': len(data['body_reviews']),
        'scope_note_records': len(data['scope_notes']),
        'observation_record_kinds': dict(sorted(Counter(row['record_kind'] for row in data['observations']).items())),
        'source_types': dict(sorted(Counter(row['original_file_type'] for row in data['sources']).items())),
        'query_facets_reproduced': True,
        'unknown_values_are_not_zero': True,
        'source_original_bytes_revalidated_by_exporter': False,
        'container_sha256': hashlib.sha256(container_path.read_bytes()).hexdigest(),
        'source_versions': [
            {key: source[key] for key in ('source_id', 'original_file_sha256', 'original_file_bytes', 'original_file_type')}
            for source in sorted(data['sources'], key=lambda row: row['source_id'])
        ],
        'limits': [
            '私立館公開來源試作，不是使用者私人台帳；不讀取私人收藏、財務、人員或廠商資料。',
            '不列入公立71館與426館年格，不跨館加總，不推論全國修護量。',
            '原詞、原數字、完成狀態與範圍分歧保留；範圍註記不核實包含關係，也不改成年量。',
            'SHA與來源ID閉合檢查不等同重新下載或人工二校；只在所列來源、頁段與年份內解讀。',
        ],
    }
    outputs['metadata/private_art_pilot_build.json'] = encode(summary)
    return {'outputs': outputs, 'tables': tables, 'summary': summary}
