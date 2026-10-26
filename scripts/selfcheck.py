#!/usr/bin/env python3
"""Exercise reader equivalence and update failure preservation in a temp copy."""
import csv, hashlib, importlib.util, io, json, shutil, sqlite3, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('build_exports',ROOT/'scripts/build_exports.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
def hashes(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()for p in root.rglob('*')if p.is_file()and'__pycache__'not in p.parts}
def main():
    facts=builder.read(ROOT/'data/facts.json');inventory=builder.read(ROOT/'metadata/inventory.json');version=(ROOT/'VERSION').read_text().strip()
    checks=builder.validate(facts,inventory,version)
    rows=[json.loads(line)for line in(ROOT/'data/observations.jsonl').read_text().splitlines()]
    assert rows==facts['observations']
    schema=builder.read(ROOT/'schema/observation.schema.json')
    # Check the types/required/const/enum/minimum subset used by our schema.
    types={'string':lambda v:isinstance(v,str),'null':lambda v:v is None,'integer':lambda v:isinstance(v,int)and not isinstance(v,bool),'number':lambda v:isinstance(v,(int,float))and not isinstance(v,bool),'array':lambda v:isinstance(v,list),'object':lambda v:isinstance(v,dict)}
    for r in rows:
        assert set(schema['required'])<=r.keys()
        assert set(r)<=schema['properties'].keys()
        for k,v in r.items():
            rule=schema['properties'][k]
            if 'type'in rule:
                allowed=rule['type']if isinstance(rule['type'],list)else[rule['type']]
                assert any(types[t](v)for t in allowed),(r['observation_id'],k,'type')
            if 'const'in rule:assert v==rule['const']and type(v)is type(rule['const'])
            if 'enum'in rule:assert v in rule['enum']
            if v is not None and'minimum'in rule:assert v>=rule['minimum']
    with sqlite3.connect(ROOT/'data/museum-conservation.sqlite')as con:
        actual=[json.loads(row[0])for row in con.execute('SELECT record_json FROM observations ORDER BY rowid')]
        assert actual==rows
        assert con.execute('SELECT count(*) FROM source_inventory').fetchone()[0]==426
        assert con.execute('SELECT count(*) FROM observations WHERE quantity_numeric IS NULL').fetchone()[0]==sum(r['quantity_numeric']is None for r in rows)
        assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    with(ROOT/'data/observations.csv').open(encoding='utf-8-sig',newline='')as f: csvrows=list(csv.DictReader(f))
    for expected,actual in zip(rows,csvrows):
        for k in builder.columns(rows):assert str(builder.flat(expected.get(k)))==actual[k],(expected['observation_id'],k)
    assert len(rows)==len(csvrows)
    reviews=facts.get('body_reviews',[])
    review_lines=[json.loads(line)for line in(ROOT/'data/body_reviews.jsonl').read_text().splitlines()]
    assert reviews==review_lines
    with sqlite3.connect(ROOT/'data/museum-conservation.sqlite')as con:
        assert [json.loads(r[0])for r in con.execute('SELECT record_json FROM body_reviews ORDER BY row_number')]==reviews
    # Multi-year values are stored once with a period, never assigned to a single year.
    multi=json.loads(json.dumps(facts));mr=multi['observations'][0]
    mr.update(data_year=None,reporting_period_raw='2020–2022',data_year_start=2020,data_year_end=2022,year_assignment_status='multi_year_not_allocated')
    builder.validate(multi,inventory,version)
    mr['data_year']=2021
    try:builder.validate(multi,inventory,version)
    except AssertionError:pass
    else:raise AssertionError('multi-year figure silently became a single-year value')
    with tempfile.TemporaryDirectory()as tmp:
        root=Path(tmp)/'pilot';root.mkdir()
        for folder in ['data','metadata','scripts','catalog','schema']:shutil.copytree(ROOT/folder,root/folder,ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copy(ROOT/'VERSION',root/'VERSION')
        cmd=[sys.executable,str(root/'scripts/build_exports.py')]
        before=hashes(root)
        same=subprocess.run(cmd,capture_output=True,text=True);assert same.returncode==0,same.stderr
        assert json.loads(same.stdout)['status']=='unchanged';assert hashes(root)==before
        # Wrong number: reject before replacing any release data.
        bad=json.loads(json.dumps(facts));r=next(r for r in bad['observations']if r['quantity_numeric']is not None and r['numeric_origin']=='source_reported');r['quantity_numeric']+=1
        candidate=Path(tmp)/'invalid.json';candidate.write_bytes(builder.encode(bad))
        result=subprocess.run(cmd+['--candidate-facts',str(candidate)],capture_output=True,text=True)
        assert result.returncode!=0 and hashes(root)==before
        # An absent source string cannot turn into an invented numeric zero.
        bad=json.loads(json.dumps(facts));r=next(r for r in bad['observations']if r['numeric_origin']=='source_reported');r['quantity_raw']=None;r['quantity_numeric']=0
        candidate.write_bytes(builder.encode(bad));result=subprocess.run(cmd+['--candidate-facts',str(candidate)],capture_output=True,text=True)
        assert result.returncode!=0 and hashes(root)==before
        optimized=subprocess.run([sys.executable,'-O',str(root/'scripts/build_exports.py'),'--check'],capture_output=True,text=True)
        assert optimized.returncode!=0 and hashes(root)==before
        # Same official source URL, changed bytes: requires a deliberate reviewed change.
        bad=json.loads(json.dumps(facts));s=next(s for s in bad['sources']if s['official_file_url']);old=s['source_id'];s['original_file_sha256']='a'*64;s['source_id']='src-'+'a'*16
        for r in bad['observations']:
            if r['source_id']==old:r['source_id']=s['source_id']
        for review in bad.get('body_reviews',[]):
            review['source_ids']=[s['source_id']if v==old else v for v in review['source_ids']]
            for detail in review.get('source_page_reviews',[])+review.get('source_locators',[]):
                if detail['source_id']==old:detail['source_id']=s['source_id']
        candidate.write_bytes(builder.encode(bad));result=subprocess.run(cmd+['--candidate-facts',str(candidate)],capture_output=True,text=True)
        assert result.returncode!=0 and'Source bytes changed'in result.stderr and hashes(root)==before
        # A broken export is detected by check, not silently repaired during check.
        target=root/'data/observations.csv';target.write_bytes(target.read_bytes()+b'broken\n');broken=hashes(root)
        result=subprocess.run(cmd+['--check'],capture_output=True,text=True)
        assert result.returncode!=0 and hashes(root)==broken
    print(json.dumps({'status':'pass','checks':checks,'csv_jsonl_sqlite_equal':True,'invalid_candidate_preserves_previous':True,'changed_source_requires_review':True,'unchanged_writes_zero_files':True,'check_detects_export_corruption_without_writing':True},ensure_ascii=False))
if __name__=='__main__':main()
