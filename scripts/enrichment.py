#!/usr/bin/env python3
"""Evidence-linked review annotations and conservative derived search sidecars.

No quantity is summed or converted. All original observations remain unchanged.
"""
from pathlib import Path
from collections import Counter
import hashlib, json, re
import coverage as coverage_model
import normalization

ROOT = Path(__file__).resolve().parents[1]
INPUT_FILES = ['data/absence_annotations.json', 'metadata/absence_vocabulary.json',
               'metadata/organization_dimensions.json', 'metadata/normalization_rules.json',
               'schema/absence_annotation.schema.json', 'schema/normalization_record.schema.json']
FIGURE_NAMES = ['coverage-states.svg', 'coverage-facets.svg', 'absence-tags.svg']


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def digest(body):
    return hashlib.sha256(body).hexdigest()


def read(path):
    return json.loads(path.read_text())


def figure_source_sha(coverage, annotations, vocabulary):
    return digest(encode({'coverage': coverage, 'annotations': annotations, 'vocabulary': vocabulary}))


def validate_inputs(facts, inventory, root=ROOT, shape_validator=None):
    if shape_validator is None:
        from build_exports import validate_review_shape
        shape_validator = validate_review_shape
    annotations = read(root / 'data/absence_annotations.json')
    vocabulary = read(root / 'metadata/absence_vocabulary.json')
    dimensions = read(root / 'metadata/organization_dimensions.json')
    rules = read(root / 'metadata/normalization_rules.json')
    current = coverage_model.current_reviews(facts['body_reviews'])
    target = {r['review_id']: r for r in current
              if r['review_status'] == 'body_read_no_eligible_quantity_located'}
    assert len(annotations) == len(target), 'absence_annotation_target_count'
    assert {r['review_id'] for r in annotations} == set(target), 'absence_annotation_target_ids'
    schema = read(root / 'schema/absence_annotation.schema.json')
    for a in annotations:
        shape_validator(a, schema, a['review_id'])
        r = target[a['review_id']]
        assert (a['organization_id'], a['target_data_year'], a['source_ids']) == (
            r['organization_id'], r['target_data_year'], r['source_ids']), 'absence_annotation_scope'
        assert a['absence_reason'] and a['evidence'], 'absence_missing_decision_or_evidence'
        for k in ['content_tags', 'absence_reason']:
            assert len(a[k]) == len(set(a[k])), 'absence_duplicate_label'
            assert set(a[k]) <= {t for e in a['evidence'] for t in e[k]}, 'absence_unsupported_label'
        if a['classification_status'] == 'insufficient_detail':
            assert a['content_tags'] == [] and a['absence_reason'] == ['no_specific_reason_documented']
        else:
            assert 'no_specific_reason_documented' not in a['absence_reason']
        for e in a['evidence']:
            assert e['quote'] and len(e['quote']) <= 220 and e['quote'] in r[e['field']], 'absence_quote_not_in_note'
            assert set(e['content_tags']) <= set(a['content_tags'])
            assert set(e['absence_reason']) <= set(a['absence_reason'])
        assert set(a['content_tags']) <= set(vocabulary['content_tag_labels'])
        assert set(a['absence_reason']) <= set(vocabulary['absence_reason_labels'])
    expected_ids = {r['source_inventory_id'] for r in inventory['baseline_71_organizations']
                    + inventory['supplemental_14_organization_candidates']} | {
        r['source_facility_inventory_id'] for r in inventory['additional_13_public_facility_candidates']}
    dd = dimensions['organizations']
    assert len(dd) == len(expected_ids) and {d['organization_id'] for d in dd} == expected_ids
    assert dimensions['working_category_is_workflow_not_institution_type'] is True
    assert dimensions['unknowns_preserved'] is True
    for d in dd:
        assert d['admin_group'] in ['central', 'local', 'unknown']
        assert d['island_group'] in ['main_island', 'offshore', 'unknown']
        assert d['automatic_numeric_aggregation_allowed'] is False
        assert d['working_category_by_batch']
        for b in d['working_category_by_batch']:
            assert b['institution_type_inferred'] is False
    # Dimension provenance quotes come from the unchanged inventory/workflow files.
    evidence_inputs = set()
    roster_rows = inventory['baseline_71_organizations'] + inventory['supplemental_14_organization_candidates'] + inventory['additional_13_public_facility_candidates']
    roster_by_id = {r.get('source_inventory_id', r.get('source_facility_inventory_id')): r for r in roster_rows}
    def check_evidence(value):
        if isinstance(value, dict):
            if 'literal_short_value' in value:
                evidence_inputs.add(value['input_filename'])
            if 'literal_short_value' in value and isinstance(value['literal_short_value'], str):
                text = (root / value['input_filename']).read_text()
                assert value['literal_short_value'] in text, ('dimension_literal_not_in_input', value)
                if value['input_filename'] == 'metadata/inventory.json':
                    row = roster_by_id[value['organization_id']]
                    assert row[value['field']] == value['literal_short_value'], 'dimension_wrong_roster_row_or_field'
            for v in value.values():
                check_evidence(v)
        elif isinstance(value, list):
            for v in value:
                check_evidence(v)
    check_evidence(dd)
    assert evidence_inputs <= {i['input_filename'] for i in dimensions['input_manifest']}, 'dimension_evidence_missing_from_manifest'
    for item in dimensions['input_manifest']:
        assert digest((root / item['input_filename']).read_bytes()) == item['sha256'], 'dimension_input_changed'
    normalized = normalization.normalize(facts, rules)
    norm_schema = read(root / 'schema/normalization_record.schema.json')
    assert len(normalized) == len(facts['observations'])
    for row in normalized:
        shape_validator(row, norm_schema, row['observation_id'])
    coverage = coverage_model.generate(facts, inventory, dimensions)
    return {'annotations': annotations, 'vocabulary': vocabulary, 'dimensions': dimensions,
            'rules': rules, 'normalized': normalized, 'coverage': coverage}


def generate(facts, inventory, root=ROOT, shape_validator=None):
    inputs = validate_inputs(facts, inventory, root, shape_validator)
    aa, vocab, cov = inputs['annotations'], inputs['vocabulary'], inputs['coverage']
    tables = {'absence_annotations': aa, 'normalized_observations': inputs['normalized'],
              'coverage_cells': cov['cells'], 'coverage_groups': cov['groups']}
    outputs = {'metadata/coverage.json': encode(cov)}
    outputs.update(normalization.build_outputs(facts, inputs['rules']))
    labels = vocab['content_tag_labels']
    tagcounts = Counter(t for row in aa for t in row['content_tags'])
    reasoncounts = Counter(t for row in aa for t in row['absence_reason'])
    cc = Counter(r['classification_status'] for r in aa)
    n_cells = len({(a['organization_id'], a['target_data_year']) for a in aa})
    n_only = sum(c['coverage_state'] == 'no_quantity_scope_only' for c in cov['cells'])
    by_review = {r['review_id']: r for r in facts['body_reviews']}
    report = ['# 指定查核範圍的缺量內容註記\n',
              f'版本v{facts["dataset_version"]}；{len(aa)}則目前N查核的說明註記。這不是機構未公開原因調查，也不是重新閱讀所有原件。\n',
              f'有文字支持{cc["supported_by_review_note"]}則，資訊不足{cc["insufficient_detail"]}則。',
              f'{len(aa)}則來源查核、{n_cells}個含N館年格與{n_only}個目前僅有N狀態的格是不同粒度；同館年有數值與另一來源指定段無量可並存。\n',
              '## 判讀與證據\n',
              '每列以review_id連回原查核，保留來源、範圍、內容標籤、不可採原因及引文欄位。引文來自原公開查核說明，不冒充官方PDF逐字引文；其中「本輪」指原查核當時，不是本版重新看圖。',
              '資訊不足不是零，也不會強塞其他類；未指派某標籤不代表已證明該內容不存在。數位作業、盤點或館外服務不是一律排除，須讀每筆原範圍。\n',
              '標籤可複選，以下各列不可相加為館年、機構、報告或物件總數。\n',
              '|內容標籤|查核註記數|\n|---|---:|']
    report += [f'|{labels[t]}|{tagcounts[t]}|' for t in labels]
    report += ['\n## 不可採原因（僅限原查核指定範圍）\n',
               '|原因標籤|查核註記數|\n|---|---:|']
    report += [f'|{label}|{reasoncounts[key]}|' for key, label in vocab['absence_reason_labels'].items()]
    report += ['\n![既有N查核說明的內容標籤，分類可重疊](figures/absence-tags.svg)\n',
               '## 逐則註記索引\n', '|館所|目標年|查核識別|內容標籤|判定|\n|---|---:|---|---|---|']
    for a in aa:
        name = by_review[a['review_id']]['organization_name'].replace('|', '／')
        tags = '、'.join(labels[t] for t in a['content_tags']) or '未有足夠資訊'
        status = '說明文字支持' if a['classification_status'] == 'supported_by_review_note' else '資訊不足'
        report.append(f'|{name}|{a["target_data_year"]}|{a["review_id"]}|{tags}|{status}|')
    report += ['\n完整引文、支持標籤與欄位見[data/absence_annotations.json](../data/absence_annotations.json)；',
               '原核讀證據見[data/body_reviews.jsonl](../data/body_reviews.jsonl)。原狀態與歷史未因標籤改寫。\n']
    outputs['docs/ABSENCE.md'] = ('\n'.join(report) + '\n').encode()
    summ = ['# 查核格的範圍與覆蓋分母\n', f'版本v{facts["dataset_version"]}。觀察單位是候選識別×目標年格，不是修護物件或完整報告份數。\n',
            '三個集合分開呈現；狀態保留全部目前來源，混合狀態不以最高層級覆蓋。\n',
            '|集合|館年格數|目前來源查核則數|本版無查核格|至少一來源有已核紀錄的格|\n|---|---:|---:|---:|---:|']
    for p in cov['populations']:
        summ.append(f'|{p["definition"]}|{p["denominator_cells"]}|{p["current_review_records"]}|{p["state_counts"]["not_assessed"]}|{p["cells_with_any_verified_observation_review"]}|')
    summ += ['\n原426格與實際review格不同；無查核不能改為本輪未定位來源。聯集也不是98個候選的所有年份或全國母體。',
             '已有數值仍只證明所列來源分項，不代表完整年度量；不提供全國公開率或績效排名。\n',
             '![三種明確集合的格狀態](figures/coverage-states.svg)\n',
             '![按工作流程、原權管文字、行政區島群與年度的有界查核格](figures/coverage-facets.svg)\n',
             '## 分組的意思\n',
             'working_category_by_batch只表示原NPM／順序二至六工作文件實列的流程成員，不是官方館類。未在這些表中指派者保留pre_batch_or_unassigned；不推未曾研究。多批次以完整成員集合形成互斥組，沒有一格重算多次。',
             'admin_group只分原權管／營運文字中可辨識的中央、地方或unknown，不代表藏品所有權、法律登記或營運形式。island_group只分原名錄或權管行政區的島群；多場址或資料不足保持unknown，不推實物與所有分館位置。原名錄PDF未核的層級保留。',
             '各年納入集合可能不同，不能看柱形差異便推斷作業或機構行為趨勢。',
             'JSON與CSV提供各集合按工作批次成員集合×行政群組×島群×年交叉的實際分母及狀態數；0格不是0件。\n',
             '[完整coverage.json](../metadata/coverage.json) · [逐格CSV](../data/coverage_cells.csv) · [分組CSV](../data/coverage_groups.csv) · [分組原始證據](../metadata/organization_dimensions.json)\n']
    outputs['docs/COVERAGE.md'] = ('\n'.join(summ) + '\n').encode()
    source_sha = figure_source_sha(cov, aa, vocab)
    figures = {}
    for name in FIGURE_NAMES:
        path = root / 'docs/figures' / name
        if path.exists():
            body = path.read_bytes()
            match = re.search(rb'<!-- enrichment-source-sha256: ([a-f0-9]{64}) -->', body)
            assert match and match[1].decode() == source_sha, 'figure_source_changed_rerender_from_candidate'
            assert b'<script' not in body and b'/Users/' not in body
            figures[name] = {'path': 'docs/figures/' + name, 'sha256': digest(body), 'bytes': len(body)}
    build = {
        'schema_version': '1.0', 'dataset_version': facts['dataset_version'],
        'canonical_facts_sha256': digest(encode(facts)),
        'input_sha256': {name: digest((root / name).read_bytes()) for name in INPUT_FILES},
        'source_schema_versions': {'absence': '1.0', 'normalization': '1.0', 'coverage': '1.0'},
        'annotation_records': len(aa), 'annotation_classification_status_counts': dict(cc),
        'normalized_observation_records': len(inputs['normalized']),
        'coverage_current_review_records': len(coverage_model.current_reviews(facts['body_reviews'])),
        'coverage_reviewed_cells': next(p['denominator_cells'] for p in cov['populations'] if p['population_id'] == 'reviewed_cohort'),
        'figure_source_sha256': source_sha, 'figure_artifacts': figures,
        'original_observations_mutated': False, 'quantities_summed_or_converted': False,
        'national_estimate': False,
    }
    outputs['metadata/enrichment_build.json'] = encode(build)
    return {'tables': tables, 'outputs': outputs, 'summary': build, 'coverage': cov}
