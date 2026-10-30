#!/usr/bin/env python3
"""Validate bounded original-page completion assessments without changing facts."""
from pathlib import Path
from collections import Counter
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
LABELS={
 'explicit_item_completion_supported':'指定分項有直接完成語',
 'parent_context_supported':'父句或總述的完成脈絡可支持',
 'completion_not_explicit_in_read_scope':'所讀範圍未定位明確完成語',
 'completion_scope_ambiguous':'完成語適用範圍仍不明',
 'source_unavailable_for_this_review':'本輪原件未能核讀'}
def encode(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(x):return hashlib.sha256(canonical(x)).hexdigest()
def read(p):return json.loads(p.read_text())
def generate(facts,root=ROOT,shape_validator=None):
 if shape_validator is None:
  from build_exports import validate_review_shape
  shape_validator=validate_review_shape
 rows=read(root/'data/completion_reviews.json');rules=read(root/'metadata/completion_review_rules.json')
 assert set(rules)=={'rule_version','input_manifest','assessment_labels','limits'},'completion_rule_fields'
 assert rules['rule_version']=='1.0'and rules['assessment_labels']==LABELS,'completion_rule_vocabulary'
 manifest=rules['input_manifest'];assert set(manifest)=={'facts_source','reviews_source','reviewed_observation_ids','observations_sha256','reviews_sha256'},'completion_manifest_fields'
 assert manifest['facts_source']=='data/facts.json#observations'and manifest['reviews_source']=='data/completion_reviews.json','completion_manifest_source'
 assert digest(facts['observations'])==manifest['observations_sha256'],'completion_original_observations_changed'
 assert digest(rows)==manifest['reviews_sha256'],'completion_unreviewed_assessment_changed'
 observations={o['observation_id']:o for o in facts['observations']};sources={s['source_id']:s for s in facts['sources']}
 target={o['observation_id']for o in facts['observations']if o['completion_category']=='completion_from_context'}
 assert set(manifest['reviewed_observation_ids'])==target and len(manifest['reviewed_observation_ids'])==len(target),'completion_manifest_target'
 assert len(rows)==len(target)and {r['observation_id']for r in rows}==target,'completion_review_target_closure'
 assert len({r['review_id']for r in rows})==len(rows),'completion_duplicate_review_id'
 schema=read(root/'schema/completion_review.schema.json')
 for row in rows:
  shape_validator(row,schema,row['review_id']);o=observations[row['observation_id']];s=sources[o['source_id']]
  assert (row['source_id'],row['original_file_sha256'],row['original_completion_status'],row['original_completion_category'])==(o['source_id'],s['original_file_sha256'],o['completion_status'],o['completion_category']),'completion_wrong_source_or_original_value'
  assert row['pdf_pages_1_based']==sorted(set(row['pdf_pages_1_based'])),'completion_duplicate_or_unsorted_page'
  pp=set(row['pdf_pages_1_based']);tt=set(row['text_read_pdf_pages_1_based']);ii=set(row['image_viewed_pdf_pages_1_based'])
  assert tt<=pp and ii<=pp,'completion_evidence_outside_reviewed_pages'
  if s.get('original_file_pdf_pages'):assert all(p<=s['original_file_pdf_pages']for p in pp),'completion_page_beyond_source'
  if row['assessment']!='source_unavailable_for_this_review':
   assert o['pdf_page_1_based']in pp and ii,'completion_missing_original_page_or_reading'
   assert row['evidence_basis']=='new_selected_original_page_reading','completion_reading_basis'
  if row['assessment']in {'explicit_item_completion_supported','parent_context_supported'}:
   assert row['completion_phrase_raw']and len(row['completion_phrase_raw'])<=48,'completion_missing_or_long_phrase'
  else:assert len(row['completion_phrase_raw'])<=48,'completion_long_phrase'
  assert row['reviewed_at']<=facts['as_of'],'completion_future_review_date'
 counts=Counter(r['assessment']for r in rows);pagekeys={(r['source_id'],p)for r in rows for p in r['image_viewed_pdf_pages_1_based']}
 summary={'schema_version':'1.0','dataset_version':facts['dataset_version'],'reviewed_records':len(rows),'source_versions':len({r['source_id']for r in rows}),'image_viewed_source_pages':len(pagekeys),'assessment_counts':dict(counts),'original_observations_mutated':False,'assessment_automatically_replaces_original_completion_category':False,'quantities_summed_or_converted':False,'human_second_review_claimed':False,'input_sha256':{n:hashlib.sha256((root/n).read_bytes()).hexdigest()for n in ['data/completion_reviews.json','metadata/completion_review_rules.json','schema/completion_review.schema.json']}}
 lines=['# 指定完成語的原頁覆核\n',f'版本v{facts["dataset_version"]}。本表核讀{len(rows)}筆原先依上下文分類的紀錄，另存本輪完成語、父句範圍與剩餘未知。原觀測、原完成詞與原分類完整保留，沒有自動升格為分項明載完成。\n','只核列示業務子段，非全頁所有欄位、全冊、全年作業或逐件完成名冊；原件與頁圖不重發布。這是AI原頁判讀，不是人類二校或館方認證。\n','|館所／年|紀錄|本輪判讀|必要短語及適用範圍|官方定位|\n|---|---|---|---|---|']
 for r in rows:
  o=observations[r['observation_id']];s=sources[r['source_id']];url=s['official_file_url']or s['official_landing_url'];page=o['pdf_page_1_based'];phrase='「'+r['completion_phrase_raw']+'」'if r['completion_phrase_raw']else'未定位必要完成短語'
  text=(phrase+'；'+r['interpretation_note']+' '+r['remaining_uncertainty']).replace('|','／')
  lines.append('|'+o['organization_name']+'／'+str(o['data_year'])+'|['+o['observation_id']+'](../catalog/records/'+o['observation_id']+'.json)|'+LABELS[r['assessment']]+'|'+text+'|[PDF'+','.join(map(str,r['pdf_pages_1_based']))+'／印'+r['printed_page']+']('+url+'#page='+str(page)+')|')
 lines+=['\n完成語的原文短語只支持所列分項、父句或概述；不跨批次、不同對象或量詞移用。未知不等於未完成；有完成脈絡也不證明獨特物件、全年完整或跨館可比。','\nJSON、JSONL、CSV及SQLite的completion_reviews表保留原值、來源SHA與實際文字／看圖頁。原資料的completion_category保留原分類，本輪判讀須連讀本表，不把兩層混成新的完成件數。\n']
 outputs={'data/completion_reviews.json':encode(rows),'metadata/completion_review_build.json':encode(summary),'docs/COMPLETION_REVIEW.md':('\n'.join(lines)+'\n').encode()}
 return {'rows':rows,'outputs':outputs,'summary':summary}
