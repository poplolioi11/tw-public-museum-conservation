#!/usr/bin/env python3
"""Validate a separate public environmental-operation statistics supplement.

The supplement never contributes to the main observation or coverage denominators.
Only existing public source metadata is joined; this module reads no originals,
private ledgers, network resources, or local source paths. ``build(root, facts)``
returns deterministic export bytes for the caller's normal manifest/check flow.
Run with --write or --check to manage only these three generated outputs.
"""
import argparse
import csv
from datetime import date
import hashlib
import io
import json
from pathlib import Path
import re
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
INPUT = 'data/preservation_statistics.json'
SCHEMA = 'schema/preservation-statistics.schema.json'
OUTPUTS = (
    'data/preservation_statistics.csv',
    'data/preservation_statistics.jsonl',
    'metadata/preservation_statistics.json',
)
if not __debug__:
    raise SystemExit('Validation requires normal Python; optimized mode is not supported.')


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def digest(body):
    return hashlib.sha256(body).hexdigest()


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _shape(value, schema, path='$'):
    """Validate the deliberately small JSON Schema subset used by this module."""
    supported = {'$schema', 'title', 'description', 'type', 'properties', 'required',
                 'additionalProperties', 'items', 'minimum', 'maximum', 'enum', 'const'}
    _require(not set(schema) - supported, f'{path}: unsupported schema keyword')
    kinds = {
        'object': lambda x: isinstance(x, dict),
        'array': lambda x: isinstance(x, list),
        'string': lambda x: isinstance(x, str),
        'integer': lambda x: isinstance(x, int) and not isinstance(x, bool),
        'boolean': lambda x: isinstance(x, bool),
        'null': lambda x: x is None,
    }
    if 'type' in schema:
        types = schema['type'] if isinstance(schema['type'], list) else [schema['type']]
        _require(all(t in kinds for t in types), f'{path}: unsupported schema type')
        _require(any(kinds[t](value) for t in types), f'{path}: wrong type')
    if 'enum' in schema:
        _require(value in schema['enum'], f'{path}: value outside enum')
    if 'const' in schema:
        _require(value == schema['const'] and type(value) is type(schema['const']),
                 f'{path}: wrong constant')
    for key, compare in [('minimum', lambda x, y: x >= y), ('maximum', lambda x, y: x <= y)]:
        if key in schema and value is not None:
            _require(compare(value, schema[key]), f'{path}: outside bound')
    if isinstance(value, dict):
        properties = schema.get('properties', {})
        _require(set(schema.get('required', [])) <= value.keys(), f'{path}: required field missing')
        if schema.get('additionalProperties') is False:
            _require(set(value) <= properties.keys(), f'{path}: extra field')
        for key, item in value.items():
            if key in properties:
                _shape(item, properties[key], path + '/' + key)
    if isinstance(value, list) and 'items' in schema:
        for index, item in enumerate(value):
            _shape(item, schema['items'], path + '/' + str(index))


def _public_text(value, where):
    _require(not re.search(r'/Users/|file://|drive\.google\.com|localhost|127\.0\.0\.1|'
                          r'private-[a-z]+-|controller_[A-Z_]+|'
                          r'AIza[0-9A-Za-z_-]{20,}|sk-[0-9A-Za-z_-]{20,}', value),
             f'{where}: private path, identifier, or credential pattern')
    _require(not re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', value), f'{where}: email address')


def _official_url(value):
    _require(isinstance(value, str), 'source: missing official URL')
    parts = urlparse(value)
    _require(parts.scheme == 'https' and parts.hostname and not parts.username and not parts.password,
             'source: invalid official URL')
    _public_text(value, 'source URL')
    # This public supplement is limited to existing Taiwanese official PDF sources.
    _require(parts.hostname.endswith('.gov.tw'), 'source: non-government domain')


def validate(root, facts):
    """Return validated canonical input and source-enriched export records."""
    body = (root / INPUT).read_bytes()
    data = json.loads(body)
    schema = json.loads((root / SCHEMA).read_text())
    _shape(data, schema)
    _require(data['dataset_version'] == facts['dataset_version'], 'dataset version mismatch')
    _require(re.fullmatch(r'\d+\.\d+\.\d+', data['dataset_version']), 'invalid dataset version')
    _require(data['scope_note'].strip(), 'empty supplement scope note')
    _public_text(data['scope_note'], 'supplement scope')
    sources = {s['source_id']: s for s in facts['sources']}
    _require(len(sources) == len(facts['sources']), 'duplicate public source ID')
    known_orgs = {}
    for observation in facts['observations']:
        known_orgs.setdefault(observation['organization_id'], set()).add(observation['organization_name'])
    seen_ids, seen_cells, enriched, used_sources = set(), set(), [], {}
    for row in data['records']:
        record_id = row['statistics_id']
        _require(re.fullmatch(r'[A-Z][A-Za-z0-9_-]{2,95}', record_id), 'invalid public statistics ID')
        _require(record_id not in seen_ids, 'duplicate statistics ID')
        seen_ids.add(record_id)
        for key, value in row.items():
            if isinstance(value, str):
                _public_text(value, record_id + '/' + key)
                _require(value.strip(), record_id + '/' + key + ': blank string')
        _require(row['organization_name'] in known_orgs.get(row['organization_id'], set()),
                 record_id + ': organization absent from main public facts')
        _require(re.fullmatch(r'(?:0|[1-9][0-9]*|[1-9][0-9]{0,2}(?:,[0-9]{3})+)', row['quantity_raw']),
                 record_id + ': quantity must be an exact source integer string')
        _require(int(row['quantity_raw'].replace(',', '')) == row['quantity_numeric'],
                 record_id + ': quantity raw/numeric mismatch')
        _require(not re.search(r'經費|預算|決算金額|採購|廠商|金額|財務|(?:新臺|新台|美)幣|元|圓|NT\$|USD|TWD',
                               row['metric_as_reported'] + row['unit_as_reported'], re.I),
                 record_id + ': financial or procurement metric')
        _require(len(row['period_evidence']) <= 180, record_id + ': period evidence too long')
        kind = row['period_kind']
        if kind == 'report_year_table':
            _require(row['period_year'] == row['report_year'], record_id + ': year context mismatch')
        elif kind == 'report_year_context':
            _require(row['period_year'] is None and row['period_start'] is None and row['period_end'] is None,
                     record_id + ': report context must not infer observation dates')
        elif kind == 'up_to_end_start_unspecified':
            _require(row['period_year'] is None and row['period_start'] is None and row['period_end'] is not None,
                     record_id + ': unknown-start period must not become annual')
        elif kind == 'after_installation_end_unspecified':
            _require(all(row[k] is None for k in ['period_year', 'period_start', 'period_end']),
                     record_id + ': after-installation period has no inferred dates')
        for field in ['period_start', 'period_end']:
            if row[field] is not None:
                try:
                    _require(date.fromisoformat(row[field]).isoformat() == row[field], record_id + ': non-canonical date')
                except (TypeError, ValueError):
                    raise ValueError(record_id + ': invalid ISO date') from None
        if row['period_start'] is not None and row['period_end'] is not None:
            _require(row['period_start'] <= row['period_end'], record_id + ': reversed period')
        source = sources.get(row['source_id'])
        _require(source is not None, record_id + ': unknown source ID')
        _require(source['original_file_type'] == 'PDF', record_id + ': source is not a PDF')
        _require(re.fullmatch(r'[0-9a-f]{64}', source['original_file_sha256']), record_id + ': source hash missing')
        _require(source['source_id'] == 'src-' + source['original_file_sha256'][:16], record_id + ': source ID/hash mismatch')
        _require(isinstance(source['original_file_bytes'], int) and source['original_file_bytes'] > 0,
                 record_id + ': source byte count missing')
        _require(1 <= row['pdf_page_1_based'] <= source['original_file_pdf_pages'], record_id + ': page outside source')
        _official_url(source['official_file_url'])
        for key in ['title', 'official_file_url']:
            _public_text(source[key], record_id + '/source/' + key)
        cell = (row['source_id'], row['pdf_page_1_based'], row['source_locator'])
        _require(cell not in seen_cells, record_id + ': duplicate source cell')
        seen_cells.add(cell)
        extra = {
            'source_title': source['title'],
            'official_file_url': source['official_file_url'],
            'original_file_sha256': source['original_file_sha256'],
        }
        enriched.append(dict(row, **extra))
        used_sources[source['source_id']] = {
            'source_id': source['source_id'], **extra,
            'original_file_bytes': source['original_file_bytes'],
            'original_file_pdf_pages': source['original_file_pdf_pages'],
        }
    return data, enriched, used_sources, body


def build(root, facts):
    """Return three output paths and bytes; do not mutate files or main facts."""
    root = Path(root)
    data, rows, sources, body = validate(root, facts)
    columns = sorted({key for row in rows for key in row})
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=columns, lineterminator='\n')
    writer.writeheader()
    writer.writerows({key: '' if value is None else str(value).lower() if isinstance(value, bool) else value
                     for key, value in row.items()} for row in rows)
    metadata = {
        'schema_version': data['schema_version'], 'dataset_version': data['dataset_version'],
        'input_file': INPUT, 'input_sha256': digest(body), 'input_bytes': len(body),
        'record_count': len(rows), 'source_version_count': len(sources),
        'scope_note': data['scope_note'],
        'denominator_role': 'separate_supplement_excluded_from_main_observations_and_coverage',
        'default_aggregation_allowed': False, 'cross_museum_comparable': False,
        'year_on_year_ready': False, 'unique_object_count_verified': False,
        'period_kind_counts': {kind: sum(row['period_kind'] == kind for row in rows)
                               for kind in sorted({row['period_kind'] for row in rows})},
        'units_as_reported': sorted({row['unit_as_reported'] for row in rows}),
        'sources': [sources[key] for key in sorted(sources)],
    }
    return {
        OUTPUTS[0]: stream.getvalue().encode('utf-8-sig'),
        OUTPUTS[1]: ''.join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                            for row in rows).encode(),
        OUTPUTS[2]: encode(metadata),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--write', action='store_true')
    modes.add_argument('--check', action='store_true')
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    facts = json.loads((args.root / 'data/facts.json').read_text())
    outputs = build(args.root, facts)
    for relative, body in outputs.items():
        path = args.root / relative
        if args.check:
            _require(path.exists() and path.read_bytes() == body, 'generated output mismatch: ' + relative)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
    print(json.dumps({'status': 'pass', 'mode': 'check' if args.check else 'write',
                      'records': json.loads(outputs[OUTPUTS[2]])['record_count'],
                      'outputs': list(outputs)}))


if __name__ == '__main__':
    main()
