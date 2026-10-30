#!/usr/bin/env python3
"""Project reviewed relation/evidence notes without inferring object relationships.

Only the standard library is used. The supplied public relation dictionaries are
retained verbatim as typed JSON values; no original source is read by this code.
"""
from pathlib import Path
from collections import Counter
import argparse
import copy
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
RULE_VERSION = '1.0'
SINGLE_ROLES = ('parent', 'parent_observation_id', 'observation_id',
                'from_observation_id', 'to_existing_observation_id', 'larger_scope',
                'completion_subset', 'treatment_record', 'completed_record')
MULTIPLE_ROLES = ('children', 'candidate_child_ids', 'observation_ids',
                  'existing_release_observation_ids')
STRING_FIELDS = ('type', 'relation_type', 'relation_id', 'note',
                 'interpretation_note', 'relationship_evidence', 'unit_warning',
                 'warning', 'printed_page', 'reporting_period_raw', 'source_id')
BOOLEAN_FIELDS = ('relationship_verified', 'not_additive_together',
                  'independent_object_subset_verified', 'source_components_in_parent')
INTEGER_FIELDS = ('data_year', 'pdf_page')
INTEGER_LIST_FIELDS = ('data_years', 'pdf_pages_1_based')
ALLOWED_FIELDS = set(SINGLE_ROLES + MULTIPLE_ROLES + STRING_FIELDS + BOOLEAN_FIELDS
                     + INTEGER_FIELDS + INTEGER_LIST_FIELDS)


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_rules(rules):
    require(isinstance(rules, dict) and set(rules) == {
        'rule_version', 'input_manifest', 'category_labels', 'projection_kind_labels',
        'type_rules', 'verification_policy', 'limits'}, 'relation_rules_fields')
    require(rules['rule_version'] == RULE_VERSION, 'relation_rule_version')
    manifest = rules['input_manifest']
    require(isinstance(manifest, dict) and set(manifest) == {
        'source', 'audit_baseline_dataset_version', 'reviewed_relation_count',
        'relations_sha256', 'digest_algorithm'}, 'relation_manifest_fields')
    require(manifest['source'] == 'data/facts.json#relations' and
            manifest['digest_algorithm'] == 'sha256-canonical-json-utf8-ordered-relations-v1',
            'relation_manifest_source_or_algorithm')
    require(type(manifest['reviewed_relation_count']) is int and
            manifest['reviewed_relation_count'] > 0, 'relation_manifest_count')
    h = manifest['relations_sha256']
    require(isinstance(h, str) and len(h) == 64 and
            all(c in '0123456789abcdef' for c in h), 'relation_manifest_sha256')
    require(isinstance(rules['category_labels'], dict) and rules['category_labels'] and
            isinstance(rules['projection_kind_labels'], dict) and rules['projection_kind_labels'],
            'relation_rule_vocabularies')
    mapped = {}
    require(isinstance(rules['type_rules'], list), 'relation_type_rules_array')
    for item in rules['type_rules']:
        require(isinstance(item, dict) and set(item) == {
            'relation_type_original', 'category', 'projection_kind'}, 'relation_type_rule_fields')
        raw = item['relation_type_original']
        require(isinstance(raw, str) and raw and raw not in mapped, 'relation_type_rule_duplicate')
        require(item['category'] in rules['category_labels'] and
                item['projection_kind'] in rules['projection_kind_labels'], 'relation_type_rule_vocabulary')
        mapped[raw] = item
    return mapped


def validate_relation(original, known_observations, known_sources, mapped):
    require(isinstance(original, dict) and not set(original) - ALLOWED_FIELDS,
            'relation_unknown_original_field')
    keys = [k for k in ('type', 'relation_type') if k in original]
    require(len(keys) == 1, 'relation_type_key_ambiguous_or_missing')
    type_key = keys[0]
    raw = original[type_key]
    require(isinstance(raw, str) and raw in mapped, 'relation_type_unreviewed')
    for key in STRING_FIELDS + SINGLE_ROLES:
        if key in original:
            require(isinstance(original[key], str) and original[key], 'relation_string_field_' + key)
    for key in BOOLEAN_FIELDS:
        if key in original:
            require(type(original[key]) is bool, 'relation_boolean_field_' + key)
    for key in INTEGER_FIELDS:
        if key in original:
            require(type(original[key]) is int and original[key] > 0, 'relation_integer_field_' + key)
    for key in INTEGER_LIST_FIELDS:
        if key in original:
            require(isinstance(original[key], list) and
                    all(type(n) is int and n > 0 for n in original[key]), 'relation_integer_array_' + key)
    roles = []
    for key in SINGLE_ROLES + MULTIPLE_ROLES:
        if key not in original:
            continue
        if key in SINGLE_ROLES:
            values = [original[key]]
            cardinality = 'single'
        else:
            values = original[key]
            require(isinstance(values, list) and values and
                    all(isinstance(v, str) and v for v in values), 'relation_role_array_' + key)
            cardinality = 'multiple'
        require(set(values) <= known_observations.keys(), 'relation_unknown_observation_id_' + key)
        roles.append({'role': key, 'cardinality': cardinality, 'observation_ids': list(values)})
    require(roles, 'relation_without_observation_reference')
    if 'source_id' in original:
        require(original['source_id'] in known_sources, 'relation_unknown_explicit_source')
    return type_key, mapped[raw], roles


def project(facts, rules):
    mapped = validate_rules(rules)
    require(isinstance(facts, dict) and isinstance(facts.get('relations'), list), 'relation_facts_shape')
    originals = facts['relations']
    observations = {o['observation_id']: o for o in facts['observations']}
    sources = {s['source_id'] for s in facts['sources']}
    require(len(observations) == len(facts['observations']) and
            len(sources) == len(facts['sources']), 'relation_duplicate_source_or_observation_id')
    require(all(o['source_id'] in sources for o in observations.values()), 'relation_observation_source_closure')
    rows = []
    for ordinal, original in enumerate(originals, 1):
        type_key, mapping, roles = validate_relation(original, observations, sources, mapped)
        ids = sorted({i for role in roles for i in role['observation_ids']})
        source_ids = {observations[i]['source_id'] for i in ids}
        if 'source_id' in original:
            source_ids.add(original['source_id'])
        verification = original.get('relationship_verified')
        state = ('not_stated_in_original' if verification is None else
                 'asserted_true_in_original' if verification else 'asserted_false_in_original')
        row = {
            'projection_id': f'relation-{ordinal:04d}-{digest(original)[:12]}',
            'source_relation_ordinal_1_based': ordinal,
            'source_relation_sha256': digest(original),
            'relation_id_original': original.get('relation_id'),
            'relation_type_field_original': type_key,
            'relation_type_original': original[type_key],
            'category': mapping['category'], 'projection_kind': mapping['projection_kind'],
            'reference_roles': roles, 'observation_ids': ids,
            'source_ids': sorted(source_ids),
            'explicit_source_id_original': original.get('source_id'),
            'relationship_verified_original': verification,
            'relationship_verification_state': state,
            'not_additive_together_original': original.get('not_additive_together'),
            'original_relation': copy.deepcopy(original),
            'aggregation_allowed': False, 'unit_conversion_allowed': False,
            'unique_object_inference_allowed': False,
            'new_official_relation_verification_performed': False,
            'relation_projection_rule_version': RULE_VERSION,
        }
        rows.append(row)
    manifest = rules['input_manifest']
    require(len(originals) == manifest['reviewed_relation_count'] and
            digest(originals) == manifest['relations_sha256'], 'relation_input_not_reviewed')
    require(set(mapped) == {r['relation_type_original'] for r in rows}, 'relation_unused_or_missing_type_rule')
    require([r['original_relation'] for r in rows] == originals, 'relation_original_roundtrip')
    return rows


def generate(facts, root=ROOT):
    root = Path(root)
    rules = read(root / 'metadata/relation_projection_rules.json')
    rows = project(facts, rules)
    # This validates the actual supported schema subset, not general JSON Schema.
    from build_exports import validate_review_shape
    schema = read(root / 'schema/relation_projection.schema.json')
    for row in rows:
        validate_review_shape(row, schema, row['projection_id'])
    counts = Counter(r['category'] for r in rows)
    verification = Counter(r['relationship_verification_state'] for r in rows)
    lines = ['# 原關係與證據註記的機讀附表\n',
             f'版本v{facts["dataset_version"]}；逐列保留{len(rows)}則原關係／證據註記，不合併、不去重、不改原值。\n',
             '這是既有公開註記的分類與參照附表，不是新的官方原件核讀、物件去重或關係認證。分類只能協助查找，不能授予相加、換算、跨年配分或獨特物件推定資格。\n',
             '## 如何解讀\n',
             '- source_relation_ordinal_1_based是原relations陣列的1起算位置；source_relation_sha256核對該原字典的canonical JSON。原字典完整保留在original_relation。',
             '- reference_roles保留每一原參照欄及其順序；observation_ids只供參照聯集，不是物件集合。source_ids來自被參照觀測與原明列來源，不是已新讀來源清單。',
             '- relationship_verified_original僅照錄原布林值，未列時為null；false只表示原註記沒有核實該關係，不是已證明沒有關係。true也不是本版重新驗證。',
             '- not_additive_together_original只照錄原值；未列時null不代表可相加。所有投影列仍固定不授予加總、量詞換算或獨特物件推定資格。',
             '- 續頁定位、來源構成脈絡與計量提醒，不自動當成兩筆物件之間的包含關係。原分類名稱含includes、same、completed等字樣，不能替代原件證據或補出未列的verified旗標。\n',
             '## 分類計數（註記列，不是館年或文物量）\n',
             '|分類|註記列數|\n|---|---:|']
    lines += [f'|{label}|{counts[key]}|' for key, label in rules['category_labels'].items()]
    lines += ['\n## 原關係核實旗標\n', '|原旗標狀態|列數|\n|---|---:|',
              f'|原列true|{verification["asserted_true_in_original"]}|',
              f'|原列false|{verification["asserted_false_in_original"]}|',
              f'|原未列，保留null|{verification["not_stated_in_original"]}|',
              '\n原資料見[data/facts.json](../data/facts.json)的relations；完整投影見[data/relation_projection.json](../data/relation_projection.json)，分類規則見[relation_projection_rules.json](../metadata/relation_projection_rules.json)。\n']
    outputs = {'data/relation_projection.json': encode(rows),
               'docs/RELATIONS.md': ('\n'.join(lines) + '\n').encode()}
    build = {'schema_version': '1.0', 'dataset_version': facts['dataset_version'],
             'relation_projection_rule_version': RULE_VERSION,
             'records': len(rows), 'category_counts': dict(counts),
             'original_verification_state_counts': dict(verification),
             'source_relations_sha256': digest(facts['relations']),
             'input_sha256': {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                              for name in ['metadata/relation_projection_rules.json',
                                           'schema/relation_projection.schema.json',
                                           'scripts/relation_projection.py']},
             'original_relations_mutated': False,
             'quantities_summed_or_converted': False,
             'new_original_read_claimed': False,
             'new_official_relation_verification_performed': False}
    outputs['metadata/relation_projection_build.json'] = encode(build)
    return {'rows': rows, 'outputs': outputs, 'summary': build}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--facts', type=Path, default=ROOT / 'data/facts.json')
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--output-dir', type=Path,
                   help='optional external preview root; canonical exports use build_exports')
    p.add_argument('--check', action='store_true',
                   help='validate inputs; with output-dir also compare generated bytes')
    args = p.parse_args()
    result = generate(read(args.facts), args.root)
    if args.output_dir is not None:
        require(args.output_dir.resolve() != args.root.resolve(), 'relation_cli_canonical_write_forbidden')
        for name, body in result['outputs'].items():
            target = args.output_dir / name
            if args.check:
                require(target.is_file() and target.read_bytes() == body, 'relation_preview_changed_' + name)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(body)
    print(json.dumps({'status': 'pass', **result['summary']}, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
