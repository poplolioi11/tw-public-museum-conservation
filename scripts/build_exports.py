#!/usr/bin/env python3
"""Validate curated facts and stage deterministic, offline exports with rollback.

Only the standard library is required. No network or original PDF is read.
Use --candidate-facts for an update: invalid candidates leave the prior data intact.
"""
import argparse, csv, hashlib, io, json, os, re, sqlite3, tempfile, unicodedata
from pathlib import Path
from collections import Counter
from urllib.parse import urlparse
from classify_facets import facets,vocabulary

ROOT=Path(__file__).resolve().parents[1]
if not __debug__:raise SystemExit('Validation must run with normal Python, without -O or PYTHONOPTIMIZE.')
def encode(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
def digest(x):return hashlib.sha256(x).hexdigest()
def read(p):return json.loads(p.read_text())
def validate_review_shape(value,rule,path='$'):
    """Enforce the documented schema subset, recursively; no full JSON Schema claim."""
    supported={'$schema','$id','title','description','type','properties','required','additionalProperties','items','minimum','enum','const'}
    assert not set(rule)-supported,('unsupported_review_schema_keyword',path,set(rule)-supported)
    types={'string':lambda v:isinstance(v,str),'null':lambda v:v is None,
           'integer':lambda v:isinstance(v,int)and not isinstance(v,bool),
           'number':lambda v:isinstance(v,(int,float))and not isinstance(v,bool),
           'array':lambda v:isinstance(v,list),'object':lambda v:isinstance(v,dict),
           'boolean':lambda v:isinstance(v,bool)}
    if 'type'in rule:
        allowed=rule['type']if isinstance(rule['type'],list)else[rule['type']]
        assert all(t in types for t in allowed),('unsupported_review_schema_type',path)
        assert any(types[t](value)for t in allowed),('review_schema_type',path)
    if 'const'in rule:assert value==rule['const']and type(value)is type(rule['const']),('review_schema_const',path)
    if 'enum'in rule:assert value in rule['enum'],('review_schema_enum',path)
    if value is not None and'minimum'in rule:assert value>=rule['minimum'],('review_schema_minimum',path)
    if isinstance(value,dict):
        props=rule.get('properties',{})
        assert set(rule.get('required',[]))<=value.keys(),('review_schema_required',path)
        if rule.get('additionalProperties')is False:assert set(value)<=props.keys(),('review_schema_additional_property',path)
        for k,v in value.items():
            if k in props:validate_review_shape(v,props[k],path+'/'+k)
    if isinstance(value,list)and'items'in rule:
        for i,v in enumerate(value):validate_review_shape(v,rule['items'],path+'/'+str(i))
def sqlite_logically_equal(left,right):
    """SQLite versions can change page layouts; compare schema and every table cell.

    The selected artifact's exact bytes remain bound by metadata/build.json.
    Both connections are read-only temporary copies, never the published files.
    """
    try:
        with tempfile.TemporaryDirectory()as tmp:
            paths=[Path(tmp)/name for name in ['left.sqlite','right.sqlite']]
            for path,body in zip(paths,[left,right]):path.write_bytes(body)
            connections=[sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)for path in paths]
            try:
                if any(c.execute('PRAGMA integrity_check').fetchone()!=('ok',)for c in connections):return False
                schema=[c.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name').fetchall()for c in connections]
                if schema[0]!=schema[1]:return False
                for kind,name,_,_ in schema[0]:
                    if kind!='table':continue
                    if not re.fullmatch('[A-Za-z_][A-Za-z0-9_]*',name):return False
                    if connections[0].execute('SELECT * FROM "'+name+'" ORDER BY rowid').fetchall()!=connections[1].execute('SELECT * FROM "'+name+'" ORDER BY rowid').fetchall():return False
                return True
            finally:
                for c in connections:c.close()
    except sqlite3.DatabaseError:return False
def source_number(raw):
    if raw is None:return None
    text=unicodedata.normalize('NFKC',str(raw)).replace(',','').strip()
    if text.isdecimal():return int(text)
    # Exact single Chinese numerals only; qualifiers and composite units remain null.
    return {'零':0,'〇':0,'一':1,'二':2,'兩':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10}.get(text)
def flat(v):
    if isinstance(v,(dict,list)):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    if v is None:return ''
    if isinstance(v,bool):return 'true'if v else'false'
    return v
def quantity_display(record):
    raw=record['quantity_raw']if record['quantity_raw']is not None else'程式推算 '+str(record['quantity_numeric'])
    unit=record['unit_as_reported']
    parts=re.findall(r'[\u4e00-\u9fff]+',unit or'')
    if parts and all(p in str(raw)for p in parts):return str(raw)
    return str(raw)+' '+str(unit or'量詞未明')
def columns(rows):return sorted({k for r in rows for k in r})
def csv_bytes(rows):
    f=io.StringIO(newline='');w=csv.DictWriter(f,fieldnames=columns(rows),lineterminator='\n');w.writeheader()
    w.writerows({k:flat(v)for k,v in r.items()}for r in rows)
    return f.getvalue().encode('utf-8-sig')
def jsonl_bytes(rows):return ''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n'for r in rows).encode()
def official_url(u):
    if u is None:return
    p=urlparse(u);assert p.scheme=='https'and p.hostname,('bad_url',u)
    assert not p.username and not p.password
    assert p.hostname not in ['localhost','127.0.0.1']
    assert not p.hostname.endswith('google.com')and p.hostname!='drive.google.com',('private_or_non_source_url',u)
def current_reviews(reviews):
    """Keep every unextended record; an organization-year may have several leaves."""
    by_id={r['review_id']:r for r in reviews}
    assert len(by_id)==len(reviews), 'duplicate_review_id'
    parents=set()
    for row in reviews:
        seen={row['review_id']};parent_id=row.get('extends_review_id')
        while parent_id:
            assert parent_id in by_id,('review_parent_missing',row['review_id'])
            assert parent_id not in seen,('review_extension_cycle',row['review_id'])
            seen.add(parent_id);parent=by_id[parent_id]
            assert (parent['organization_id'],parent['target_data_year'])==(row['organization_id'],row['target_data_year']),('review_parent_scope_mismatch',row['review_id'])
            parents.add(parent_id);parent_id=parent.get('extends_review_id')
    return [r for r in reviews if r['review_id']not in parents]
def validate(facts,inventory,version):
    assert facts['dataset_version']==version
    obs=facts['observations'];sources=facts['sources'];ids=[r['observation_id']for r in obs];sid=[r['source_id']for r in sources]
    assert len(ids)==len(set(ids));assert len(sid)==len(set(sid))
    for s in sources:
        h=s['original_file_sha256'];assert re.fullmatch('[a-f0-9]{64}',h)
        assert s['source_id']=='src-'+h[:16]
        assert s['original_file_bytes']>0 and s['redistributed_original']is False
        assert s['original_file_type']in ['PDF','HTML']
        official_url(s['official_landing_url']);official_url(s['official_file_url'])
    source_by_id={s['source_id']:s for s in sources}
    for r in obs:
        assert r['source_id']in sid
        if r['data_year']is None:
            assert r.get('year_assignment_status')=='multi_year_not_allocated'
            assert r.get('reporting_period_raw')
            start,end=r.get('data_year_start'),r.get('data_year_end')
            assert isinstance(start,int)and isinstance(end,int)and 1900<=start<end<=2100
        else:
            assert isinstance(r['data_year'],int)and 1900<=r['data_year']<=2100
            assert r.get('year_assignment_status')!='multi_year_not_allocated','A multi-year figure must not be assigned to one year.'
        if source_by_id[r['source_id']]['original_file_type']=='PDF':
            assert isinstance(r['pdf_page_1_based'],int)and r['pdf_page_1_based']>0
        else:
            assert r['pdf_page_1_based']is None,'HTML observations must not invent a PDF page.'
            assert r['printed_page']is None,'HTML observations must not borrow a printed PDF page.'
            assert isinstance(r.get('source_locator'),str)and r['source_locator'].strip(),'HTML observations need a body locator.'
        assert r['metric_as_reported']
        if r['unit_as_reported']is None:assert r.get('unit_status')=='not_stated_in_source'
        assert r['default_aggregation_allowed']is False
        assert r['cross_museum_comparable']is False
        assert r['unique_object_count_verified']is False
        for key,value in facets(r).items():assert r[key]==value,('query_facet_mismatch',r['observation_id'],key)
        value=r['quantity_numeric'];raw=r['quantity_raw']
        if value is not None:assert isinstance(value,(int,float))and not isinstance(value,bool)and value>=0
        if r['numeric_origin']=='controller_derived':
            assert raw is None
            cs=r['derivation']['components'];assert {c['unit_raw']for c in cs}=={r['unit_as_reported']}
            assert sum(c['quantity_numeric']for c in cs)==value
        elif raw is not None:
            assert source_number(raw)==value,('quantity_conversion',r['observation_id'],raw,value)
        else:assert value is None,'Missing source number must not acquire an imputed numeric value.'
    for r in facts['relations']:
        for k in ['parent','parent_observation_id','observation_id','from_observation_id','to_existing_observation_id','larger_scope','completion_subset','treatment_record','completed_record']:
            if r.get(k):assert r[k]in ids,(k,r[k])
        for k in ['children','candidate_child_ids','observation_ids']:
            for v in r.get(k,[]):assert v in ids,(k,v)
    inv=inventory['source_inventory_records'];keys=[(r['source_inventory_id'],r['target_data_year'])for r in inv]
    assert len(keys)==len(set(keys))==426
    assert len(inventory['baseline_71_organizations'])==71
    assert {k[1]for k in keys}==set(range(2020,2026))
    baseline_ids={r['source_inventory_id']for r in inventory['baseline_71_organizations']}
    assert len(baseline_ids)==71 and {k[0]for k in keys}==baseline_ids
    assert all({y for ident,y in keys if ident==i}==set(range(2020,2026))for i in baseline_ids)
    s=facts['summary'];assert s['total_fact_rows']==len(obs)
    assert s['organizations_with_facts']==len({r['organization_name']for r in obs})
    assert s['verified_original_source_files']==len(sources)
    assert s['verified_original_pdf_files']==sum(r['original_file_type']=='PDF'for r in sources)
    assert s['verified_original_html_files']==sum(r['original_file_type']=='HTML'for r in sources)
    assert s['observation_records']==sum(r['record_kind']=='observation'for r in obs)
    assert s['context_component_records']==sum(r['record_kind']=='context_component'for r in obs)
    assert s['derived_summary_records']==sum(r['record_kind']=='derived_summary'for r in obs)
    assert s['national_repaired_object_total']is None
    text=encode([facts,inventory]).decode()
    for pattern in [r'/Users/',r'file://',r'drive\.google\.com',r'localhost',r'127\.0\.0\.1',r'@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',r'AIza[\w-]{20,}',r'gh[pousr]_[A-Za-z0-9]{20,}']:
        assert not re.search(pattern,text),('prohibited_public_content',pattern)
    reviews=facts.get('body_reviews',[])
    rid=[r['review_id']for r in reviews];assert len(rid)==len(set(rid))
    source_map={s['source_id']:s for s in sources}
    review_schema=read(ROOT/'schema/body_review.schema.json')
    for r in reviews:
        validate_review_shape(r,review_schema,r['review_id'])
        assert isinstance(r['target_data_year'],int)
        assert r['review_status']in ['numeric_observations_verified','body_read_no_eligible_quantity_located','source_found_body_not_reviewed','source_not_located_in_this_search','annual_scope_not_separable','outside_selected_scope']
        for v in r['source_ids']:assert v in sid,('review_source_missing',v)
        for v in r['observation_ids']:assert v in ids,('review_observation_missing',v)
        if r['review_status']in ['numeric_observations_verified','body_read_no_eligible_quantity_located','annual_scope_not_separable','outside_selected_scope']:assert r['source_ids']
        assert r['missing_quantity_is_zero']is False
        if r.get('extends_review_id'):assert r['extends_review_id']in rid
        for locator in r.get('source_locators',[]):assert locator['source_id']in r['source_ids']and locator['locator']
        for detail in r['source_page_reviews']:
            assert detail['source_id']in r['source_ids']
            assert all(isinstance(p,int)and p>0 for p in detail['pdf_pages_1_based'])
            for page_kind in ['text_read_pdf_pages_1_based','image_viewed_pdf_pages_1_based']:
                assert set(detail.get(page_kind,[]))<=set(detail['pdf_pages_1_based']),('review_evidence_outside_reviewed_pages',r['review_id'],page_kind)
            maximum=source_map[detail['source_id']].get('original_file_pdf_pages')
            if maximum:assert all(p<=maximum for p in detail['pdf_pages_1_based'])
        assert r['reviewed_pdf_pages_1_based']==sorted({p for detail in r['source_page_reviews']for p in detail['pdf_pages_1_based']})
    assert s['body_review_records']==len(reviews)
    current_reviews(reviews)
    distinct_reviews={(r['organization_name'],r['target_data_year'])for r in reviews}
    assert s['body_review_target_year_cells']==len(distinct_reviews)
    return {'fact_rows':len(obs),'source_reported_observations':s['observation_records'],'derived_summaries':s['derived_summary_records'],'context_components':s['context_component_records'],'organizations_with_facts':s['organizations_with_facts'],'original_source_versions':len(sources),'original_pdf_versions':s['verified_original_pdf_files'],'original_html_versions':s['verified_original_html_files'],'multi_year_records_not_allocated_to_years':sum(r['data_year']is None for r in obs),'body_review_records':len(reviews),'distinct_source_year_review_cells':len(distinct_reviews),'inventory_lookup_grid_cells_not_facts':len(keys),'unknown_values_are_not_zero':True,'query_facets_reproduced':True,'source_pdf_revalidation_performed':False}
def generate(facts,inventory,version):
    tables={'observations':facts['observations'],'sources':facts['sources'],'relations':facts['relations'],'body_reviews':facts.get('body_reviews',[]),'source_inventory':inventory['source_inventory_records'],'baseline_organizations':inventory['baseline_71_organizations'],'supplemental_organizations':inventory['supplemental_14_organization_candidates'],'facility_candidates':inventory['additional_13_public_facility_candidates'],'name_relations':inventory['name_relations']}
    output={'data/facts.json':encode(facts),'metadata/inventory.json':encode(inventory)}
    output['schema/vocabulary.json']=encode(vocabulary())
    source_map={s['source_id']:s for s in facts['sources']}
    for r in facts['observations']:
        ident=r['observation_id'];assert re.fullmatch('[A-Za-z0-9_-]+',ident)
        output[f'catalog/records/{ident}.json']=encode({'dataset_version':version,'record':r,'source':source_map[r['source_id']],'versioned_record_url':f'https://raw.githubusercontent.com/poplolioi11/tw-public-museum-conservation/v{version}/catalog/records/{ident}.json'})
    catalog=['# 館所索引',f'\n版本：{version}。可先看[資料樣貌](SAMPLE.md)，再依館所查找各筆原詞、原數字與官方來源。\n',
      '每筆數值均附核讀來源。下列「補充正文查核」另計年度來源查找紀錄；0則表示未另建這類紀錄，不表示數值未核來源。列數也不是文物件數或修復合計。\n']
    review_labels={'numeric_observations_verified':'已核原報數值','body_read_no_eligible_quantity_located':'指定正文未定位合格數量',
      'source_found_body_not_reviewed':'找到來源，正文待讀','source_not_located_in_this_search':'本輪未定位指定來源',
      'annual_scope_not_separable':'年度範圍無法拆分','outside_selected_scope':'不在本次採用範圍'}
    current=current_reviews(facts.get('body_reviews',[]));current_ids={r['review_id']for r in current}
    names=sorted({r['organization_name']for r in facts['observations']+facts.get('body_reviews',[])})
    for name in names:
        rows=[r for r in facts['observations']if r['organization_name']==name];reviews=[r for r in facts.get('body_reviews',[])if r['organization_name']==name]
        orgid=next((r['organization_id']for r in rows+reviews if r.get('organization_id')),None);assert orgid
        catalog.append(f'- [{name}](museums/{orgid}.md)：{len(rows)}列數值／推算／脈絡紀錄；{len(reviews)}則補充正文查核。')
        lines=['# '+name,f'\n版本：{version}。以下為本版已核子集；列數不代表不重複文物或修復量。\n','|資料年／期間|原報作業|原數字與量詞|逐筆來源|','|---|---|---|---|']
        for r in rows:
            period=str(r['data_year'])if r['data_year']is not None else r['reporting_period_raw'];raw=r['quantity_raw']if r['quantity_raw']is not None else'程式推算 '+str(r['quantity_numeric'])
            lines.append('|'+period+'|'+r['metric_as_reported'].replace('|','／')+'|'+quantity_display(r)+'|['+r['observation_id']+'](../records/'+r['observation_id']+'.json)|')
        lines+=['\n## 目前補充查核\n','依明確延伸關係保留所有尚未被延伸的紀錄；同館同年可能有多則。所列頁段不代表全年所有來源已讀，未定位數量不代表零。\n']
        for r in reviews:
            if r['review_id']in current_ids:lines.append(f"- {r['target_data_year']}｜{review_labels[r['review_status']]}：{r['review_scope']} {r['interpretation_note']}（{r['review_id']}）")
        history=[r for r in reviews if r['review_id']not in current_ids]
        if history:
            lines+=['\n## 已有後續覆讀的歷史查核\n','原紀錄保留；目前結論請沿extends_review_id讀取後續紀錄，不以狀態好壞或日期挑選。\n']
            for r in history:lines.append(f"- {r['target_data_year']}｜{review_labels[r['review_status']]}：{r['review_scope']} {r['interpretation_note']}（{r['review_id']}）")
        output[f'catalog/museums/{orgid}.md']=('\n'.join(lines)+'\n').encode()
    output['catalog/README.md']=('\n'.join(catalog)+'\n').encode()
    examples=[]
    def example(label,predicate,note):
        row=next((r for r in facts['observations']if predicate(r)),None)
        if row:examples.append((label,row,note))
    example('原報精確數字',lambda r:r['observation_id']=='NMTH-2020-full-treatment','「完整修護」是作業分類，不能只憑名稱認定已完成。')
    example('來源明列零',lambda r:r['quantity_raw']=='0'and r['numeric_origin']=='source_reported','只有來源明列且確認語義的零才記0；未查到的數字保留未知。')
    example('原報近似量',lambda r:r['observation_id']=='thcdc-2024-arrangement-registration','保留「餘」等原字串，精確數值欄留空，不改成整數300。')
    example('原報雙單位',lambda r:r['observation_id']=='daxi-2025-combined-project','同一原句的兩種單位一起保留，不拆配成兩筆獨立工作量。')
    for suffix,label in [('treatment-project-cases','案數'),('treatment-objects-as-reported','文物件數'),('conservation-work-items','工作項數')]:
        example(label,lambda r,s=suffix:r['observation_id']=='KHM-2024-'+s,'同年件、案、項各有原報範圍，不互換、不相加。')
    example('跨年期間',lambda r:r['data_year']is None,'保留原報期間，不平均分配到各年度。')
    example('程式推算',lambda r:r['numeric_origin']=='controller_derived','另標計算依據，不能當作原報總數。')
    example('官方網頁',lambda r:source_map[r['source_id']]['original_file_type']=='HTML','依網頁的年度段落定位，不借用其他PDF的頁碼。')
    sample=['# 資料樣貌',f'\n版本：{version}。以下挑選不同資料型態，示範如何閱讀；不是隨機抽樣或可相加的統計表。\n',
      '|型態|館所｜資料年／期間|原報作業|原數字與量詞|如何閱讀|回查來源|','|---|---|---|---|---|---|']
    for label,row,note in examples:
        period=str(row['data_year'])if row['data_year']is not None else row['reporting_period_raw']
        raw=str(row['quantity_raw'])if row['quantity_raw']is not None else'程式推算 '+str(row['quantity_numeric'])
        source=source_map[row['source_id']]
        original=('[官方PDF第'+str(row['pdf_page_1_based'])+'頁]('+source['official_file_url']+'#page='+str(row['pdf_page_1_based'])+')')if source['original_file_type']=='PDF'else('[官方網頁]('+source['official_file_url']+')')
        values=[label,row['organization_name']+'｜'+period,row['metric_as_reported'],quantity_display(row),note,
          '[逐筆資料](records/'+row['observation_id']+'.json)／'+original]
        sample.append('|'.join(['']+[v.replace('|','／').replace('\n',' ')for v in values]+['']))
    sample+=['\n每筆完整資料還保留完成狀態、對象範圍、來源版次與雜湊。近似量或雙單位的精確數值欄留空，是保留不確定性。\n',
      '[依館所查找](README.md)｜[全部CSV資料](../data/observations.csv)｜[欄位說明](../docs/DATA_DICTIONARY.md)\n']
    output['catalog/SAMPLE.md']=('\n'.join(sample)+'\n').encode()
    coverage=[]
    for organization,year in sorted({(r['organization_name'],r['data_year'])for r in facts['observations']},key=lambda v:(v[0],v[1]if v[1]is not None else -1)):
        selected=[r for r in facts['observations']if r['organization_name']==organization and r['data_year']==year]
        coverage.append({'organization_name':organization,'data_year':year,'fact_rows':len(selected),'source_ids':sorted({r['source_id']for r in selected}),'reported_periods':sorted({r['reporting_period_raw']for r in selected if r.get('reporting_period_raw')}),'complete_annual_quantity_series_verified':False,'note':'只表示本版已有這些正文分項；data_year=null為未拆到單年的跨年期間；不是全館全年所有作業或不重複物件的完整統計。'})
    output['metadata/read_coverage.json']=encode({'dataset_version':version,'cohorts':coverage,'body_reviews':{'historical_record_count':len(facts.get('body_reviews',[])),'current_record_count':len(current),'current_organization_year_cells':len({(r['organization_id'],r['target_data_year'])for r in current}),'current_status_counts':dict(Counter(r['review_status']for r in current)),'current_review_ids':[r['review_id']for r in current],'selection_rule':'all leaves of explicit extends_review_id links; do not collapse organization-year, choose latest date or prefer a status','full_year_all_sources_reviewed':False},'note':'與凍結的426格盤點狀態不同；紀錄數不等於館年格數，同格多則全部保留；不回填未知數值為零。'})
    for name,rows in tables.items():
        output[f'data/{name}.jsonl']=jsonl_bytes(rows)
        output[f'data/{name}.csv']=csv_bytes(rows)
    with tempfile.TemporaryDirectory()as tmp:
        p=Path(tmp)/'data.sqlite';con=sqlite3.connect(p)
        for name,rows in tables.items():
            # Typed observations retain numeric nulls; every row also preserves canonical JSON.
            if name=='observations':
                con.execute('CREATE TABLE observations(observation_id TEXT PRIMARY KEY,organization_name TEXT,data_year INTEGER,metric_as_reported TEXT,quantity_numeric REAL,quantity_raw TEXT,unit_as_reported TEXT,numeric_origin TEXT,source_id TEXT,pdf_page_1_based INTEGER,action_categories_json TEXT,completion_category TEXT,subject_scope_category TEXT,record_json TEXT NOT NULL)')
                con.executemany('INSERT INTO observations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',[(r['observation_id'],r['organization_name'],r['data_year'],r['metric_as_reported'],r['quantity_numeric'],r['quantity_raw'],r['unit_as_reported'],r['numeric_origin'],r['source_id'],r['pdf_page_1_based'],json.dumps(r['action_categories'],ensure_ascii=False),r['completion_category'],r['subject_scope_category'],json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':')))for r in rows])
            else:
                con.execute(f'CREATE TABLE {name}(row_number INTEGER PRIMARY KEY,record_json TEXT NOT NULL)')
                con.executemany(f'INSERT INTO {name} VALUES(?,?)',[(i+1,json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':')))for i,r in enumerate(rows)])
        con.execute('CREATE TABLE dataset_metadata(version TEXT,as_of TEXT,warning TEXT)')
        con.execute('INSERT INTO dataset_metadata VALUES(?,?,?)',(version,facts['as_of'],'No national repaired-object total; heterogeneous metrics are non-additive.'))
        con.commit();assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok';con.close()
        output['data/museum-conservation.sqlite']=p.read_bytes()
    return output
def main():
    a=argparse.ArgumentParser();a.add_argument('--root',type=Path,default=ROOT);a.add_argument('--check',action='store_true');a.add_argument('--candidate-facts',type=Path);a.add_argument('--candidate-inventory',type=Path);a.add_argument('--accept-reviewed-source-change',action='store_true');args=a.parse_args()
    root=args.root;version=(root/'VERSION').read_text().strip()
    facts=read(args.candidate_facts or root/'data/facts.json');inventory=read(args.candidate_inventory or root/'metadata/inventory.json')
    checks=validate(facts,inventory,version)
    outputs=generate(facts,inventory,version)
    sqlite_path='data/museum-conservation.sqlite'
    existing=root/sqlite_path
    if existing.is_file():
        published_bytes=existing.read_bytes()
        if published_bytes!=outputs[sqlite_path]and sqlite_logically_equal(published_bytes,outputs[sqlite_path]):
            outputs[sqlite_path]=published_bytes
    previous=read(root/'metadata/build.json')if(root/'metadata/build.json').exists()else None
    versions={}
    for s in facts['sources']:
        if s['official_file_url']:versions.setdefault(s['official_file_url'],set()).add(s['original_file_sha256'])
    versions={u:sorted(hs)for u,hs in versions.items()}
    if previous and not args.accept_reviewed_source_change:
        for u,hs in versions.items():
            old=previous['original_source_versions'].get(u)
            if isinstance(old,str):old=[old]
            assert old is None or old==hs,'Source bytes changed: review before replacing an earlier version.'
    manifest={'dataset_version':version,'as_of':facts['as_of'],'checks':checks,'canonical_fact_projection_sha256':digest(encode(facts)),'inventory_projection_sha256':digest(encode(inventory)),'original_source_versions':versions,'exports':{p:{'sha256':digest(b),'bytes':len(b)}for p,b in sorted(outputs.items())}}
    outputs['metadata/build.json']=encode(manifest)
    if args.check:
        for p,b in outputs.items():assert(root/p).read_bytes()==b,('export_mismatch',p)
        print(json.dumps({'status':'pass','mode':'offline_projection_and_export_consistency','checks':checks},ensure_ascii=False));return
    changed=[p for p,b in outputs.items()if not(root/p).exists()or(root/p).read_bytes()!=b]
    if not changed:print(json.dumps({'status':'unchanged','files_written':0}));return
    # Every candidate is validated before any canonical or export path is replaced.
    with tempfile.TemporaryDirectory(dir=root)as tmp:
        for p in changed:
            target=Path(tmp)/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(outputs[p])
        backups={p:(root/p).read_bytes()if(root/p).exists()else None for p in changed}
        replaced=[]
        try:
            for p in changed:
                target=root/p;target.parent.mkdir(parents=True,exist_ok=True);os.replace(Path(tmp)/p,target);replaced.append(p)
        except OSError:
            for p in reversed(replaced):
                target=root/p
                if backups[p]is None:target.unlink(missing_ok=True)
                else:target.write_bytes(backups[p])
            raise
    print(json.dumps({'status':'updated','files_written':len(changed),'checks':checks},ensure_ascii=False))
if __name__=='__main__':main()
