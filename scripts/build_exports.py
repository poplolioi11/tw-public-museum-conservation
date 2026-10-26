#!/usr/bin/env python3
"""Validate curated facts and stage deterministic, offline exports with rollback.

Only the standard library is required. No network or original PDF is read.
Use --candidate-facts for an update: invalid candidates leave the prior data intact.
"""
import argparse, csv, hashlib, io, json, os, re, sqlite3, tempfile, unicodedata
from pathlib import Path
from collections import Counter
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
if not __debug__:raise SystemExit('Validation must run with normal Python, without -O or PYTHONOPTIMIZE.')
def encode(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
def digest(x):return hashlib.sha256(x).hexdigest()
def read(p):return json.loads(p.read_text())
def flat(v):
    if isinstance(v,(dict,list)):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    if v is None:return ''
    if isinstance(v,bool):return 'true'if v else'false'
    return v
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
def validate(facts,inventory,version):
    assert facts['dataset_version']==version
    obs=facts['observations'];sources=facts['sources'];ids=[r['observation_id']for r in obs];sid=[r['source_id']for r in sources]
    assert len(ids)==len(set(ids));assert len(sid)==len(set(sid))
    for s in sources:
        h=s['original_file_sha256'];assert re.fullmatch('[a-f0-9]{64}',h)
        assert s['source_id']=='src-'+h[:16]
        assert s['original_file_bytes']>0 and s['redistributed_original']is False
        official_url(s['official_landing_url']);official_url(s['official_file_url'])
    for r in obs:
        assert r['source_id']in sid
        assert isinstance(r['data_year'],int)and 1900<=r['data_year']<=2100
        assert isinstance(r['pdf_page_1_based'],int)and r['pdf_page_1_based']>0
        assert r['metric_as_reported']
        if r['unit_as_reported']is None:assert r.get('unit_status')=='not_stated_in_source'
        assert r['default_aggregation_allowed']is False
        assert r['cross_museum_comparable']is False
        assert r['unique_object_count_verified']is False
        value=r['quantity_numeric'];raw=r['quantity_raw']
        if value is not None:assert isinstance(value,(int,float))and not isinstance(value,bool)and value>=0
        if r['numeric_origin']=='controller_derived':
            assert raw is None
            cs=r['derivation']['components'];assert {c['unit_raw']for c in cs}=={r['unit_as_reported']}
            assert sum(c['quantity_numeric']for c in cs)==value
        elif raw is not None:
            n=unicodedata.normalize('NFKC',str(raw)).replace(',','').strip()
            if n.isdecimal():assert int(n)==value
            else:assert value is None
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
    assert s['verified_original_pdf_files']==len(sources)
    assert s['observation_records']==sum(r['record_kind']=='observation'for r in obs)
    assert s['context_component_records']==sum(r['record_kind']=='context_component'for r in obs)
    assert s['derived_summary_records']==sum(r['record_kind']=='derived_summary'for r in obs)
    assert s['national_repaired_object_total']is None
    text=encode([facts,inventory]).decode()
    for pattern in [r'/Users/',r'file://',r'drive\.google\.com',r'localhost',r'127\.0\.0\.1',r'@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',r'AIza[\w-]{20,}',r'gh[pousr]_[A-Za-z0-9]{20,}']:
        assert not re.search(pattern,text),('prohibited_public_content',pattern)
    return {'fact_rows':len(obs),'source_reported_observations':s['observation_records'],'derived_summaries':s['derived_summary_records'],'context_components':s['context_component_records'],'organizations_with_facts':s['organizations_with_facts'],'original_pdf_versions':len(sources),'inventory_lookup_grid_cells_not_facts':len(keys),'inventory_status_counts':dict(Counter(r['status']for r in inv)),'unknown_values_are_not_zero':True,'source_pdf_revalidation_performed':False}
def generate(facts,inventory,version):
    tables={'observations':facts['observations'],'sources':facts['sources'],'relations':facts['relations'],'source_inventory':inventory['source_inventory_records'],'baseline_organizations':inventory['baseline_71_organizations'],'supplemental_organizations':inventory['supplemental_14_organization_candidates'],'facility_candidates':inventory['additional_13_public_facility_candidates'],'name_relations':inventory['name_relations']}
    output={'data/facts.json':encode(facts),'metadata/inventory.json':encode(inventory)}
    coverage=[]
    for organization,year in sorted({(r['organization_name'],r['data_year'])for r in facts['observations']}):
        selected=[r for r in facts['observations']if r['organization_name']==organization and r['data_year']==year]
        coverage.append({'organization_name':organization,'data_year':year,'fact_rows':len(selected),'source_ids':sorted({r['source_id']for r in selected}),'complete_annual_quantity_series_verified':False,'note':'只表示本版已有這些正文分項；不是全館全年所有作業或不重複物件的完整統計。'})
    output['metadata/read_coverage.json']=encode({'dataset_version':version,'cohorts':coverage,'note':'與凍結的426格盤點狀態不同；不回填未知數值為零。'})
    for name,rows in tables.items():
        output[f'data/{name}.jsonl']=jsonl_bytes(rows)
        output[f'data/{name}.csv']=csv_bytes(rows)
    with tempfile.TemporaryDirectory()as tmp:
        p=Path(tmp)/'data.sqlite';con=sqlite3.connect(p)
        for name,rows in tables.items():
            # Typed observations retain numeric nulls; every row also preserves canonical JSON.
            if name=='observations':
                con.execute('CREATE TABLE observations(observation_id TEXT PRIMARY KEY,organization_name TEXT,data_year INTEGER,metric_as_reported TEXT,quantity_numeric REAL,quantity_raw TEXT,unit_as_reported TEXT,numeric_origin TEXT,source_id TEXT,pdf_page_1_based INTEGER,record_json TEXT NOT NULL)')
                con.executemany('INSERT INTO observations VALUES(?,?,?,?,?,?,?,?,?,?,?)',[(r['observation_id'],r['organization_name'],r['data_year'],r['metric_as_reported'],r['quantity_numeric'],r['quantity_raw'],r['unit_as_reported'],r['numeric_origin'],r['source_id'],r['pdf_page_1_based'],json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':')))for r in rows])
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
