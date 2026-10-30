#!/usr/bin/env python3
"""Describe bounded review cells, retaining source-level state sets (stdlib)."""
from collections import Counter, defaultdict
import json

STATES = {
    'numeric_only': '只有已核數值查核',
    'no_quantity_scope_only': '只有指定段未定位適用量查核',
    'mixed_current_states': '同格有不同來源狀態',
    'source_not_located': '本輪未定位來源',
    'body_pending': '適用正文待核',
    'annual_not_separable': '年度範圍不可分離',
    'outside_scope': '不在採用範圍',
    'not_assessed': '本版無館年查核索引',
}
SINGLE = {
    'numeric_observations_verified': 'numeric_only',
    'body_read_no_eligible_quantity_located': 'no_quantity_scope_only',
    'source_not_located_in_this_search': 'source_not_located',
    'source_found_body_not_reviewed': 'body_pending',
    'annual_scope_not_separable': 'annual_not_separable',
    'outside_selected_scope': 'outside_scope',
}
POPULATIONS = {
    'baseline_inventory_71x6': '原71組織×2020–2025歷史索引格',
    'reviewed_cohort': '本版已有有界查核的館所候選×目標年',
    'baseline_review_union': '原歷史索引與本版有界查核的聯集',
    'reviewed_2020_2025_cohort': '已查核集合中目標年為2020–2025的子集',
    'reviewed_outside_2020_2025_cohort': '已查核集合中目標年不在2020–2025的歷史子集',
}


def current_reviews(reviews):
    extended = {r['extends_review_id'] for r in reviews if r.get('extends_review_id')}
    return [r for r in reviews if r['review_id'] not in extended]


def state_for(values):
    if not values:
        return 'not_assessed'
    return 'mixed_current_states' if len(values) > 1 else SINGLE[values[0]]


def counts(rows):
    found = Counter(r['coverage_state'] for r in rows)
    return {k: found[k] for k in STATES}


def generate(facts, inventory, dimensions):
    current = current_reviews(facts['body_reviews'])
    reviews = defaultdict(list)
    for r in current:
        reviews[(r['organization_id'], r['target_data_year'])].append(r)
    baseline = {(r['source_inventory_id'], r['target_data_year']): r
                for r in inventory['source_inventory_records']}
    dim = {r['organization_id']: r for r in dimensions['organizations']}
    allkeys = set(baseline) | set(reviews)
    assert {k[0] for k in allkeys} <= set(dim), 'coverage_dimension_missing'
    known_obs = defaultdict(list)
    for o in facts['observations']:
        if o['data_year'] is not None:
            known_obs[(o['organization_id'], o['data_year'])].append(o['observation_id'])
    rows = []
    for oid, year in sorted(allkeys):
        rr = sorted(reviews.get((oid, year), []), key=lambda r: r['review_id'])
        ss = sorted({r['review_status'] for r in rr})
        d = dim[oid]
        memberships = sorted({b['batch_id'] for b in d['working_category_by_batch']})
        assert memberships
        pp = ['baseline_review_union']
        if (oid, year) in baseline:
            pp.append('baseline_inventory_71x6')
        if rr:
            pp.append('reviewed_cohort')
            pp.append('reviewed_2020_2025_cohort' if 2020 <= year <= 2025
                      else 'reviewed_outside_2020_2025_cohort')
        lookup = baseline.get((oid, year))
        rows.append({
            'coverage_cell_id': f'{oid}::{year}', 'organization_id': oid,
            'organization_names_as_reported': sorted({r['organization_name'] for r in rr})
                or [d['organization_name_as_in_inventory']],
            'target_data_year': year, 'populations': sorted(pp),
            'review_ids': [r['review_id'] for r in rr], 'review_statuses': ss,
            'coverage_state': state_for(ss),
            'linked_observation_ids': sorted({x for r in rr for x in r['observation_ids']}),
            'single_year_fact_ids': sorted(known_obs.get((oid, year), [])),
            'baseline_lookup_record_id': lookup['source_inventory_record_id'] if lookup else None,
            'working_category_by_batch': memberships,
            'working_category_membership_set': '+'.join(memberships),
            'admin_group': d['admin_group'], 'island_group': d['island_group'],
            'dimension_evidence_organization_id': oid,
            'complete_annual_operations_verified': False,
            'national_population_membership_verified': False,
        })
    summaries, grouped = [], []
    axes = ['year', 'working_category_by_batch', 'admin_group', 'island_group',
            'working_category_by_batch+admin_group+island_group+year']
    for pop, label in POPULATIONS.items():
        selected = [r for r in rows if pop in r['populations']]
        n = len(selected)
        cc = counts(selected)
        summaries.append({
            'population_id': pop, 'definition': label, 'denominator_cells': n,
            'current_review_records': sum(len(r['review_ids']) for r in selected),
            'state_counts': cc,
            'state_percentages': {s: round(v / n * 100, 6) if n else None for s, v in cc.items()},
            'cells_with_any_verified_observation_review': sum(
                'numeric_observations_verified' in r['review_statuses'] for r in selected),
            'not_a_national_rate': True,
        })
        for axis in axes:
            buckets = defaultdict(list)
            for r in selected:
                if axis == 'year':
                    values = {'year': r['target_data_year']}
                elif axis == 'working_category_by_batch':
                    values = {'working_category_membership_set': r['working_category_membership_set']}
                elif axis in ['admin_group', 'island_group']:
                    values = {axis: r[axis]}
                else:
                    values = {k: r[k] for k in ['working_category_membership_set', 'admin_group',
                                                'island_group', 'target_data_year']}
                key = json.dumps(values, sort_keys=True, ensure_ascii=False)
                buckets[key].append(r)
            for key in sorted(buckets):
                subset = buckets[key]
                c = counts(subset)
                grouped.append({
                    'population_id': pop, 'dimension': axis, 'group_values': json.loads(key),
                    'denominator_cells': len(subset), 'state_counts': c,
                    'state_percentages': {s: round(v / len(subset) * 100, 6) for s, v in c.items()},
                    'all_memberships_preserved_as_one_disjoint_set': True,
                    'not_a_national_rate': True,
                })
    assert all(sum(s['state_counts'].values()) == s['denominator_cells'] for s in summaries + grouped)
    assert sum(len(r['review_ids']) for r in rows) == len(current)
    return {
        'schema_version': '1.1', 'dataset_version': facts['dataset_version'], 'as_of': facts['as_of'],
        'observation_unit': 'organization_id_target_year_cell',
        'state_selection_rule': 'all current source-review states; mixed states kept; no highest-state replacement',
        'not_a_national_estimate': True,
        'baseline_inventory_original_pdf_reverified': False,
        'working_category_is_not_official_museum_type': True,
        'geography_is_recorded_roster_or_authority_area_not_all_branch_or_object_location': True,
        'state_labels': STATES, 'populations': summaries, 'cells': rows, 'groups': grouped,
        'period_2020_2025': {
            'target_year_min': 2020, 'target_year_max': 2025,
            'reviewed_cells': sum('reviewed_2020_2025_cohort' in r['populations'] for r in rows),
            'baseline_review_union_cells': sum(2020 <= r['target_data_year'] <= 2025 for r in rows),
            'outside_period_reviewed_cells': sum('reviewed_outside_2020_2025_cohort' in r['populations'] for r in rows),
            'counts_are_review_cells_not_objects': True,
        },
        'limits': [
            '格的狀態只描述既有有界查核，不是全年作業、機構未做或未公開的判定。',
            '原426格歷史索引與已核集合分開；無查核不等於本輪未定位來源。',
            '全部已查核集合另分2020–2025與期間外歷史子集；子集已包含於全集，不能再相加。歷史索引補登不增加2020–2025格數。',
            '同館年不同來源的狀態全部保留；有數值與指定段無量可以同時成立。',
            '工作批次是整理流程，多批次以完整成員集合分組，不冒充館類或重複加進多組。',
            '權管及島群依原中繼資料，原PDF未核層級保留；跨場址或資料不足保持unknown。',
            '各年納入集合可能不同，不能將柱形差異解讀為保存修護量或機構行為趨勢。',
            '0格只表示該分母中沒有這類查核格，從未填入0件或把未知數量補零。',
        ],
    }
