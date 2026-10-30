#!/usr/bin/env python3
"""Regression checks for evidence boundaries, cohort denominators and failure safety."""
from collections import Counter
from pathlib import Path
import copy, csv, hashlib, io, json, shutil, sqlite3, subprocess, sys, tempfile
import build_exports as builder
import enrichment, normalization

ROOT = Path(__file__).resolve().parents[1]


def check(root=ROOT):
    facts = builder.read(root / 'data/facts.json')
    inventory = builder.read(root / 'metadata/inventory.json')
    original = copy.deepcopy(facts)
    result = enrichment.validate_inputs(facts, inventory, root)
    cov = result['coverage']
    assert facts == original, 'enrichment_changed_original_facts'
    # Build the populations independently from explicit keys and extension links.
    old = {r['extends_review_id'] for r in facts['body_reviews'] if r.get('extends_review_id')}
    leaves = [r for r in facts['body_reviews'] if r['review_id'] not in old]
    reviewed = {(r['organization_id'], r['target_data_year']) for r in leaves}
    baseline = {(r['source_inventory_id'], r['target_data_year']) for r in inventory['source_inventory_records']}
    sets = {'baseline_inventory_71x6': baseline, 'reviewed_cohort': reviewed,
            'baseline_review_union': baseline | reviewed,
            'reviewed_2020_2025_cohort': {k for k in reviewed if 2020 <= k[1] <= 2025},
            'reviewed_outside_2020_2025_cohort': {k for k in reviewed if not 2020 <= k[1] <= 2025}}
    assert sets['reviewed_2020_2025_cohort'].isdisjoint(sets['reviewed_outside_2020_2025_cohort'])
    assert sets['reviewed_2020_2025_cohort'] | sets['reviewed_outside_2020_2025_cohort'] == reviewed
    assert len(cov['cells']) == len(baseline | reviewed)
    for population in cov['populations']:
        name = population['population_id']
        subset = [c for c in cov['cells'] if name in c['populations']]
        assert {(c['organization_id'], c['target_data_year']) for c in subset} == sets[name]
        assert population['denominator_cells'] == len(sets[name])
        assert sum(population['state_counts'].values()) == len(sets[name])
        assert population['state_counts']['not_assessed'] == len(sets[name] - reviewed)
        for axis in {g['dimension'] for g in cov['groups']}:
            groups = [g for g in cov['groups'] if g['population_id'] == name and g['dimension'] == axis]
            assert sum(g['denominator_cells'] for g in groups) == len(sets[name]), 'memberships_double_counted'
            assert all(sum(g['state_counts'].values()) == g['denominator_cells'] for g in groups)
    lookup = {(c['organization_id'], c['target_data_year']): c for c in cov['cells']}
    for key, cell in lookup.items():
        rr = [r for r in leaves if (r['organization_id'], r['target_data_year']) == key]
        assert set(cell['review_ids']) == {r['review_id'] for r in rr}
        assert set(cell['review_statuses']) == {r['review_status'] for r in rr}
        assert cell['coverage_state'] == ('not_assessed' if not rr else
               'mixed_current_states' if len({r['review_status'] for r in rr}) > 1 else cell['coverage_state'])
    mixed = lookup[('BASE-023', 2025)]
    assert mixed['coverage_state'] == 'mixed_current_states'
    assert {'numeric_observations_verified', 'body_read_no_eligible_quantity_located'} <= set(mixed['review_statuses'])
    # Every quantity-free export retains full JSON; the SQLite view is equivalent.
    tables = {'absence_annotations': result['annotations'], 'normalized_observations': result['normalized'],
              'coverage_cells': cov['cells'], 'coverage_groups': cov['groups'],
              'relation_projection': result['relation_projection']['rows'],
              'completion_reviews': result['completion_reviews']['rows']}
    with sqlite3.connect(root / 'data/museum-conservation.sqlite') as con:
        for name, rows in tables.items():
            assert rows == [json.loads(x) for x in (root / f'data/{name}.jsonl').read_text().splitlines()]
            assert rows == [json.loads(x[0]) for x in con.execute(f'SELECT record_json FROM {name} ORDER BY row_number')]
            csvrows = list(csv.DictReader(io.StringIO((root / f'data/{name}.csv').read_text(encoding='utf-8-sig'))))
            assert len(rows) == len(csvrows)
            for expected, actual in zip(rows, csvrows):
                assert all(str(builder.flat(expected.get(k))) == actual[k] for k in builder.columns(rows))
    assert {r['observation_id'] for r in result['normalized']} == {r['observation_id'] for r in facts['observations']}
    boundaries = normalization.validate_boundaries(facts, result['rules'])
    # A corrupt sidecar must be refused before replacing any existing export.
    failures = 0
    with tempfile.TemporaryDirectory() as temp:
        sandbox = Path(temp) / 'package'
        shutil.copytree(root, sandbox, ignore=shutil.ignore_patterns('.git', '__pycache__', 'source-cache'))
        def snapshot():
            return {str(p.relative_to(sandbox)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sandbox.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        cases = [
            ('data/absence_annotations.json', lambda x: x[0]['evidence'][0].update(quote='invented quotation absent from the source note')),
            ('data/absence_annotations.json', lambda x: x.pop()),
            ('data/absence_annotations.json', lambda x: x[0].update(unknown_field=True)),
            ('data/absence_annotations.json', lambda x: x[0].update(target_data_year=x[0]['target_data_year'] + 1)),
            ('data/absence_annotations.json', lambda x: x[0].update(content_tags=['stock'], evidence=[dict(x[0]['evidence'][0], content_tags=[])])),
            ('metadata/normalization_rules.json', lambda x: x.update(unexpected_mapping='unreviewed')),
            ('metadata/organization_dimensions.json', lambda x: x['organizations'][0].update(admin_group='guessed')),
            ('metadata/organization_dimensions.json', lambda x: x['organizations'][0]['admin_group_assessment']['evidence'][0].update(literal_short_value='臺北市')),
            ('metadata/organization_dimensions.json', lambda x: x['input_manifest'].pop()),
            ('metadata/relation_projection_rules.json', lambda x: x['type_rules'][0].update(category='unreviewed_guess')),
            ('data/completion_reviews.json', lambda x: x[0].update(assessment='explicit_item_completion_supported')),
            ('data/completion_reviews.json', lambda x: x[0].update(source_id='unknown-original')),
        ]
        for name, mutate in cases:
            path = sandbox / name
            saved = path.read_bytes()
            value = json.loads(saved)
            mutate(value)
            path.write_bytes(builder.encode(value))
            before = snapshot()
            run = subprocess.run([sys.executable, str(sandbox / 'scripts/build_exports.py')], capture_output=True, text=True)
            assert run.returncode != 0 and snapshot() == before, ('invalid_enrichment_wrote_exports', name)
            failures += 1
            path.write_bytes(saved)
    return {'status': 'pass', 'annotation_rows': len(result['annotations']),
            'normalized_rows': len(result['normalized']), 'population_denominators': {k: len(v) for k, v in sets.items()},
            'all_current_source_states_preserved': True, 'quantity_free_exports_equivalent': True,
            'invalid_inputs_preserve_previous_exports': failures, 'normalization_boundaries': boundaries}


if __name__ == '__main__':
    print(json.dumps(check(), ensure_ascii=False))
