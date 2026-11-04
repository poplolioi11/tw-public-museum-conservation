#!/usr/bin/env python3
"""Export separate reviewed public/private supplements without quantity totals.

Reads public inputs only. Bounded schema/pattern checks do not replace original
source review, privacy review, or human audit. Originals stay outside the repo.
"""
import csv, hashlib, io, json, re, unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

LAYERS=('public_followup','private_artist_museums','private_university_museums',
        'private_university_other_museums','art_center_scope_candidates')
SCHEMA='schema/conservation-supplement.schema.json'
DIRECTORY='data/conservation_supplement'
METADATA='metadata/conservation_supplement_build.json'
REVIEWED_HOSTS={'www.juming.org.tw','tw.limeishu.org','yangsanlang.com.tw',
    'www.yuyuyang.com.tw','www.tcam.museum','collections.culture.tw'}
# Existing Juming official annual-report links use this exact CMS file area.
REVIEWED_CMS_PREFIX='https://comet.noonspace.com/w62/ec/MsgInfo/'
PERIOD_KINDS={'dated_event','report_context_only','cumulative_as_of',
    'recurring_frequency','bounded_period','undated','announced_plan'}
if not __debug__:raise SystemExit('Normal Python validation is required.')

def encode(value):return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
def require(condition,message):
    if not condition:raise ValueError(message)
def public_text(value,where):
    if isinstance(value,dict):
        for k,v in value.items():public_text(k,where+'/key');public_text(v,where+'/'+k)
    elif isinstance(value,list):
        for i,v in enumerate(value):public_text(v,where+'/'+str(i))
    elif isinstance(value,str):
        require(not re.search(r'/Users/|file://|drive\.google\.com|localhost|127\.0\.0\.1|'
            r'AIza[0-9A-Za-z_-]{20,}|sk-[0-9A-Za-z_-]{20,}|'
            r'gh[pousr]_[A-Za-z0-9]{20,}|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',value),
            where+': private path, identifier, address or credential')
        require(not re.search(r'(?:NT\$|TWD|USD|新臺幣)\s*[\d一二三四五六七八九十百千萬億,]+|'
            r'[\d一二三四五六七八九十百千萬億,]+\s*(?:億|萬|千)?元|'
            r'(?:預算|決算|經費|金額|採購)\s*[:：]?\s*[\d一二三四五六七八九十百千萬億,]+',value,re.I),
            where+': prohibited financial amount')
        require(not re.search(r'庫位|平面圖|警衛|監視器|門禁|警報|監視死角|感測器位置',value),
            where+': prohibited security detail')
def official_url(value):
    p=urlparse(value)
    require(p.scheme=='https' and p.hostname and not p.username and not p.password,'supplement invalid source URL')
    require(p.hostname.endswith(('.gov.tw','.edu.tw')) or p.hostname in REVIEWED_HOSTS
            or value.startswith(REVIEWED_CMS_PREFIX),
            'supplement unreviewed source host: '+str(p.hostname))
    public_text(value,'URL')
def iso_date(value,where):
    if value is not None:
        require(re.fullmatch(r'\d{4}-\d{2}-\d{2}',value)is not None,where+': expected ISO date')
        date.fromisoformat(value)

def validate(root,version):
    from preservation_texts import _shape
    from build_exports import source_number
    root=Path(root);schema=json.loads((root/SCHEMA).read_text());loaded={};ids=set()
    for layer in LAYERS:
        data=json.loads((root/DIRECTORY/(layer+'.json')).read_text());_shape(data,schema,layer)
        require(data['dataset_version']==version,'supplement version mismatch')
        require(data['layer']==layer,'supplement layer/path mismatch');public_text(data,layer)
        institutions={r['organization_id']:r for r in data['institutions']}
        require(len(institutions)==len(data['institutions']),'duplicate supplement organization')
        sources={r['source_id']:r for r in data['sources']}
        require(len(sources)==len(data['sources']),'duplicate supplement source')
        for institution in institutions.values():
            if institution['official_url']is not None:official_url(institution['official_url'])
            ident=institution['identity_source_id']
            if ident is not None:
                require(ident in sources and institution['identity_source_url']==sources[ident]['url'],
                        'supplement identity source reference missing')
                require(bool(institution['identity_locator']),'supplement identity locator missing')
        for s in sources.values():
            official_url(s['url']);h=s['sha256']
            if h is not None:
                require(re.fullmatch(r'[0-9a-f]{64}',h)is not None and s['source_id']=='src-'+h[:16],'source/hash mismatch')
                require(type(s['bytes'])is int and s['bytes']>0,'verified supplement original requires bytes')
                require(s['verification_level']=='original_bytes_verified','supplement source verification mismatch')
            else:
                require(s['bytes']is None and s['pdf_pages']is None and s['verification_level']=='official_web_body_only',
                        'unavailable original must not acquire bytes/pages')
            if s['format']=='PDF' and h is not None:
                require(type(s['pdf_pages'])is int and s['pdf_pages']>0,'PDF page count missing')
            elif s['format']=='HTML':require(s['pdf_pages']is None,'HTML must not acquire PDF page count')
        def locator(row,primary=False):
            s=sources.get(row['source_id']);require(s is not None,'supplement source reference missing')
            require(row['source_url']==s['url'],'supplement source URL mismatch');page=row['pdf_page_1_based']
            if s['format']=='PDF':
                require(type(page)is int and type(s['pdf_pages'])is int and 1<=page<=s['pdf_pages'],
                        'supplement PDF locator out of bounds')
            else:require(page is None and row['printed_page']is None,'HTML cannot acquire PDF or printed page')
            require(bool(row['source_locator'].strip()),'supplement blank source locator')
            if primary:require(s['sha256']is not None,'adopted supplement record requires saved official original')
        for row in data['records']:
            validate_record(row,ids,institutions,locator,source_number)
        loaded[layer]=data
    return loaded

def validate_record(row,ids,institutions,locator,source_number):
    ident=row['record_id'];require(ident not in ids,'duplicate supplement record');ids.add(ident)
    organization=institutions.get(row['organization_id'])
    require(organization is not None and row['organization_name']==organization['organization_name'],
            'supplement organization mismatch')
    locator(row,True)
    for evidence in row['period_evidence']:locator(evidence)
    for key in ['period_start','period_end','as_of_date','report_date','publication_date']:iso_date(row[key],ident+'/'+key)
    require(row['period_kind']in PERIOD_KINDS,'supplement period kind')
    require(bool(row['period_label'].strip()) and bool(row['period_basis'].strip()),'supplement missing period explanation')
    if row['period_start']is not None and row['period_end']is not None:
        require(row['period_start']<=row['period_end'],'reversed supplement period')
    if row['data_year']is not None:
        require(row['period_kind']in {'dated_event','bounded_period','announced_plan'},
                'undated, recurring or cumulative evidence cannot acquire an activity year')
        for field in ['period_start','period_end']:
            if row[field]is not None:
                require(date.fromisoformat(row[field]).year==row['data_year'],
                        'activity year differs from explicit activity period')
    if row['data_year']is None:
        require(bool(re.search(r'未知|未明|未確定|不明|無法|未限定|未獨立|未載|未界定',
            row['period_label']+row['period_basis']+row['reporting_period_raw'])),
            'unknown supplement year must be visible')
    if row['record_kind']=='quantity_record':
        require(bool(row['quantity_raw']) and bool(row['unit_as_reported']),'supplement quantity requires raw value and unit')
        require(row['quantity_numeric']==source_number(row['quantity_raw']),'supplement numeric/raw mismatch')
        if row['dual_unit_quantities']:
            require(row['quantity_numeric']is None and len(row['dual_unit_quantities'])>=2,
                    'compound units cannot acquire scalar or total')
            for c in row['dual_unit_quantities']:
                require(c['quantity_numeric']==source_number(c['quantity_raw']),'compound component numeric/raw mismatch')
            def compound_text(s):
                return re.sub(r'[\s,，、；;/（）()]','',unicodedata.normalize('NFKC',s))
            components=''.join(c['quantity_raw']+c['unit_as_reported']for c in row['dual_unit_quantities'])
            require(compound_text(components)==compound_text(row['quantity_raw']),
                    'compound components differ from the original quantity string')
    else:
        require(row['quantity_raw']is row['quantity_numeric']is row['unit_as_reported']is None
                and not row['dual_unit_quantities'] and bool(row['text_summary']),'text supplement must not acquire quantity')
    # Contextual exclusion notes may remain; amounts/vendors/security details may not.
    text=' '.join(str(row.get(k)or'')for k in ['metric_label','subject_scope','text_summary'])
    require(not re.search(r'NT\$|TWD|USD|新臺幣|萬元|億元|廠商|採購|得標|委外公司',text,re.I),
            'supplement prohibited finance/vendor content')
    require(not re.search(r'庫位|平面圖|警衛|監視器|門禁|警報|監視死角|感測器位置',text),
            'supplement prohibited security detail')

def build(root,facts):
    root=Path(root);data=validate(root,facts['dataset_version'])
    props=json.loads((root/SCHEMA).read_text())['properties']['records']['items']['properties'];columns=sorted(props)
    outputs={};summaries={}
    for layer,value in data.items():
        prefix=DIRECTORY+'/'+layer;body=(root/(prefix+'.json')).read_bytes();outputs[prefix+'.json']=body
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=columns,lineterminator='\n');writer.writeheader()
        for row in value['records']:
            cells={}
            for k in columns:
                v=row[k];cells[k]=(''if v is None else str(v).lower()if isinstance(v,bool)else
                    json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))if isinstance(v,(dict,list))else v)
            writer.writerow(cells)
        outputs[prefix+'.csv']=stream.getvalue().encode('utf-8-sig')
        outputs[prefix+'.jsonl']=''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n'for r in value['records']).encode()
        summaries[layer]=dict(input_file=prefix+'.json',input_sha256=hashlib.sha256(body).hexdigest(),
            institution_count=len(value['institutions']),source_versions=len(value['sources']),record_count=len(value['records']),
            quantity_record_count=sum(r['record_kind']=='quantity_record'for r in value['records']),
            text_record_count=sum(r['record_kind']=='text_record'for r in value['records']),
            unknown_activity_year_count=sum(r['record_kind']=='quantity_record'and r['data_year']is None for r in value['records']))
    outputs[METADATA]=encode(dict(schema_version='1.0',dataset_version=facts['dataset_version'],layers=summaries,
        public_baseline_eligible=False,default_aggregation_allowed=False,main_observation_count_unchanged=True,
        frozen_coverage_denominators_unchanged=True,human_verified=False,
        scope_note='分層補充紀錄；報告年不代替作業年，列數不是年度全量或全國統計。',
        validation_limits='結構與明顯模式檢查不代替原件、語義、隱私或人工核讀。'))
    return outputs
