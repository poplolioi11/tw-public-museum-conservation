#!/usr/bin/env python3
"""Validate and export a separate official general preservation-work text layer.

Only the declared public JSON and existing public source metadata are read.  The
module never reads originals, private ledgers, paths, or network resources.
``build(root, facts)`` returns three deterministic output byte strings without
changing main observations, quantities, SQLite, or coverage denominators.

Text privacy and faithful paraphrase still require manual source review.  The
patterns below reject obvious prohibited content; they cannot identify every
person, vendor, facility detail, unsupported inference, or semantic mistake.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
INPUT = 'data/preservation_texts.json'
SCHEMA = 'schema/preservation-text.schema.json'
OUTPUTS = ('data/preservation_texts.csv', 'data/preservation_texts.jsonl',
           'metadata/preservation_texts_build.json')
# This exact official museum host was separately source-reviewed for this layer.
# Do not treat an arbitrary .museum domain as official.
REVIEWED_OFFICIAL_HOSTS = {'www.tnam.museum'}
if not __debug__:
    raise SystemExit('Validation requires normal Python; optimized mode is unsupported.')


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def digest(body):
    return hashlib.sha256(body).hexdigest()


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _shape(value, schema, path='$'):
    """Enforce the deliberately bounded JSON Schema subset used by this layer."""
    supported = {'$schema', 'title', 'description', 'type', 'properties', 'required',
                 'additionalProperties', 'items', 'minimum', 'maximum', 'enum',
                 'const', 'minLength', 'maxLength'}
    _require(not set(schema) - supported, path + ': unsupported schema keyword')
    types = {'object': lambda v: isinstance(v, dict), 'array': lambda v: isinstance(v, list),
             'string': lambda v: isinstance(v, str),
             'integer': lambda v: isinstance(v, int) and not isinstance(v, bool),
             'boolean': lambda v: isinstance(v, bool), 'null': lambda v: v is None}
    if 'type' in schema:
        allowed = schema['type'] if isinstance(schema['type'], list) else [schema['type']]
        _require(all(t in types for t in allowed), path + ': unsupported schema type')
        _require(any(types[t](value) for t in allowed), path + ': wrong type')
    if 'const' in schema:
        _require(type(value) is type(schema['const']) and value == schema['const'], path + ': wrong constant')
    if 'enum' in schema:
        _require(value in schema['enum'], path + ': outside enum')
    for key, compare in [('minimum', lambda v, b: v >= b), ('maximum', lambda v, b: v <= b)]:
        if key in schema and value is not None:
            _require(compare(value, schema[key]), path + ': outside bound')
    if isinstance(value, str):
        if 'minLength' in schema:
            _require(len(value) >= schema['minLength'], path + ': string too short')
        if 'maxLength' in schema:
            _require(len(value) <= schema['maxLength'], path + ': string too long')
    if isinstance(value, dict):
        props = schema.get('properties', {})
        _require(set(schema.get('required', [])) <= value.keys(), path + ': required field missing')
        if schema.get('additionalProperties') is False:
            _require(set(value) <= props.keys(), path + ': extra field')
        for key, item in value.items():
            if key in props:
                _shape(item, props[key], path + '/' + key)
    if isinstance(value, list) and 'items' in schema:
        for index, item in enumerate(value):
            _shape(item, schema['items'], path + '/' + str(index))


def _public_text(value, where):
    _require(not re.search(r'/Users/|file://|drive\.google\.com|localhost|127\.0\.0\.1|'
                          r'private-[a-z]+-|controller_[A-Z_]+|'
                          r'AIza[0-9A-Za-z_-]{20,}|sk-[0-9A-Za-z_-]{20,}', value),
             where + ': private path, identifier, or credential pattern')
    _require(not re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', value), where + ': email address')


def _official_url(value):
    _require(isinstance(value, str), 'source: official URL missing')
    p = urlparse(value)
    _require(p.scheme == 'https' and p.hostname and not p.username and not p.password,
             'source: invalid official URL')
    _public_text(value, 'source URL')
    _require(p.hostname.endswith(('.gov.tw', '.edu.tw')) or p.hostname in REVIEWED_OFFICIAL_HOSTS,
             'source: non-official domain')


def validate(root, facts):
    """Return validated input, source-enriched rows, source map and input bytes."""
    root = Path(root)
    body = (root / INPUT).read_bytes()
    data = json.loads(body)
    _shape(data, json.loads((root / SCHEMA).read_text()))
    _require(data['dataset_version'] == facts['dataset_version'], 'dataset version mismatch')
    _require(re.fullmatch(r'\d+\.\d+\.\d+', data['dataset_version']), 'invalid dataset version')
    _require(data['scope_note'].strip(), 'blank layer scope note')
    _public_text(data['scope_note'], 'layer scope')
    sources = {s['source_id']: s for s in facts['sources']}
    _require(len(sources) == len(facts['sources']), 'duplicate public source ID')
    known_orgs = {}
    for row in facts['observations'] + facts.get('body_reviews', []):
        known_orgs.setdefault(row['organization_id'], set()).add(row['organization_name'])
    ids, cells, rows, used = set(), set(), [], {}
    for row in data['records']:
        ident = row['text_id']
        _require(re.fullmatch(r'[A-Z][A-Za-z0-9_-]{2,95}', ident), 'invalid public text ID')
        _require(ident not in ids, 'duplicate text ID')
        ids.add(ident)
        for key, value in row.items():
            if isinstance(value, str):
                _require(value.strip(), ident + '/' + key + ': blank string')
                _public_text(value, ident + '/' + key)
        _require(row['organization_name'] in known_orgs.get(row['organization_id'], set()),
                 ident + ': organization absent from public facts')
        # Only an intentionally reviewed paraphrase belongs in this field.
        statement = row['statement']
        _require(not re.search(r'\d|[零〇一二三四五六七八九十百千萬億兩]+\s*(?:人|位|名|員|件|筆|次|組|元|圓)', statement),
                 ident + ': statement must not introduce a quantity')
        _require(not re.search(r'經費|預算|決算|採購|廠商|金額|財務|公司|企業|NT\$|USD|TWD', statement, re.I),
                 ident + ': financial, vendor, or procurement statement')
        _require(not re.search(r'庫位|平面圖|警衛|監視器|攝影機|門禁|警報|設備配置|防護缺口|監視死角|感測器位置', statement),
                 ident + ': facility or security-detail statement')
        if row['period_basis'] in {'report_context', 'undated'}:
            _require(re.search(r'未知|未明|未載|未單列|未另列|無法確定|不明', row['period_as_reported']),
                     ident + ': context or undated period must preserve uncertainty')
        source = sources.get(row['source_id'])
        _require(source is not None, ident + ': unknown source ID')
        h = source.get('original_file_sha256')
        _require(isinstance(h, str) and re.fullmatch(r'[0-9a-f]{64}', h), ident + ': source hash missing')
        _require(source['source_id'] == 'src-' + h[:16], ident + ': source ID/hash mismatch')
        _require(type(source.get('original_file_bytes')) is int and source['original_file_bytes'] > 0,
                 ident + ': source byte count missing')
        kind = source.get('original_file_type')
        if kind == 'PDF':
            page = row['pdf_page_1_based']
            count = source.get('original_file_pdf_pages')
            _require(type(page) is int and type(count) is int and 1 <= page <= count,
                     ident + ': PDF page outside verified source bounds')
        elif kind == 'HTML':
            _require(row['pdf_page_1_based'] is None and row['printed_page'] is None,
                     ident + ': HTML must not acquire PDF or printed pages')
        else:
            raise ValueError(ident + ': unsupported original source type')
        _official_url(source.get('official_file_url'))
        _public_text(source['title'], ident + '/source title')
        cell = (row['source_id'], row['pdf_page_1_based'], row['source_locator'], row['text_category'])
        _require(cell not in cells, ident + ': duplicate source text cell')
        cells.add(cell)
        extra = {'source_title': source['title'], 'official_file_url': source['official_file_url'],
                 'original_file_sha256': h}
        rows.append(dict(row, **extra))
        used[source['source_id']] = {'source_id': source['source_id'], **extra,
            'original_file_type': kind, 'original_file_bytes': source['original_file_bytes'],
            'original_file_pdf_pages': source.get('original_file_pdf_pages')}
    return data, rows, used, body


def build(root, facts):
    """Return only three generated output byte strings; mutate no inputs."""
    data, rows, sources, body = validate(root, facts)
    # Stable columns also make an intentionally empty future layer unambiguous.
    schema = json.loads((Path(root) / SCHEMA).read_text())
    columns = sorted(set(schema['properties']['records']['items']['properties']) |
                     {'source_title', 'official_file_url', 'original_file_sha256'})
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=columns, lineterminator='\n')
    writer.writeheader()
    writer.writerows({k: '' if v is None else str(v).lower() if isinstance(v, bool) else v
                     for k, v in row.items()} for row in rows)
    metadata = {'schema_version': data['schema_version'], 'dataset_version': data['dataset_version'],
        'input_file': INPUT, 'input_sha256': digest(body), 'input_bytes': len(body),
        'record_count': len(rows), 'source_version_count': len(sources), 'scope_note': data['scope_note'],
        'denominator_role': 'separate_texts_excluded_from_main_observations_and_coverage',
        'measure_status': 'text_only', 'numeric_quantity_eligible': False,
        'annual_quantity_eligible': False, 'default_aggregation_allowed': False,
        'cross_museum_comparable': False,
        'category_counts': {c: sum(r['text_category'] == c for r in rows)
                            for c in sorted({r['text_category'] for r in rows})},
        'period_basis_counts': {b: sum(r['period_basis'] == b for r in rows)
                                for b in sorted({r['period_basis'] for r in rows})},
        'sources': [sources[k] for k in sorted(sources)],
        'validation_limits': ['Structural and obvious-pattern checks do not replace source review, '
                              'privacy review, or faithful-paraphrase assessment.']}
    return {OUTPUTS[0]: stream.getvalue().encode('utf-8-sig'),
        OUTPUTS[1]: ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                            for r in rows).encode(), OUTPUTS[2]: encode(metadata)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    modes = p.add_mutually_exclusive_group(required=True)
    modes.add_argument('--write', action='store_true')
    modes.add_argument('--check', action='store_true')
    p.add_argument('--root', type=Path, default=ROOT)
    a = p.parse_args()
    outputs = build(a.root, json.loads((a.root / 'data/facts.json').read_text()))
    for relative, body in outputs.items():
        path = a.root / relative
        if a.check:
            _require(path.exists() and path.read_bytes() == body, 'generated output mismatch: ' + relative)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
    print(json.dumps({'status': 'pass', 'mode': 'check' if a.check else 'write',
                      'records': json.loads(outputs[OUTPUTS[2]])['record_count'], 'outputs': list(outputs)}))


if __name__ == '__main__':
    main()
