#!/usr/bin/env python3
"""Build the static, source-preserving museum catalogue (standard library only).

Only writes site/. --check computes the expected bytes without writing anything.
Original files and canonical data are never modified or redistributed.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
from html import escape
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEWER_VERSION = '1.2.0'
REPOSITORY = 'https://github.com/poplolioi11/tw-public-museum-conservation'
ENRICHMENT_DOWNLOADS = {
    'coverage': ('metadata/coverage.json', '查核格狀態與年份子集 JSON'),
    'absence_annotations': ('data/absence_annotations.json', '缺量註記與引文 JSON'),
    'absence_annotations_jsonl': ('data/absence_annotations.jsonl', '缺量註記 JSONL'),
    'absence_annotations_csv': ('data/absence_annotations.csv', '缺量註記 CSV'),
    'normalized_observations_jsonl': ('data/normalized_observations.jsonl', '搜尋別名 JSONL'),
    'normalized_observations_csv': ('data/normalized_observations.csv', '搜尋別名 CSV'),
    'coverage_cells_jsonl': ('data/coverage_cells.jsonl', '逐格查核狀態 JSONL'),
    'coverage_cells_csv': ('data/coverage_cells.csv', '逐格查核狀態 CSV'),
    'coverage_groups_jsonl': ('data/coverage_groups.jsonl', '分組分母與狀態 JSONL'),
    'coverage_groups_csv': ('data/coverage_groups.csv', '分組分母與狀態 CSV'),
    'organization_dimensions': ('metadata/organization_dimensions.json', '組織分組與原始證據 JSON'),
    'absence_vocabulary': ('metadata/absence_vocabulary.json', '缺量內容與原因詞表 JSON'),
    'normalization_rules': ('metadata/normalization_rules.json', '搜尋別名規則與覆核清冊 JSON'),
    'enrichment_build': ('metadata/enrichment_build.json', '有界整理來源與圖表版本清單 JSON'),
    'relation_projection': ('data/relation_projection.json', '關係與證據註記附表 JSON'),
    'relation_projection_jsonl': ('data/relation_projection.jsonl', '關係與證據註記 JSONL'),
    'relation_projection_csv': ('data/relation_projection.csv', '關係與證據註記 CSV'),
    'relation_projection_rules': ('metadata/relation_projection_rules.json', '關係附表對照與原值清冊 JSON'),
    'relation_projection_build': ('metadata/relation_projection_build.json', '關係附表版本與限制 JSON'),
    'completion_reviews': ('data/completion_reviews.json', '指定完成語覆核 JSON'),
    'completion_reviews_jsonl': ('data/completion_reviews.jsonl', '指定完成語覆核 JSONL'),
    'completion_reviews_csv': ('data/completion_reviews.csv', '指定完成語覆核 CSV'),
    'completion_review_rules': ('metadata/completion_review_rules.json', '完成語覆核範圍與清冊 JSON'),
    'completion_review_build': ('metadata/completion_review_build.json', '完成語覆核版本與限制 JSON'),
}
FIGURES = {
    'coverage-states.svg': ('集合與年份子集的查核格狀態',
        '下方狀態表列出相同數據；全集包含子集，各欄不能相加。'),
    'coverage-facets.svg': ('分組與年度的有界查核格',
        '工作流程、權管文字、行政區島群與年度的分組分母及狀態見分組 CSV；各年納入集合可能不同，不能解讀為修護量或機構行為趨勢。'),
    'absence-tags.svg': ('既有缺量查核說明的內容標籤',
        '內容標籤表提供相同計數；一則可有多個標籤，標籤數不可相加為館年、報告或物件總數。'),
}
STATE_EXPLANATIONS = {
    'numeric_only': '目前來源查核只有已核數值狀態；仍僅限所列分項，不證明全館全年完整。',
    'no_quantity_scope_only': '目前來源查核只有指定段未定位適用量；不是零修護，也不是全年未公開。',
    'mixed_current_states': '同館同年不同來源有不同狀態，全部保留；有數值與另一來源指定段無量可以並存。',
    'source_not_located': '原輪次的有限查找未定位適用來源，不等於沒有來源、沒有作業或未公開。',
    'body_pending': '來源或原件已定位，適用正文仍待核，不能當成已讀無量。',
    'annual_not_separable': '來源的年度或館級範圍無法分離，不拆年、不分配父機構或他館的數量。',
    'outside_scope': '所列來源或年度不在本題採用範圍，不表示該館沒有保存工作。',
    'not_assessed': '此格沒有本版有界查核，不改寫成未定位來源或已讀無量。',
}


def sha(body):
    return hashlib.sha256(body).hexdigest()


def stable(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8')


def relation_ids(relation):
    single = ('parent', 'parent_observation_id', 'observation_id', 'from_observation_id',
              'to_existing_observation_id', 'larger_scope', 'completion_subset',
              'treatment_record', 'completed_record')
    multiple = ('children', 'candidate_child_ids', 'observation_ids', 'existing_release_observation_ids')
    return {relation[k] for k in single if isinstance(relation.get(k), str)} | {
        ident for k in multiple for ident in relation.get(k, []) if isinstance(ident, str)}


def input_snapshot(root):
    names = ['VERSION', 'data/facts.json', 'schema/vocabulary.json', 'scripts/build_site.py']
    names += ['site-src/' + name for name in ('index.html', 'enrichment.html', 'app.css', 'app.js')]
    names += [path for path, _ in ENRICHMENT_DOWNLOADS.values()]
    names += ['metadata/inventory.json', 'schema/absence_annotation.schema.json',
              'schema/normalization_record.schema.json']
    names += ['docs/figures/' + name for name in FIGURES]
    return {name: (root / name).read_bytes() for name in names}


def safe_old_path(name):
    fixed = {'data/' + Path(path).name for path, _ in ENRICHMENT_DOWNLOADS.values()}
    fixed |= {'figures/' + name for name in FIGURES}
    return name in fixed or bool(re.fullmatch(r'data/[a-f0-9]{64}\.json|records/[A-Za-z0-9._-]+\.json', name))


def enrichment_page(inputs, facts, version, outputs):
    """Publish exact sidecars and render counts of review cells, never quantities."""
    coverage = json.loads(inputs['metadata/coverage.json'])
    annotations = json.loads(inputs['data/absence_annotations.json'])
    vocabulary = json.loads(inputs['metadata/absence_vocabulary.json'])
    normalized = [json.loads(line) for line in inputs['data/normalized_observations.jsonl'].splitlines()]
    relations = json.loads(inputs['data/relation_projection.json'])
    completed = json.loads(inputs['data/completion_reviews.json'])
    relation_rules = json.loads(inputs['metadata/relation_projection_rules.json'])
    completion_rules = json.loads(inputs['metadata/completion_review_rules.json'])
    if coverage['dataset_version'] != version or coverage['as_of'] != facts['as_of']:
        raise ValueError('Coverage and canonical facts versions differ; rebuild exports first')
    if annotations != [json.loads(line) for line in inputs['data/absence_annotations.jsonl'].splitlines()]:
        raise ValueError('Annotation JSON and JSONL differ; rebuild exports first')
    for key in ('cells', 'groups'):
        rows = [json.loads(line) for line in inputs['data/coverage_' + key + '.jsonl'].splitlines()]
        if rows != coverage[key]:
            raise ValueError('Coverage JSON and ' + key + ' JSONL differ; rebuild exports first')
    normalized_ids = [r['observation_id'] for r in normalized]
    if len(normalized_ids) != len(set(normalized_ids)) or set(normalized_ids) != {
            r['observation_id'] for r in facts['observations']}:
        raise ValueError('Normalized sidecar must link each existing observation once')
    populations = coverage['populations']
    if {p['population_id'] for p in populations} != {
            'baseline_inventory_71x6', 'reviewed_cohort', 'baseline_review_union',
            'reviewed_2020_2025_cohort', 'reviewed_outside_2020_2025_cohort'} or len(populations) != 5:
        raise ValueError('Expected explicit review-cell populations and year subsets')
    labels = coverage['state_labels']
    if set(labels) != set(STATE_EXPLANATIONS):
        raise ValueError('Coverage state vocabulary changed; review page explanations first')
    counts = {}
    for p in populations:
        selected = [c for c in coverage['cells'] if p['population_id'] in c['populations']]
        cc = Counter(c['coverage_state'] for c in selected)
        counts[p['population_id']] = {key: cc[key] for key in labels}
        if len(selected) != p['denominator_cells'] or counts[p['population_id']] != p['state_counts']:
            raise ValueError('Coverage cell population and summary differ')
        if sum(len(c['review_ids']) for c in selected) != p['current_review_records']:
            raise ValueError('Coverage current source-review count differs')
    statuses = Counter(a['classification_status'] for a in annotations)
    if set(statuses) - {'supported_by_review_note', 'insufficient_detail'}:
        raise ValueError('Unknown annotation status; do not silently omit it')
    tagcounts = Counter(t for a in annotations for t in a['content_tags'])
    if set(tagcounts) - set(vocabulary['content_tag_labels']):
        raise ValueError('Annotation tag is absent from the published vocabulary')
    downloads = {}
    for key, (source_path, label) in ENRICHMENT_DOWNLOADS.items():
        body = inputs[source_path]
        path = 'data/' + Path(source_path).name
        outputs[path] = body
        downloads[key] = {'url': path, 'download_url': './' + path, 'label': label,
                          'source_path': source_path, 'sha256': sha(body), 'bytes': len(body)}
    # Same canonical encoding as enrichment.figure_source_sha; no original files are read here.
    figure_source_body = (json.dumps({'coverage': coverage, 'annotations': annotations,
        'vocabulary': vocabulary}, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
    figure_source_sha = sha(figure_source_body)
    figures = {}
    for name, (label, note) in FIGURES.items():
        source_path = 'docs/figures/' + name
        body = inputs[source_path]
        marker = re.search(rb'<!-- enrichment-source-sha256: ([a-f0-9]{64}) -->', body)
        if not marker or marker[1].decode() != figure_source_sha:
            raise ValueError('Figure source marker differs; rerender ' + name)
        if b'<script' in body.lower() or b'/Users/' in body:
            raise ValueError('Unexpected executable or private content in figure: ' + name)
        path = 'figures/' + name
        outputs[path] = body
        figures[name] = {'url': path, 'download_url': './' + path, 'label': label,
                         'source_path': source_path, 'sha256': sha(body), 'bytes': len(body)}
    population_table = '<div class="table-wrap"><table class="summary-table"><caption>每欄使用自己的館年格分母；全集與子集已重疊，各欄不能相加</caption><thead><tr><th scope="col">目前來源狀態</th>'
    population_table += ''.join('<th scope="col">' + escape(p['definition']) + '<br>' +
        str(p['denominator_cells']) + '格</th>' for p in populations)
    population_table += '</tr></thead><tbody>'
    for key, label in labels.items():
        population_table += '<tr><th scope="row">' + escape(label) + '</th>'
        population_table += ''.join('<td>' + str(counts[p['population_id']][key]) + '</td>' for p in populations)
        population_table += '</tr>'
    population_table += '</tbody></table></div>'
    population_notes = '<ul>' + ''.join('<li>' + escape(p['definition']) + '：' +
        str(p['denominator_cells']) + '個館年格，對應' + str(p['current_review_records']) +
        '則目前來源查核。</li>' for p in populations) + '</ul>'
    guide = '<dl>' + ''.join('<dt>' + escape(label) + '</dt><dd>' +
        escape(STATE_EXPLANATIONS[key]) + '</dd>' for key, label in labels.items()) + '</dl>'
    annotation_summary = (f'本版為{len(annotations)}則目前「指定段未定位適用量」查核增加內容註記；'
        f'{statuses["supported_by_review_note"]}則有既有查核說明文字支持，'
        f'{statuses["insufficient_detail"]}則資訊不足。註記的單位是查核則數，與館年格數不同。')
    tags = '<div class="table-wrap"><table class="summary-table"><caption>既有查核說明的內容標籤，可複選，不可相加</caption><thead><tr><th scope="col">內容標籤</th><th scope="col">查核註記數</th></tr></thead><tbody>'
    tags += ''.join('<tr><th scope="row">' + escape(label) + '</th><td>' + str(tagcounts[key]) + '</td></tr>'
                    for key, label in vocabulary['content_tag_labels'].items())
    tags += '</tbody></table></div>'
    relation_counts = Counter(r['category'] for r in relations)
    relation_table = '<div class="table-wrap"><table class="summary-table"><caption>既有關係與證據註記列數，不是物件量</caption><thead><tr><th scope="col">註記類型</th><th scope="col">列數</th></tr></thead><tbody>'
    relation_table += ''.join('<tr><th scope="row">'+escape(label)+'</th><td>'+str(relation_counts[key])+'</td></tr>' for key,label in relation_rules['category_labels'].items())
    relation_table += '</tbody></table></div>'
    original_by_id = {o['observation_id']:o for o in facts['observations']}
    source_by_id = {s['source_id']:s for s in facts['sources']}
    if len(relations) != len(facts['relations']) or [r['original_relation'] for r in relations] != facts['relations']:
        raise ValueError('Relation projection must preserve all original notes')
    if len(completed) != len({r['observation_id'] for r in completed}) or {r['observation_id'] for r in completed} != {o['observation_id'] for o in facts['observations'] if o['completion_category']=='completion_from_context'}:
        raise ValueError('Completion review must link every selected original record once')
    completion_table = '<div class="table-wrap"><table class="summary-table"><caption>指定完成語原頁覆核；原分類保留，不是完成物件總數</caption><thead><tr><th scope="col">館所／年與紀錄</th><th scope="col">本輪判讀</th><th scope="col">必要完成短語與適用界線</th><th scope="col">官方原件頁段</th></tr></thead><tbody>'
    for review in completed:
        o=original_by_id[review['observation_id']];s=source_by_id[review['source_id']]
        url=(s['official_file_url'] or s['official_landing_url'])+'#page='+str(o['pdf_page_1_based'])
        completion_table += '<tr id="completion-'+escape(o['observation_id'],quote=True)+'"><th scope="row"><a href="./index.html?record='+escape(o['observation_id'],quote=True)+'">'+escape(o['organization_name']+'／'+str(o['data_year'])+'｜'+o['metric_as_reported'])+'</a></th><td>'+escape(completion_rules['assessment_labels'][review['assessment']])+'</td><td>'+escape('「'+review['completion_phrase_raw']+'」；'+review['interpretation_note']+' '+review['remaining_uncertainty'])+'</td><td><a href="'+escape(url,quote=True)+'">PDF'+','.join(map(str,review['pdf_pages_1_based']))+'／印'+escape(review['printed_page'])+'</a></td></tr>'
    completion_table += '</tbody></table></div>'
    download_links = '<ul>' + ''.join('<li><a href="./' + escape(d['url'], quote=True) + '">' +
        escape(d['label']) + '</a> <span class="download-size">（' + str(d['bytes']) + ' bytes）</span></li>'
        for d in downloads.values()) + '</ul>'
    replacements = {'__DATASET_VERSION__': escape(version), '__AS_OF__': escape(facts['as_of']),
        '__POPULATION_TABLE__': population_table, '__POPULATION_NOTES__': population_notes,
        '__STATE_GUIDE__': guide, '__ANNOTATION_SUMMARY__': escape(annotation_summary),
        '__CONTENT_TAG_TABLE__': tags, '__NORMALIZED_COUNT__': str(len(normalized)),
        '__RELATION_TABLE__': relation_table, '__RELATION_COUNT__': str(len(relations)),
        '__COMPLETION_TABLE__': completion_table, '__COMPLETION_COUNT__': str(len(completed)),
        '__DOWNLOAD_LINKS__': download_links}
    template = inputs['site-src/enrichment.html'].decode()
    for marker, replacement in replacements.items():
        if marker not in template:
            raise ValueError('Enrichment HTML marker missing: ' + marker)
        template = template.replace(marker, replacement)
    if re.search(r'__[A-Z_]+__', template):
        raise ValueError('Unresolved enrichment HTML marker')
    outputs['enrichment.html'] = template.encode()
    return {'page': {'url': 'enrichment.html', 'sha256': sha(outputs['enrichment.html']),
                     'bytes': len(outputs['enrichment.html'])},
            'downloads': downloads, 'figures': figures, 'figure_source_sha256': figure_source_sha}


def expected(root, inputs):
    version = inputs['VERSION'].decode().strip()
    facts = json.loads(inputs['data/facts.json'])
    vocabulary = json.loads(inputs['schema/vocabulary.json'])
    if facts['dataset_version'] != version:
        raise ValueError('VERSION and facts.dataset_version differ; rebuild canonical data first')
    for field in ('observations', 'sources', 'body_reviews', 'relations'):
        if not isinstance(facts.get(field), list):
            raise ValueError('Missing list: ' + field)
    if not isinstance(vocabulary.get('action_categories'), dict):
        raise ValueError('Classification vocabulary missing')
    outputs = {}
    entries = {}
    for key, name in (('data', 'data/facts.json'), ('vocabulary', 'schema/vocabulary.json')):
        body = inputs[name]
        path = 'data/' + sha(body) + '.json'
        outputs[path] = body
        entries[key] = {'url': path, 'sha256': sha(body), 'bytes': len(body), 'download_url': './' + path}
    source_map = {s['source_id']: s for s in facts['sources']}
    seen = set()
    for row in facts['observations']:
        record_id = row['observation_id']
        if not re.fullmatch(r'[A-Za-z0-9._-]+', record_id) or record_id in seen:
            raise ValueError('Unsafe or duplicate observation id: ' + record_id)
        seen.add(record_id)
        if row['source_id'] not in source_map:
            raise ValueError('Unresolved source: ' + record_id)
        related = [r for r in facts['relations'] if record_id in relation_ids(r)]
        outputs['records/' + record_id + '.json'] = stable({'dataset_version': version, 'observation': row, 'source': source_map[row['source_id']], 'relations': related})
    enrichment = enrichment_page(inputs, facts, version, outputs)
    template = inputs['site-src/index.html'].decode()
    if '__DATASET_VERSION__' not in template:
        raise ValueError('HTML dataset-version marker missing')
    outputs['index.html'] = template.replace('__DATASET_VERSION__', version).encode()
    for name in ('app.css', 'app.js'):
        outputs[name] = inputs['site-src/' + name]
    outputs['.nojekyll'] = b''
    outputs['llms.txt'] = (f'''# 臺灣公立館保存修護公開資料索引

資料版本 {version}；資料截點 {facts['as_of']}。這是有限來源子集，不是全國完整修護統計。

- [資料清單](manifest.json)：完整 JSON 的相對路徑、SHA-256、bytes、版本及逐筆入口。
- [本版完整公開事實]({entries['data']['url']})：observations、sources、relations、body_reviews 與範圍摘要。
- [分類詞彙]({entries['vocabulary']['url']})：分類標籤及使用限制。
- [有界資料整理](enrichment.html)：館年格全集與年份子集、缺量註記、關係及完成語覆核、文字表格與圖表。
- 逐筆紀錄：records/{{observation_id}}.json，含 observation、source、relations。
- [GitHub 說明與固定發行版本]({REPOSITORY})。

共 {len(facts['observations'])} 列紀錄，列數不是修復物件數。保留原數字字串、量詞、完成狀態與官方來源。
body_reviews含{len(facts['body_reviews'])}則歷史查核；目前紀錄為未被extends_review_id延伸的所有紀錄，同館同年可有多則，不按日期或狀態挑一筆。六種查核狀態分開，適用正文待核不等於指定正文已讀無量；每則原註記的文字／圖頁範圍也不等於全年已讀。
metric_label供解讀，metric_as_reported保留原詞。專案原列對象量不等於年度已完成量，請同讀完成狀態、原報期間與對象範圍。
未知不是零；近似量與雙單位不強轉整數；跨年數值不拆成年份；分項、合計與可能重疊的批次不相加。
HTML 來源以 source_locator 定位，PDF 頁碼為 null；PDF 來源以 pdf_page_1_based 定位。
引用請同時提供資料版本、observation_id 與原官方來源及頁碼／正文定位。程式與文件的 MIT 不改變來源權利。

## 有界整理的機器入口

manifest.json 的 enrichment.downloads 與 enrichment.figures 提供每個端點的 url、SHA-256、bytes 及來源路徑。
缺量註記只引用既有公開查核說明，不是機構未公開原因、新原件核讀或官方逐字引文。資訊不足保持資訊不足。
coverage 的觀察單位是 organization_id×target_data_year；population 全集與年份子集互有重疊，不相加、不稱全國公開率。
not_assessed、source_not_located、body_pending、no_quantity_scope_only 與 mixed_current_states 分別保留。
normalization 僅為既有觀測的搜尋別名；不帶 quantity、不換算件數、不使混合作業或跨館量值可相加。
''' + '\n'.join('- [' + d['label'] + '](' + d['url'] + ')' for d in enrichment['downloads'].values()) + '\n' +
        '\n'.join('- [' + d['label'] + '](' + d['url'] + ')' for d in enrichment['figures'].values()) + '\n').encode('utf-8')
    manifest = {'schema_version': 1, 'viewer_version': VIEWER_VERSION, 'dataset_version': version,
                'as_of': facts['as_of'], 'data': entries['data'], 'vocabulary': entries['vocabulary'],
                'enrichment': enrichment,
                'repository_url': REPOSITORY, 'record_url_template': './records/{observation_id}.json',
                'inputs_sha256': {name: sha(body) for name, body in inputs.items()},
                'scope_note': '有限來源目錄；紀錄筆數不是物件總數，未作年度或館際加總。',
                'generated_files': sorted(outputs)}
    outputs['manifest.json'] = stable(manifest)
    return outputs


def write_changed(path, body):
    if path.is_file() and path.read_bytes() == body:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_bytes(body)
    temp.replace(path)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=ROOT)
    ap.add_argument('--check', action='store_true', help='Detect stale outputs without writing')
    args = ap.parse_args()
    root = args.root.resolve()
    inputs = input_snapshot(root)
    outputs = expected(root, inputs)
    if input_snapshot(root) != inputs:
        raise SystemExit('Input changed while building; no output was written')
    dest = root / 'site'
    old = {}
    if (dest / 'manifest.json').is_file():
        try:
            old = json.loads((dest / 'manifest.json').read_bytes())
        except (ValueError, OSError):
            pass
    stale = [name for name, body in outputs.items() if not (dest / name).is_file() or (dest / name).read_bytes() != body]
    obsolete = [name for name in old.get('generated_files', []) if safe_old_path(name) and name not in outputs and (dest / name).is_file()]
    if args.check:
        if stale or obsolete:
            print(json.dumps({'status': 'stale', 'different_or_missing': stale, 'obsolete_generated': obsolete}, ensure_ascii=False))
            raise SystemExit(1)
        print(json.dumps({'status': 'current', 'files': len(outputs), 'dataset_version': json.loads(inputs['data/facts.json'])['dataset_version']}))
        return
    changed = 0
    for name, body in outputs.items():
        if name != 'manifest.json':
            changed += write_changed(dest / name, body)
    if input_snapshot(root) != inputs:
        raise SystemExit('Input changed while writing; manifest was not committed. Rebuild before deployment.')
    changed += write_changed(dest / 'manifest.json', outputs['manifest.json'])
    for name in obsolete:
        (dest / name).unlink()
    print(json.dumps({'status': 'built', 'dataset_version': json.loads(inputs['data/facts.json'])['dataset_version'], 'files': len(outputs), 'changed': changed, 'removed_old_generated': len(obsolete)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
