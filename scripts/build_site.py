#!/usr/bin/env python3
"""Build the static, source-preserving museum catalogue (standard library only).

Only writes site/. --check computes the expected bytes without writing anything.
Original files and canonical data are never modified or redistributed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEWER_VERSION = '1.1.0'
REPOSITORY = 'https://github.com/poplolioi11/tw-public-museum-conservation'


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
    names += ['site-src/' + name for name in ('index.html', 'app.css', 'app.js')]
    return {name: (root / name).read_bytes() for name in names}


def safe_old_path(name):
    return bool(re.fullmatch(r'data/[a-f0-9]{64}\.json|records/[A-Za-z0-9._-]+\.json', name))


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
- 逐筆紀錄：records/{{observation_id}}.json，含 observation、source、relations。
- [GitHub 說明與固定發行版本]({REPOSITORY})。

共 {len(facts['observations'])} 列紀錄，列數不是修復物件數。保留原數字字串、量詞、完成狀態與官方來源。
body_reviews含{len(facts['body_reviews'])}則歷史查核；目前紀錄為未被extends_review_id延伸的所有紀錄，同館同年可有多則，不按日期或狀態挑一筆。六種查核狀態分開，適用正文待核不等於指定正文已讀無量；每則原註記的文字／圖頁範圍也不等於全年已讀。
metric_label供解讀，metric_as_reported保留原詞。專案原列對象量不等於年度已完成量，請同讀完成狀態、原報期間與對象範圍。
未知不是零；近似量與雙單位不強轉整數；跨年數值不拆成年份；分項、合計與可能重疊的批次不相加。
HTML 來源以 source_locator 定位，PDF 頁碼為 null；PDF 來源以 pdf_page_1_based 定位。
引用請同時提供資料版本、observation_id 與原官方來源及頁碼／正文定位。程式與文件的 MIT 不改變來源權利。
''').encode('utf-8')
    manifest = {'schema_version': 1, 'viewer_version': VIEWER_VERSION, 'dataset_version': version,
                'as_of': facts['as_of'], 'data': entries['data'], 'vocabulary': entries['vocabulary'],
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
