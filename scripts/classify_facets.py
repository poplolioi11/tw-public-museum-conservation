#!/usr/bin/env python3
"""Versioned, conservative search facets. Original evidence fields never change.

Tags describe wording in the reported metric, not standardized work per object.
Unknown completion labels require controller review before publishing.
"""
import json,re
from pathlib import Path

RULE_VERSION='1.2'
ACTION_LABELS={
 'restoration_as_reported':'修護／修復（依原報）',
 'maintenance':'保存維護／預防性保存',
 'arrangement':'整飭／整理',
 'inspection_registration':'檢視／登錄',
 'cleaning':'清潔／除塵／除膠等',
 'stabilization':'加固／搶救',
 'mounting':'裝裱／重新裝潢',
 'scientific_examination':'科學檢測',
 'digitization':'數位化／掃描',
 'digital_restoration':'純數位修復',
 'mixed_workflow':'原報混合作業／合計',
 'needs_review':'分類待核'}
COMPLETION_LABELS={
 'explicit_completed':'原文明載完成',
 'completion_from_context':'依段落／父項完成脈絡',
 'completed_at_stated_cutoff':'截至指定時點完成',
 'annual_execution_not_explicit':'年度執行，未明載完成',
 'in_progress':'進行中',
 'performed_activity':'活動已施作',
 'not_explicitly_stated':'未明載完成狀態',
 'needs_review':'狀態待核'}
COMPLETION_GROUPS={
 'explicit_completed':[
  'completed_explicit','explicit_completed','completed_as_reported','原文明載完成','原文明載修護完成',
  '原文明載111年完成全數20件','原文明載完成，但為混合合計'],
 'completion_from_context':[
  'completed_under_parent_statement','段落有完成總述；分項未另載完成',
  '年度已完成計畫之執行分項','已完成施政概述中的原報數，分項未另載完成'],
 'completed_at_stated_cutoff':['completed_as_of_stated_month','原文明載截至資料年底已完成'],
 'annual_execution_not_explicit':[
  'annual_actual_table_completion_not_explicit','annual_execution_reported',
  'annual_execution_reported_no_explicit_completed','annual_output_as_reported',
  'as_reported_annual_operation','annual_operation_listed',
  '原文稱館內處理數量，未另載逐件完成日','年度已處置敘述，未逐件另載完成日',
  '年度處置表，未逐件另載完成日','原文稱執行修護，未另載完成',
  '原文稱本年度辦理修護，未另載完成','本年度修護敘述，未另載完成',
  '年度已執行敘述，未另載完成','本計畫年度執行敘述，未另載完成',
  '原表為2020年年度件數，未另載完成用語；不由分類名完整修護推定完成。',
  '原表為年度件數，未另載完成用語；不由分類名完整修護推定完成。'],
 'in_progress':['進行處置；不可當已完成'],
 'performed_activity':['performed_as_reported'],
 'not_explicitly_stated':['not_explicitly_stated','未對此分項另載完成字樣','原文未另載完成']}
COMPLETION_MAP={raw:category for category,items in COMPLETION_GROUPS.items()for raw in items}

def action_categories(record):
    metric=record['metric_as_reported'];cls=record['metric_class'];tags=set()
    if '數位修復'in metric:tags.add('digital_restoration')
    elif re.search('修護|修復',metric):tags.add('restoration_as_reported')
    if re.search('維護|保存|預防性|薰蒸|燻蒸|除蟲',metric):tags.add('maintenance')
    if re.search('整飭|整理',metric):tags.add('arrangement')
    if re.search('檢視|巡檢|登錄|檢登',metric):tags.add('inspection_registration')
    # A treatment-table heading must not label its inspection subrow as treatment.
    # The 2025 actual-results source spelling 檢示 is preserved in the raw metric.
    if cls=='museum_reported_inspection':
        tags.discard('restoration_as_reported')
        tags.add('inspection_registration')
    if re.search('清潔|除塵|除膠|除黴',metric):tags.add('cleaning')
    if re.search('加固|搶救',metric):tags.add('stabilization')
    if re.search('裝裱|裝潢',metric+' '+cls):tags.add('mounting')
    if re.search('檢測|科學分析|科學檢測|XRF',metric):tags.add('scientific_examination')
    if re.search('數位化|數位掃描|數位影像|影像擷取',metric):tags.add('digitization')
    mixed_hints=('combined_','mixed_selection_maintenance','mixed_arrangement_restoration',
      '混合修護維護','修護與維護混合','修護及數位化混合','檢登數位化混合','原報混合合計')
    if any(hint in cls for hint in mixed_hints):tags.add('mixed_workflow')
    if cls=='mixed_arrangement_restoration':tags.update(['arrangement','restoration_as_reported','mixed_workflow'])
    if cls=='conservation_and_restoration_total':tags.add('mixed_workflow')
    if record['organization_id']=='BASE-007'and re.fullmatch(r'NMTH-20\d{2}-conservation-reported-total',record['observation_id']):tags.update(['restoration_as_reported','maintenance','stabilization','mixed_workflow'])
    # One procedure count may describe several operations; tags are never quantity splits.
    return sorted(tags or{'needs_review'})

def holding_scope_category(record):
    text=record['subject_scope']
    if re.search('館外.*(委託|受託)|館外受託',text):return 'external_service_as_reported'
    if re.search('國史館.*(委託|託管)|委託管理',text)and not re.search('本館及|本館與|混合',text):return 'entrusted_collection_as_reported'
    if re.search('混合|待入藏|未核|未另核|不列.*自藏|借展',text):return 'mixed_or_not_confirmed'
    if re.match('本館(藏品|典藏品|典藏作品|研究標本|家具|標本|典藏拼板舟|普通館藏)',text)or text.startswith('館藏作品（依藏品修護'):return 'own_collection_as_reported'
    return 'mixed_or_not_confirmed'

def facets(record):
    return {'action_categories':action_categories(record),
      'completion_category':COMPLETION_MAP.get(record['completion_status'],'needs_review'),
      'subject_scope_category':holding_scope_category(record),'classification_rule_version':RULE_VERSION}

def vocabulary():
    return {'rule_version':RULE_VERSION,'action_categories':ACTION_LABELS,'completion_categories':COMPLETION_LABELS,
      'holding_scope_categories':{'own_collection_as_reported':'原報本館藏品','entrusted_collection_as_reported':'原報託管藏品','external_service_as_reported':'原報館外受託服務','mixed_or_not_confirmed':'混合／權屬待核'},
      'limits':['分類是查詢標籤，不改寫原報詞、完成狀態或對象範圍。','同列可有多個作業標籤，未把原數字拆配到各標籤，也不證明每件均做所有作業。','修護／修復依原報廣義用語，不代表純修復或統一工作量。','原報本館藏品不代表本專案另做法律權屬調查。','未載逐件完成日期不代表未完成；分類只依保留的完成狀態文字，不另推進度。']}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('candidate',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    data=json.loads(a.candidate.read_text());unknown=[]
    for row in data['observations']:
        row.update(facets(row))
        if 'needs_review'in row['action_categories']or row['completion_category']=='needs_review':unknown.append({'id':row['observation_id'],'metric':row['metric_as_reported'],'completion_status':row['completion_status']})
    if unknown:raise SystemExit(json.dumps({'needs_controller_review':unknown},ensure_ascii=False))
    a.output.write_text(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'classified_rows':len(data['observations']),'rule_version':RULE_VERSION,'unknown_rows':len(unknown)},ensure_ascii=False))
