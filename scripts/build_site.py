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
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
VIEWER_VERSION = '1.5.0'
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
OPTIONAL_DOWNLOADS = {
    'preservation_texts': {
        'json': ('data/preservation_texts.json', '一般作業文字 JSON'),
        'csv': ('data/preservation_texts.csv', '一般作業文字 CSV'),
        'jsonl': ('data/preservation_texts.jsonl', '一般作業文字 JSONL'),
        'build': ('metadata/preservation_texts_build.json', '文字附表來源與範圍 JSON'),
    },
    'preservation_statistics': {
        'json': ('data/preservation_statistics.json', '環境作業原口徑 JSON'),
        'csv': ('data/preservation_statistics.csv', '環境作業原口徑 CSV'),
        'jsonl': ('data/preservation_statistics.jsonl', '環境作業原口徑 JSONL'),
        'build': ('metadata/preservation_statistics.json', '環境作業範圍與來源清單 JSON'),
    },
    'public_context': {
        'json': ('data/public_context_notes.json', '公立非年度量脈絡 JSON'),
        'jsonl': ('data/public_context_notes.jsonl', '公立非年度量脈絡 JSONL'),
        'csv': ('data/public_context_notes.csv', '公立非年度量脈絡 CSV'),
    },
    'private_art': {
        'json': ('data/private_art_pilot.json', '私立美術館試辦完整 JSON'),
        **{name + '_' + ext: ('data/' + name + '.' + ext, label + ' ' + ext.upper())
           for name, label in (
               ('private_art_observations', '私立館原報紀錄'),
               ('private_art_sources', '私立館來源清單'),
               ('private_art_body_reviews', '私立館有界核讀'),
               ('private_art_scope_notes', '私立館範圍註記'))
           for ext in ('csv', 'jsonl')},
        'build': ('metadata/private_art_pilot_build.json', '私立館試辦範圍與輸出清單 JSON'),
    },
}
CONSERVATION_LAYERS = {
    'public_followup': '既有公立館補查',
    'private_artist_museums': '私立藝術家／基金會館',
    'private_university_museums': '私立大學館／典藏中心',
    'private_university_other_museums': '私立大學其他博物館',
    'art_center_scope_candidates': '名稱與範圍候選',
}
CONSERVATION_PAGES = {
    'conservation_public': ('supplement-public.html', ('public_followup',)),
    'conservation_private': ('supplement-private.html', (
        'private_artist_museums', 'private_university_museums', 'private_university_other_museums')),
    'conservation_scope': ('supplement-scope.html', ('art_center_scope_candidates',)),
}
for module_key, (_, layer_keys) in CONSERVATION_PAGES.items():
    OPTIONAL_DOWNLOADS[module_key] = {
        layer + '_' + ext: ('data/conservation_supplement/' + layer + '.' + ext,
                            CONSERVATION_LAYERS[layer] + ' ' + ext.upper())
        for layer in layer_keys for ext in ('json', 'csv', 'jsonl')}
    OPTIONAL_DOWNLOADS[module_key]['build'] = (
        'metadata/conservation_supplement_build.json', '補充附表版本、範圍與輸出清單 JSON')
DOWNLOAD_BASENAMES = {'metadata/preservation_statistics.json': 'preservation_statistics_build.json'}
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
    names += ['site-src/' + name for name in ('index.html', 'enrichment.html', 'context.html',
                                             'private-art.html', 'preservation.html', 'preservation-texts.html',
                                             'supplement-public.html', 'supplement-private.html',
                                             'supplement-scope.html', 'supplement.js', 'app.css', 'app.js')]
    names += [path for path, _ in ENRICHMENT_DOWNLOADS.values()]
    names += ['metadata/inventory.json', 'schema/absence_annotation.schema.json',
              'schema/normalization_record.schema.json']
    names += ['docs/figures/' + name for name in FIGURES]
    names += [path for group in OPTIONAL_DOWNLOADS.values() for path, _ in group.values()
              if (root / path).is_file()]
    return {name: (root / name).read_bytes() for name in names}


def safe_old_path(name):
    fixed = {'data/' + Path(path).name for path, _ in ENRICHMENT_DOWNLOADS.values()}
    fixed |= {'data/' + DOWNLOAD_BASENAMES.get(path, Path(path).name) for group in OPTIONAL_DOWNLOADS.values()
              for path, _ in group.values()}
    fixed |= {'figures/' + name for name in FIGURES}
    return name in fixed or bool(re.fullmatch(r'data/[a-f0-9]{64}\.json|records/[A-Za-z0-9._-]+\.json', name))


def source_link(source, row):
    """Link only declared public official URLs; never copy an original."""
    url = source.get('official_file_url') or source.get('official_landing_url') or ''
    if not re.match(r'^https?://[^/\s]+', url):
        raise ValueError('Missing public official source URL: ' + str(row.get('source_id')))
    page = row.get('pdf_page_1_based')
    if page is not None:
        url = url.split('#', 1)[0] + '#page=' + str(page)
        locator = 'PDF ' + str(page) + '／印 ' + str(row.get('printed_page') or '未列')
    else:
        locator = row.get('source_locator') or '官方正文'
    return ('<a href="' + escape(url, quote=True) + '">' + escape(locator) + '</a>'
            '<span class="supplement-source-id mono">' + escape(row.get('source_id', '')) + '</span>')


def supplemental_pages(inputs, facts, vocabulary, version, outputs):
    """Render two separate optional public-source layers without merging facts."""
    sources = {s['source_id']: s for s in facts['sources']}
    entries = {}
    context_labels = {'planned_quantity': '計畫／優先對象', 'undated_cumulative': '未定統計期的累計',
        'multi_year_average': '長期平均', 'non_numeric_completed_project': '跨年完成專案脈絡',
        'narrative_maintenance': '維護敘述', 'case_completion_year_not_established': '完成年度未確立的個案'}
    review_labels = {'numeric_observations_verified': '有原報數值（仍依分項限制）',
        'body_read_no_eligible_quantity_located': '指定正文已讀，未定位適用量',
        'annual_scope_not_separable': '年度或對象範圍無法分離',
        'source_found_body_not_reviewed': '適用正文待核',
        'source_not_located_in_this_search': '本輪未定位適用來源',
        'outside_selected_scope': '不在本次採用範圍'}

    def downloads_for(key):
        downloads = {}
        for name, (path, label) in OPTIONAL_DOWNLOADS[key].items():
            if path not in inputs:
                continue
            body = inputs[path]
            dest = 'data/' + DOWNLOAD_BASENAMES.get(path, Path(path).name)
            if dest in outputs and outputs[dest] != body:
                raise ValueError('Supplement download path collision: ' + dest)
            outputs[dest] = body
            downloads[name] = {'url': dest, 'download_url': './' + dest, 'label': label,
                               'source_path': path, 'sha256': sha(body), 'bytes': len(body)}
        return downloads

    def render(key, filename, content, available, count):
        downloads = downloads_for(key) if available else {}
        links = ('<ul>' + ''.join('<li><a href="./' + escape(d['url'], quote=True) + '">' +
            escape(d['label']) + '</a> <span class="download-size">（' + str(d['bytes']) +
            ' bytes）</span></li>' for d in downloads.values()) + '</ul>') if downloads else '<p>此版本沒有可下載的本層資料檔。</p>'
        body = inputs['site-src/' + filename].decode()
        for marker, value in {'__DATASET_VERSION__': escape(version), '__AS_OF__': escape(facts['as_of']),
                              '__MODULE_CONTENT__': content, '__DOWNLOAD_LINKS__': links}.items():
            if marker not in body:
                raise ValueError('Supplement HTML marker missing: ' + marker)
            body = body.replace(marker, value)
        if re.search(r'__[A-Z_]+__', body):
            raise ValueError('Unresolved supplement HTML marker')
        outputs[filename] = body.encode()
        entries[key] = {'available': available, 'record_count': count if available else None,
            'page': {'url': filename, 'sha256': sha(outputs[filename]), 'bytes': len(outputs[filename])},
            'data': downloads.get('json'), 'downloads': downloads,
            'included_in_public_numeric_observations': False,
            'included_in_public_coverage_denominators': False}

    text_path = OPTIONAL_DOWNLOADS['preservation_texts']['json'][0]
    if text_path in inputs:
        text_records = json.loads(inputs[text_path])['records']
        text_rows = []
        for row in text_records:
            if row['measure_status'] != 'text_only' or row['numeric_quantity_eligible'] is not False or row['annual_quantity_eligible'] is not False or row['default_aggregation_allowed'] is not False:
                raise ValueError('General text layer cannot become numeric or annual quantity')
            source = sources[row['source_id']]
            if source['official_file_url'].startswith('https://digital.ceramics.ntpc.gov.tw/zh-tw/eLibrary/'):
                source_reference = ('<a href="'+escape(source['official_file_url'],quote=True)+'">官方年報入口</a>'
                    '<p>'+escape('下載原PDF後看第'+str(row['pdf_page_1_based'])+'頁／印'+str(row['printed_page']))+'</p>'
                    '<span class="supplement-source-id mono">'+escape(row['source_id'])+'</span>')
            else:
                source_reference = source_link(source,row)
            text_rows.append('<tr id="'+escape(row['text_id'],quote=True)+'"><th scope="row">'+
                escape(row['organization_name'])+'<p>'+escape(row['source_subject_label'])+'</p></th><td>'+
                escape(row['statement'])+'</td><td>'+escape('報告年：'+str(row['report_year']) if row['report_year'] is not None else '非年報來源；不填報告年')+
                '<p>'+escape(row['period_as_reported'])+'</p></td><td>'+escape(row['scope_note'])+'</td><td>'+
                source_reference+'<p>'+escape(row['source_locator'])+'</p></td></tr>')
        content = ('<div class="table-wrap" tabindex="0" role="region" aria-label="一般作業文字表，可橫向捲動">'
            '<table><caption>'+str(len(text_rows))+'則官方一般作業文字；列數不是人數、物件數或作業量</caption>'
            '<thead><tr><th scope="col">查找館所與原文對象</th><th scope="col">一般作業說明</th>'
            '<th scope="col">報告年與期間限制</th><th scope="col">範圍界線</th><th scope="col">官方來源定位</th></tr></thead>'
            '<tbody>'+''.join(text_rows)+'</tbody></table></div>')
        render('preservation_texts','preservation-texts.html',content,True,len(text_rows))

    statistics_path = OPTIONAL_DOWNLOADS['preservation_statistics']['json'][0]
    if statistics_path in inputs:
        statistics = json.loads(inputs[statistics_path])['records']
        labels = {'report_year_table': '原表年度', 'report_year_context': '只有年報脈絡；觀測年未明',
                  'up_to_end_start_unspecified': '只有截止時點；起點未明',
                  'after_installation_end_unspecified': '建置後；起訖未明'}
        rows = []
        for row in statistics:
            if row['default_aggregation_allowed'] is not False or row['source_id'] not in sources:
                raise ValueError('Invalid separate environmental statistics scope')
            rows.append('<tr id="'+escape(row['statistics_id'],quote=True)+'"><th scope="row">'+
                escape(str(row['report_year'])+'｜'+row['metric_as_reported'])+'</th><td>'+escape(
                row['quantity_raw']+' '+row['unit_as_reported'])+'</td><td>'+escape(labels[row['period_kind']]+
                '；'+row['period_evidence'])+'</td><td>'+escape(row['scope_note'])+'</td><td>'+
                source_link(sources[row['source_id']],row)+'<p>'+escape(row['source_locator'])+'</p></td></tr>')
        content = ('<div class="table-wrap" tabindex="0" role="region" aria-label="環境作業原口徑表，可橫向捲動">'
            '<table><caption>國立故宮博物院｜'+str(len(rows))+'則；報告年不一律等於觀測年，列數不是作業總量</caption>'
            '<thead><tr><th scope="col">報告年與原作業</th><th scope="col">原數字與單位</th>'
            '<th scope="col">期間證據</th><th scope="col">限制</th><th scope="col">官方原頁與列欄</th></tr></thead>'
            '<tbody>'+''.join(rows)+'</tbody></table></div>')
        render('preservation_statistics','preservation.html',content,True,len(rows))

    context_path = OPTIONAL_DOWNLOADS['public_context']['json'][0]
    if context_path in inputs:
        notes = json.loads(inputs[context_path])
        if not isinstance(notes, list) or any(n.get('annual_quantity_eligible') is not False or
                n.get('default_aggregation_allowed') is not False for n in notes):
            raise ValueError('Public context must remain non-annual and non-aggregating')
        rows = []
        for n in notes:
            if n['source_id'] not in sources:
                raise ValueError('Unresolved public-context source: ' + n['note_id'])
            rows.append('<tr><th scope="row">' + escape(n['organization_name']) +
                '<span class="period-label">' + escape(n.get('reporting_period_raw') or '期間未明列') +
                '</span></th><td><span class="badge">' + escape(context_labels.get(n['context_kind'], n['context_kind'])) +
                '</span><p>' + escape(n['statement_as_reported']) + '</p></td><td>' +
                escape(n['interpretation_note']) + '</td><td>' + source_link(sources[n['source_id']], n) + '</td></tr>')
        content = '<p>本版列出 ' + str(len(notes)) + ' 則來源脈絡；則數不是修護物件數。</p>'
        content += ('<div class="table-wrap" tabindex="0" role="region" aria-label="公立脈絡表，可橫向捲動"><table class="supplement-table"><caption>保留原句與期間；計畫數、累計、平均及跨年專案不等於年度已施作量</caption><thead><tr><th scope="col">館所／原報期間</th><th scope="col">原報脈絡</th><th scope="col">解讀界線</th><th scope="col">官方來源</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>') if rows else '<p>本版本未列脈絡紀錄，不表示館所沒有保存工作。</p>'
        render('public_context', 'context.html', content, True, len(notes))
    else:
        render('public_context', 'context.html', '<p class="notice">此資料版本尚未納入公立非年度量脈絡檔；這是版本範圍，不是零修護。</p>', False, 0)

    private_path = OPTIONAL_DOWNLOADS['private_art']['json'][0]
    if private_path in inputs:
        data = json.loads(inputs[private_path])
        if data.get('dataset_version') != version or data.get('scope') != 'private_art_museum_pilot' or data.get('public_baseline_eligible') is not False:
            raise ValueError('Private-art data version or separate-scope declaration differs')
        for key in ('observations', 'sources', 'body_reviews', 'scope_notes'):
            if not isinstance(data.get(key), list):
                raise ValueError('Private-art list missing: ' + key)
        private_sources = {s['source_id']: s for s in data['sources']}
        rows = []
        for o in data['observations']:
            if o['source_id'] not in private_sources or o.get('default_aggregation_allowed') is not False:
                raise ValueError('Unresolved or aggregating private-art observation')
            period = o.get('reporting_period_raw') or (str(o['data_year']) if o.get('data_year') is not None else '年度未明列')
            raw = o.get('quantity_raw')
            quantity = '原文未列數量' if raw is None else str(raw)
            unit = o.get('unit_as_reported') or '單位未列'
            completion = vocabulary.get('completion_categories', {}).get(o.get('completion_category'), o.get('completion_category') or '狀態未分類')
            holding = vocabulary.get('holding_scope_categories', {}).get(o.get('subject_scope_category'), o.get('subject_scope_category') or '範圍未分類')
            rows.append('<tr><th scope="row">' + escape(o['organization_name']) + '<span class="period-label">' + escape(period) +
                '</span></th><td><strong>' + escape(o['metric_as_reported']) + '</strong><p class="quantity">' + escape(quantity) +
                '<span class="quantity-unit">' + escape(unit) + '</span></p><span class="mono">' + escape(o['observation_id']) +
                '</span></td><td>' + escape(completion) + '<p class="period-label">原狀態：' + escape(o.get('completion_status') or '未列') +
                '</p></td><td><span class="badge">' + escape(holding) + '</span><p>' + escape(o.get('subject_scope') or '未列') +
                '</p><p>' + escape(o.get('source_scope') or '') + '</p><p>' + escape(o['interpretation_note']) +
                '</p></td><td>' + source_link(private_sources[o['source_id']], o) + '</td></tr>')
        content = '<p>本版有 ' + str(len(data['observations'])) + ' 列原報紀錄、' + str(len(data['body_reviews'])) + ' 則有界核讀；列數與則數都不是修護物件總數。</p>'
        content += ('<div class="table-wrap" tabindex="0" role="region" aria-label="私立館原報紀錄，可橫向捲動"><table class="supplement-table private-records"><caption>各列保持原值、原單位、完成狀態及對象範圍；不作年度或館際加總</caption><thead><tr><th scope="col">館所／期間</th><th scope="col">作業與原報數量</th><th scope="col">完成狀態</th><th scope="col">對象範圍與解讀界線</th><th scope="col">官方來源</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>') if rows else '<p>本版尚無採入的私立館數值紀錄；不表示零修護。</p>'
        content += '<h3 class="supplement-subheading">年度核讀與未採原因</h3><p>未列年份只表示本版尚未納入適用核讀，不補成零；同年有分項量也不代表全年範圍已完整。</p>'
        for r in data['body_reviews']:
            content += '<details class="review-entry"><summary>' + escape(r['organization_name'] + '／' + str(r['target_data_year']) + '｜' + review_labels.get(r['review_status'], r['review_status'])) + '</summary><div class="review-body"><p>' + escape(r['review_scope']) + '</p><p>' + escape(r['interpretation_note']) + '</p></div></details>'
        if data['scope_notes']:
            content += '<h3 class="supplement-subheading">保留的範圍註記</h3><ul>' + ''.join('<li>' + escape(n['note']) + '</li>' for n in data['scope_notes']) + '</ul>'
        render('private_art', 'private-art.html', content, True, len(data['observations']))
    else:
        render('private_art', 'private-art.html', '<p class="notice">此資料版本尚未納入私立美術館試辦資料；未與公立館資料合併，也不表示零修護。</p>', False, 0)
    return entries


def conservation_supplement_pages(inputs, facts, version, outputs):
    """Render source-linked facts by separate layer; never merge into main observations."""
    paths = {key: 'data/conservation_supplement/' + key + '.json'
             for key in CONSERVATION_LAYERS}
    present = {key for key, path in paths.items() if path in inputs}
    if present and present != set(paths):
        raise ValueError('Incomplete conservation supplement layers; retain every separate container')
    data = {}
    for key in present:
        layer = json.loads(inputs[paths[key]])
        if (layer.get('schema_version') != '1.0' or layer.get('dataset_version') != version or
                layer.get('layer') != key or layer.get('public_baseline_eligible') is not False):
            raise ValueError('Conservation supplement version or scope differs: ' + key)
        for field in ('institutions', 'sources', 'records'):
            if not isinstance(layer.get(field), list):
                raise ValueError('Conservation supplement list missing: ' + key + '/' + field)
        data[key] = layer

    def text(value, fallback='未明列'):
        return escape(fallback if value is None or value == '' else str(value))

    def public_url(value):
        if not isinstance(value, str):
            raise ValueError('Conservation supplement requires a public source URL')
        parsed = urlsplit(value)
        if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('Unsafe conservation supplement URL')
        return value

    def source_reference(source, row):
        url = public_url(row.get('source_url') or source.get('url'))
        page = row.get('pdf_page_1_based')
        if page is not None:
            if type(page) is not int or page < 1:
                raise ValueError('Invalid conservation supplement PDF page')
            url = url.split('#', 1)[0] + '#page=' + str(page)
            locator = 'PDF ' + str(page) + '／印 ' + str(row.get('printed_page') or '未列')
        else:
            locator = row.get('source_locator') or '官方正文'
        return ('<a href="' + escape(url, quote=True) + '">' + text(source.get('title'), '官方來源') +
                '</a><p>' + text(locator) + '</p><span class="supplement-source-id mono">' +
                text(row['source_id']) + '</span>')

    def record_html(row, key, sources):
        ident = row.get('record_id')
        if not isinstance(ident, str) or not re.fullmatch(r'[A-Za-z0-9._-]+', ident):
            raise ValueError('Unsafe conservation supplement record ID')
        if row.get('default_aggregation_allowed') is not False or row.get('human_verified') is not False:
            raise ValueError('Conservation supplement aggregation or human-review claim differs')
        kind = row.get('record_kind')
        if kind not in ('quantity_record', 'text_record') or row.get('source_id') not in sources:
            raise ValueError('Conservation supplement kind or source reference differs: ' + ident)
        year = row.get('data_year')
        if year is not None and (type(year) is not int or not 1800 <= year <= 2200):
            raise ValueError('Invalid conservation supplement activity year')
        period = '<p><strong>作業年：' + text(year, '未知／未分配') + '</strong></p>'
        period += '<p>' + text(row.get('period_label') or row.get('reporting_period_raw'), '作業起訖未明列') + '</p>'
        if row.get('period_start') or row.get('period_end'):
            period += '<p>作業區間：' + text(row.get('period_start'), '起點未知') + ' 至 ' + text(row.get('period_end'), '終點未知') + '</p>'
        if row.get('as_of_date'):
            period += '<p>時間界線：' + text(row['as_of_date']) + '</p><p class="period-label">日期依據：' + text(row.get('as_of_date_basis'), '來源快照或截止日，依期間說明判讀') + '</p>'
        if row.get('report_date'):
            period += '<p>報告日期：' + text(row['report_date']) + '</p>'
        elif row.get('report_context_year') is not None:
            period += '<p>報告脈絡年：' + text(row['report_context_year']) + '</p>'
        if row.get('publication_date') or row.get('publication_year') is not None:
            period += '<p>發布時間：' + text(row.get('publication_date') or row.get('publication_year')) + '</p>'
        activity = '<strong>' + text(row.get('metric_label')) + '</strong>'
        if kind == 'quantity_record':
            raw = str(row.get('quantity_raw') or '')
            unit = str(row.get('unit_as_reported') or '')
            parts = re.findall(r'[\u4e00-\u9fff]+', unit)
            unit_text = '' if parts and all(part in raw for part in parts) else text(unit, '量詞未明列')
            activity += '<p class="quantity">' + text(row.get('quantity_raw'), '原數字未明列') + '<span class="quantity-unit">' + unit_text + '</span></p>'
        else:
            activity += '<p><span class="badge">文字紀錄</span></p><p>' + text(row.get('text_summary')) + '</p>'
        activity += '<p class="period-label">原完成語：' + text(row.get('completion_status')) + '</p>'
        notes = '<p>' + text(row.get('subject_scope'), '對象範圍依來源段落') + '</p><p>' + text(row.get('interpretation_note'), '依來源範圍閱讀，不作加總。') + '</p>'
        details = []
        for label, field in (('期間依據', 'period_basis'), ('原報期間', 'reporting_period_raw'),
                             ('委託單位', 'commissioning_organization'), ('執行單位', 'executing_organization'),
                             ('關聯館所', 'associated_institution')):
            if row.get(field):
                details.append('<dt>' + label + '</dt><dd>' + text(row[field]) + '</dd>')
        if details:
            notes += '<details class="supplement-record-details"><summary>期間依據與角色</summary><dl>' + ''.join(details) + '</dl></details>'
        evidence = row.get('period_evidence') or []
        if not isinstance(evidence, list):
            raise ValueError('Conservation supplement period evidence must be a list')
        if evidence:
            references = []
            for item in evidence:
                if item.get('source_id') not in sources:
                    raise ValueError('Unresolved conservation supplement period source')
                references.append('<li>' + source_reference(sources[item['source_id']], item) +
                                  '<p>' + text(item.get('basis'), '只作期間旁證，不取代原量值來源。') + '</p></li>')
            notes += '<details class="supplement-period-evidence"><summary>期間旁證與原頁</summary><ul>' + ''.join(references) + '</ul></details>'
        return ('<tr id="' + escape(ident, quote=True) + '" data-supplement-record data-layer="' + key +
                '" data-organization="' + escape(row['organization_id'], quote=True) + '" data-kind="' + kind +
                '" data-year="' + (str(year) if year is not None else 'unknown') + '"><th scope="row">' +
                text(row['organization_name']) + '<span class="supplement-source-id mono">' + text(ident) +
                '</span></th><td>' + activity + '</td><td>' + period + '</td><td>' + notes + '</td><td>' +
                source_reference(sources[row['source_id']], row) + '</td></tr>')

    entries = {}
    for module_key, (filename, layer_keys) in CONSERVATION_PAGES.items():
        downloads = {}
        if present:
            for key, (path, label) in OPTIONAL_DOWNLOADS[module_key].items():
                if path not in inputs:
                    continue
                body = inputs[path]
                dest = 'data/' + Path(path).name
                if dest in outputs and outputs[dest] != body:
                    raise ValueError('Conservation supplement download path collision: ' + dest)
                outputs[dest] = body
                downloads[key] = dict(url=dest, download_url='./' + dest, label=label,
                                      source_path=path, sha256=sha(body), bytes=len(body))
        layers = {}
        sections = []
        institutions = {}
        years = set()
        ids = set()
        total = 0
        for key in layer_keys:
            layer = data.get(key)
            if layer is None:
                continue
            sources = {s['source_id']: s for s in layer['sources']}
            if len(sources) != len(layer['sources']):
                raise ValueError('Duplicate conservation supplement source')
            layer_orgs = {o['organization_id']: o for o in layer['institutions']}
            if len(layer_orgs) != len(layer['institutions']):
                raise ValueError('Duplicate conservation supplement institution')
            institutions.update(layer_orgs)
            rows = []
            for row in layer['records']:
                if row.get('organization_id') not in layer_orgs or row.get('record_id') in ids:
                    raise ValueError('Unresolved or duplicate conservation supplement record')
                ids.add(row['record_id'])
                years.add(str(row['data_year']) if row.get('data_year') is not None else 'unknown')
                rows.append(record_html(row, key, sources))
            total += len(rows)
            cards = []
            for org in layer['institutions']:
                name = text(org['organization_name'])
                if org.get('official_url'):
                    name = '<a href="' + escape(public_url(org['official_url']), quote=True) + '">' + name + '</a>'
                identity = ''
                if org.get('identity_source_url'):
                    identity = '<p><a href="' + escape(public_url(org['identity_source_url']), quote=True) + '">身分來源</a>'
                    if org.get('identity_locator'):
                        identity += '：' + text(org['identity_locator'])
                    identity += '</p>'
                    if org.get('identity_source_id'):
                        identity += '<span class="supplement-source-id mono">' + text(org['identity_source_id']) + '</span>'
                cards.append('<li data-supplement-institution data-layer="' + key + '" data-organization="' +
                    escape(org['organization_id'], quote=True) + '"><strong>' + name + '</strong><p>' +
                    text(org.get('scope_note'), '本版僅列已核對的有限來源；未列量值不表示零。') + '</p>' + identity + '</li>')
            section = ('<section class="supplement-layer" data-supplement-layer="' + key + '"><h3>' +
                CONSERVATION_LAYERS[key] + '</h3><p>' + str(len(rows)) +
                '則本層紀錄；列數不是物件量或年度總量。館所清單保留沒有採入量值的單位。</p>' +
                '<ul class="supplement-institutions">' + ''.join(cards) + '</ul>')
            if rows:
                section += ('<div class="table-wrap" tabindex="0" role="region" aria-label="' + CONSERVATION_LAYERS[key] +
                    '紀錄表，可橫向捲動"><table class="supplement-table conservation-records"><caption>' +
                    CONSERVATION_LAYERS[key] + '：原量詞、期間與來源；不相加，不與公立主表合併</caption>' +
                    '<thead><tr><th scope="col">館所與紀錄</th><th scope="col">作業與原報數量／文字</th>' +
                    '<th scope="col">作業年與報告時間</th><th scope="col">範圍與解讀界線</th>' +
                    '<th scope="col">官方來源定位</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')
            else:
                section += '<p class="notice">本層尚無採入的量值或文字紀錄；館所身分與來源缺口另列，不表示零修護。</p>'
            sections.append(section + '</section>')
            layers[key] = dict(label=CONSERVATION_LAYERS[key], institution_count=len(layer['institutions']),
                               record_count=len(rows), data=downloads.get(key + '_json'),
                               downloads={k: v for k, v in downloads.items() if k.startswith(key + '_')},
                               included_in_public_coverage_denominators=False)
        controls = ('<form id="supplement-filter-form" class="supplement-controls" role="search" aria-label="補充紀錄篩選">'
            '<div class="filter-grid"><div><label for="supplement-search">館名、作業或來源文字</label>'
            '<input id="supplement-search" type="search" placeholder="例如：點檢、送裱、華岡" autocomplete="off"></div>'
            '<div><label for="supplement-layer">資料分層</label><select id="supplement-layer"><option value="">本頁全部分層</option>' +
            ''.join('<option value="' + key + '">' + CONSERVATION_LAYERS[key] + '</option>' for key in layer_keys if key in data) +
            '</select></div><div><label for="supplement-organization">館所</label><select id="supplement-organization">'
            '<option value="">本頁全部館所</option>' + ''.join('<option value="' + escape(ident, quote=True) + '">' +
            text(org['organization_name']) + '</option>' for ident, org in institutions.items()) +
            '</select></div><div><label for="supplement-kind">紀錄類型</label><select id="supplement-kind">'
            '<option value="">量值與文字</option><option value="quantity_record">帶量值紀錄</option>'
            '<option value="text_record">文字紀錄</option></select></div><div><label for="supplement-year">作業年</label>'
            '<select id="supplement-year"><option value="">全部作業年</option>' +
            ''.join('<option value="' + year + '">' + ('未知／未分配' if year == 'unknown' else year) + '</option>'
                    for year in sorted(years, key=lambda y: (y == 'unknown', y))) +
            '</select><span class="hint">依作業年篩選，報告年不代填。</span></div></div>'
            '<div class="form-actions"><button type="reset" class="secondary">清除篩選</button></div></form>'
            '<p id="supplement-result-count" role="status" aria-live="polite">本頁' + str(total) +
            '則紀錄；數量不可直接加總。</p><p id="supplement-empty" class="notice" hidden>目前條件沒有相應紀錄；不代表零修護或沒有公開資料。</p>'
            '<noscript><p class="notice">未啟用JavaScript，以下仍完整列出本頁來源事實與館所；可用瀏覽器尋找文字。</p></noscript>')
        content = controls + ''.join(sections) if present else '<p class="notice">此版本尚未納入分層補充資料；不是零修護。</p>'
        links = '<ul>' + ''.join('<li><a href="./' + escape(d['url'], quote=True) + '">' +
            escape(d['label']) + '</a> <span class="download-size">（' + str(d['bytes']) + ' bytes）</span></li>'
            for d in downloads.values()) + '</ul>' if downloads else '<p>此版本沒有本層下載檔案。</p>'
        template = inputs['site-src/' + filename].decode()
        for marker, value in {'__DATASET_VERSION__': escape(version), '__AS_OF__': escape(facts['as_of']),
                              '__MODULE_CONTENT__': content, '__DOWNLOAD_LINKS__': links}.items():
            if marker not in template:
                raise ValueError('Conservation supplement template marker missing: ' + marker)
            template = template.replace(marker, value)
        if re.search(r'__[A-Z_]+__', template):
            raise ValueError('Unresolved conservation supplement HTML marker')
        outputs[filename] = template.encode()
        entries[module_key] = dict(available=bool(present), record_count=total if present else None,
            page=dict(url=filename, sha256=sha(outputs[filename]), bytes=len(outputs[filename])),
            layers=layers, downloads=downloads, included_in_public_numeric_observations=False,
            included_in_public_coverage_denominators=False)
    return entries


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
    supplements = supplemental_pages(inputs, facts, vocabulary, version, outputs)
    supplements.update(conservation_supplement_pages(inputs, facts, version, outputs))
    template = inputs['site-src/index.html'].decode()
    if '__DATASET_VERSION__' not in template:
        raise ValueError('HTML dataset-version marker missing')
    outputs['index.html'] = template.replace('__DATASET_VERSION__', version).encode()
    for name in ('app.css', 'app.js', 'supplement.js'):
        outputs[name] = inputs['site-src/' + name]
    outputs['.nojekyll'] = b''
    outputs['llms.txt'] = (f'''# 臺灣公立館保存修護公開資料索引

資料版本 {version}；資料截點 {facts['as_of']}。這是有限來源子集，不是全國完整修護統計。

- [資料清單](manifest.json)：完整 JSON 的相對路徑、SHA-256、bytes、版本及逐筆入口。
- [本版完整公開事實]({entries['data']['url']})：observations、sources、relations、body_reviews 與範圍摘要。
- [分類詞彙]({entries['vocabulary']['url']})：分類標籤及使用限制。
- [有界資料整理](enrichment.html)：館年格全集與年份子集、缺量註記、關係及完成語覆核、文字表格與圖表。
- [公立非年度量脈絡](context.html)：計畫、累計、平均與跨年專案，並非年度已施作量，不納入公立數值觀測。
- [私立美術館試辦](private-art.html)：獨立資料層，保留原值、原單位、完成狀態與範圍，不混入公立觀測或分母。
- [官方環境作業附表](preservation.html)：原數字、複合單位及期間證據另列；不進修護主表或公立分母，不作年度趨勢。
- [一般保存作業文字](preservation-texts.html)：官方環控、系統支援、作業角色與流程；不填人數或待修量，不進主表與公立分母。
- [公立館補查附表](supplement-public.html)：既有館所的限定作業記載，保留作業年、報告時間與累計界線，不進原公立分母。
- [私立館分層補充](supplement-private.html)：藝術家／基金會館、私立大學館及其他館分檔，原朱銘試辦仍另列。
- [名稱與範圍候選](supplement-scope.html)：機構名稱或採用範圍待釐清的獨立索引，不計入美術館數。
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
manifest.json 的 public_context 與 private_art 各列 available、page、data 及 downloads；未納入的舊版本以 available=false 表示，不能解讀為零修護。
新增層的下載入口保留輸入原始bytes；每個已採端點都有SHA-256與bytes。站點讀回須逐一核對這兩層的頁面與downloads，不能只核公立facts。
conservation_public、conservation_private、conservation_scope各有獨立page、layers與downloads；layers以分層ID連結JSON、CSV、JSONL，不把私立補充併進公立facts或coverage。HTML直接列出必要事實及來源，JavaScript只篩選已列文字。data_year未知不由report_date、report_context_year或publication_year代填；period_label、period_start、period_end及as_of_date各按來源證據保留，不保證全年完整。
''' + '\n'.join('- [' + d['label'] + '](' + d['url'] + ')' for d in enrichment['downloads'].values()) + '\n' +
        '\n'.join('- [' + d['label'] + '](' + d['url'] + ')' for d in enrichment['figures'].values()) + '\n' +
        '\n'.join('- [' + d['label'] + '](' + d['url'] + ')' for module in supplements.values()
                  for d in module['downloads'].values()) + '\n').encode('utf-8')
    manifest = {'schema_version': 1, 'viewer_version': VIEWER_VERSION, 'dataset_version': version,
                'as_of': facts['as_of'], 'data': entries['data'], 'vocabulary': entries['vocabulary'],
                'enrichment': enrichment,
                **supplements,
                'readback_contract': {
                    'optional_module_keys': ['public_context', 'private_art', 'preservation_statistics', 'preservation_texts',
                                             'conservation_public', 'conservation_private', 'conservation_scope'],
                    'verify_page_and_each_download': True,
                    'compare_sha256_and_bytes': True,
                    'public_private_denominators_separate': True,
                    'original_source_files_redistributed': False},
                'repository_url': REPOSITORY, 'record_url_template': './records/{observation_id}.json',
                'inputs_sha256': {name: sha(body) for name, body in inputs.items()},
                'scope_note': '有限來源目錄；紀錄筆數不是物件總數，未作年度或館際加總。',
                'generated_files': sorted(outputs)}
    def verify_endpoint_claims(value):
        if isinstance(value, dict):
            if {'url', 'sha256', 'bytes'} <= value.keys():
                body = outputs.get(value['url'])
                if body is None or sha(body) != value['sha256'] or len(body) != value['bytes']:
                    raise ValueError('Manifest endpoint bytes differ: ' + str(value['url']))
            for item in value.values():
                verify_endpoint_claims(item)
        elif isinstance(value, list):
            for item in value:
                verify_endpoint_claims(item)
    verify_endpoint_claims(manifest)
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
