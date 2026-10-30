#!/usr/bin/env python3
"""Exercise reader equivalence and update failure preservation in a temp copy."""
import csv, hashlib, importlib.util, io, json, shutil, sqlite3, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('build_exports',ROOT/'scripts/build_exports.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
def hashes(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()for p in root.rglob('*')if p.is_file()and'__pycache__'not in p.parts}

def assert_typed_equal(actual,expected,label):
    """Do not let Python's True == 1 hide a lossy export roundtrip."""
    assert type(actual)is type(expected),(label,'type',type(actual).__name__,type(expected).__name__)
    if isinstance(expected,dict):
        assert actual.keys()==expected.keys(),(label,'keys')
        for key in expected:assert_typed_equal(actual[key],expected[key],label+'/'+key)
    elif isinstance(expected,list):
        assert len(actual)==len(expected),(label,'length')
        for index,(left,right)in enumerate(zip(actual,expected)):assert_typed_equal(left,right,label+'/'+str(index))
    else:assert actual==expected,(label,'value')

def assert_no_private_ids(value,label):
    if isinstance(value,dict):
        for key,item in value.items():
            assert_no_private_ids(key,label+'/key')
            assert_no_private_ids(item,label+'/'+str(key))
    elif isinstance(value,list):
        for index,item in enumerate(value):assert_no_private_ids(item,label+'/'+str(index))
    elif isinstance(value,str):assert not value.startswith('PRIV-'),(label,'private_id_in_public_table')

def typed_table_roundtrip(root,name,expected,container_rows=None):
    """Read every exported cell; private record_json restores original container rows."""
    jsonrows=[json.loads(line)for line in(root/f'data/{name}.jsonl').read_text().splitlines()if line.strip()]
    assert_typed_equal(jsonrows,expected,name+'/jsonl')
    with(root/f'data/{name}.csv').open(encoding='utf-8-sig',newline='')as stream:
        reader=csv.DictReader(stream);csvrows=list(reader);fields=reader.fieldnames or []
    wanted=builder.columns(expected)if expected else(['dataset_scope','record_json']if container_rows is not None else[])
    assert fields==wanted,(name,'csv_columns')
    assert len(csvrows)==len(expected),(name,'csv_row_count')
    restored=[]
    for index,(raw,row)in enumerate(zip(csvrows,expected)):
        assert set(raw)==set(wanted),(name,index,'csv_fields')
        decoded={}
        for key in wanted:
            value=row.get(key);cell=raw[key]
            assert str(builder.flat(value))==cell,(name,index,key,'csv_cell')
            if key not in row:continue
            if value is None:
                assert cell=='';decoded[key]=None
            elif isinstance(value,str):decoded[key]=cell
            else:decoded[key]=json.loads(cell)
        assert_typed_equal(decoded,row,name+'/csv/'+str(index));restored.append(decoded)
    database=root/'data/museum-conservation.sqlite'
    with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True)as con:
        sqlrows=[json.loads(row[0])for row in con.execute(f'SELECT record_json FROM {name} ORDER BY row_number')]
    assert_typed_equal(sqlrows,expected,name+'/sqlite')
    if container_rows is not None:
        for format_name,rows in [('jsonl',jsonrows),('csv',restored),('sqlite',sqlrows)]:
            # SQLite record_json above contains the exported outer row, whose
            # own record_json must restore the inner original container row.
            inner=[json.loads(row['record_json'])for row in rows]
            assert_typed_equal(inner,container_rows,name+'/'+format_name+'/original_container')
    return {'rows':len(expected),'csv_jsonl_sqlite_typed_equal':True,
            'original_container_restored':container_rows is not None}

def check_optional_art_layers(root,facts,inventory,version):
    """Enable only layers whose actual input exists; never fabricate absent data."""
    root=Path(root).resolve();result={'source_original_semantics_revalidated':False}
    assert_no_private_ids(facts['observations'],'public/observations')
    assert_no_private_ids(facts['body_reviews'],'public/body_reviews')
    for filename in ['metadata/coverage.json','metadata/read_coverage.json',
                     'data/coverage_cells.jsonl','data/coverage_groups.jsonl']:
        path=root/filename
        if path.exists():
            data=([json.loads(line)for line in path.read_text().splitlines()if line.strip()]
                  if path.suffix=='.jsonl'else builder.read(path))
            assert_no_private_ids(data,'public/'+filename)
    result['public_observations_and_coverage_exclude_private_ids']=True
    context_path=root/'data/public_context_notes.json'
    if context_path.exists():
        from public_expansion import validate_context
        rows=validate_context(root,facts,inventory,builder.validate_review_shape)
        assert all(row['annual_quantity_eligible']is False and
                   row['default_aggregation_allowed']is False for row in rows)
        result['public_context']=typed_table_roundtrip(root,'public_context_notes',rows)
        result['expanded_public_organizations']=typed_table_roundtrip(
            root,'expanded_public_organizations',inventory.get('expanded_public_organization_candidates',[]))
    else:result['public_context']={'status':'not_enabled_no_input'}
    if(root/'data/private_art_pilot.json').exists():
        import private_art_pilot
        data=builder.read(root/'data/private_art_pilot.json')
        generated=private_art_pilot.generate(root,version)
        private={}
        for name,(key,identity)in private_art_pilot.TABLE_KEYS.items():
            originals=sorted(data[key],key=lambda row:row[identity])
            private[name]=typed_table_roundtrip(root,name,generated['tables'][name],originals)
        result['private_art']=private
    else:result['private_art']={'status':'not_enabled_no_input'}
    return result

def invalid_auxiliary_preserves_exports(root,relative,cases):
    """Only use a temporary clone; snapshot after the intentional bad-input write."""
    target=root/relative;original=target.read_bytes();good=json.loads(original);pristine=hashes(root);passed=[]
    try:
        for label,mutate,error_code in cases:
            bad=json.loads(json.dumps(good));mutate(bad);target.write_bytes(builder.encode(bad))
            # The intentional input mutation belongs to this baseline. A failed
            # run must not change it or any canonical/derived export afterwards.
            before=hashes(root)
            proc=subprocess.run([sys.executable,str(root/'scripts/build_exports.py'),
                                 '--root',str(root)],capture_output=True,text=True)
            assert proc.returncode!=0 and error_code in proc.stderr,(label,proc.stderr)
            assert hashes(root)==before,(label,'failed_run_changed_files')
            target.write_bytes(original);assert hashes(root)==pristine,(label,'input_not_restored')
            passed.append(label)
    finally:target.write_bytes(original)
    return passed

def check_optional_art_failure_protection(root):
    """Exercise source closure, annual eligibility and private-layer boundaries."""
    result={}
    if(root/'data/public_context_notes.json').exists()and builder.read(root/'data/public_context_notes.json'):
        def bad_context_source(data):data[0]['source_id']='src-selfcheck-missing-source'
        def bad_context_annual(data):data[0]['annual_quantity_eligible']=True
        result['public_context']=invalid_auxiliary_preserves_exports(root,'data/public_context_notes.json',[
            ('context_source_closure',bad_context_source,'context_scope_reference'),
            ('context_cannot_be_annual_quantity',bad_context_annual,'review_schema_const')])
    else:result['public_context']={'status':'not_enabled_no_rows'}
    path=root/'data/private_art_pilot.json'
    if path.exists()and builder.read(path)['observations']:
        def bad_quantity(data):
            row=next(row for row in data['observations']if row['numeric_origin']=='source_reported')
            row['quantity_raw']='999998'if row['quantity_numeric']==999999 else'999999'
        def public_owner(data):data['observations'][0]['organization_id']='BASE-039'
        def bad_source_hash(data):
            row=data['sources'][0];row['original_file_sha256']='a'*64 if row['original_file_sha256']!='a'*64 else'b'*64
        result['private_art']=invalid_auxiliary_preserves_exports(root,'data/private_art_pilot.json',[
            ('private_quantity_raw_numeric_mismatch',bad_quantity,'quantity_conversion'),
            ('private_observation_cannot_use_public_organization',public_owner,'organization_outside_private_container'),
            ('private_source_id_sha_closure',bad_source_hash,'source_id_sha_mismatch')])
    else:result['private_art']={'status':'not_enabled_no_observations'}
    return result

def main():
    facts=builder.read(ROOT/'data/facts.json');inventory=builder.read(ROOT/'metadata/inventory.json');version=(ROOT/'VERSION').read_text().strip()
    checks=builder.validate(facts,inventory,version)
    assert builder.source_number('兩')==2 and builder.source_number('〇')==0
    assert builder.source_number('近兩')is None and builder.source_number('兩組（四件）')is None
    rows=[json.loads(line)for line in(ROOT/'data/observations.jsonl').read_text().splitlines()]
    assert rows==facts['observations']
    # An inspection subrow remains inspection even under a treatment-table title.
    npm_inspections=[r for r in rows if r['organization_id']=='BASE-023' and r['metric_class']=='museum_reported_inspection']
    assert len(npm_inspections)==10
    assert all(r['action_categories']==['inspection_registration'] for r in npm_inspections)
    npm_2025=next(r for r in npm_inspections if r['observation_id']=='NPM-2025-finalaccounts-inspection')
    assert npm_2025['metric_as_reported']=='文物狀況檢示'
    assert npm_2025['quantity_raw']=='3,109' and npm_2025['quantity_numeric']==3109
    assert npm_2025['unit_as_reported']=='件' and npm_2025['publication_year']is None
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
    current=builder.current_reviews(reviews)
    extended={r['extends_review_id']for r in reviews if r.get('extends_review_id')}
    assert {r['review_id']for r in current}=={r['review_id']for r in reviews}-extended
    # Independent current evidence for the same museum-year must survive.
    assert len(current)>len({(r['organization_id'],r['target_data_year'])for r in current})
    coverage=builder.read(ROOT/'metadata/read_coverage.json')['body_reviews']
    assert coverage['current_record_count']==len(current)
    # A writer-version header difference can preserve logical content. The artifact
    # hash still binds its exact bytes, while schema/row corruption is rejected.
    sqlite_bytes=(ROOT/'data/museum-conservation.sqlite').read_bytes()
    alternate=bytearray(sqlite_bytes)
    alternate_version=3040001 if int.from_bytes(sqlite_bytes[96:100],'big')==3051000 else 3051000
    alternate[96:100]=alternate_version.to_bytes(4,'big')
    assert bytes(alternate)!=sqlite_bytes
    assert builder.sqlite_logically_equal(sqlite_bytes,bytes(alternate))
    with tempfile.TemporaryDirectory()as sqltmp:
        other=Path(sqltmp)/'changed.sqlite';other.write_bytes(sqlite_bytes)
        with sqlite3.connect(other)as con:con.execute("UPDATE observations SET quantity_raw='999999' WHERE rowid=1")
        assert not builder.sqlite_logically_equal(sqlite_bytes,other.read_bytes())
    review_lines=[json.loads(line)for line in(ROOT/'data/body_reviews.jsonl').read_text().splitlines()]
    assert reviews==review_lines
    with sqlite3.connect(ROOT/'data/museum-conservation.sqlite')as con:
        assert [json.loads(r[0])for r in con.execute('SELECT record_json FROM body_reviews ORDER BY row_number')]==reviews
    optional_art=check_optional_art_layers(ROOT,facts,inventory,version)
    # Multi-year values are stored once with a period, never assigned to a single year.
    multi=json.loads(json.dumps(facts));mr=multi['observations'][0]
    mr.update(data_year=None,reporting_period_raw='2020–2022',data_year_start=2020,data_year_end=2022,year_assignment_status='multi_year_not_allocated')
    builder.validate(multi,inventory,version)
    mr['data_year']=2021
    try:builder.validate(multi,inventory,version)
    except AssertionError:pass
    else:raise AssertionError('multi-year figure silently became a single-year value')
    # Synthetic contract fixture: an HTML source has a body locator, never borrowed PDF pages.
    html=json.loads(json.dumps(facts));hr=html['observations'][0]
    hr.update(source_id=next(s['source_id']for s in html['sources']if s['original_file_type']=='HTML'),pdf_page_1_based=None,printed_page=None,source_locator='synthetic annual body locator')
    html['summary']['numeric_support_source_file_versions']=len({r['source_id']for r in html['observations']})
    builder.validate(html,inventory,version)
    for key,badvalue in [('pdf_page_1_based',1),('printed_page','13'),('source_locator','')]:
        bad=json.loads(json.dumps(html));bad['observations'][0][key]=badvalue
        try:builder.validate(bad,inventory,version)
        except AssertionError:pass
        else:raise AssertionError('HTML locator contract accepted invalid '+key)
    bad=json.loads(json.dumps(facts));pr=next(r for r in bad['observations']if next(s for s in bad['sources']if s['source_id']==r['source_id'])['original_file_type']=='PDF');pr['pdf_page_1_based']=None
    try:builder.validate(bad,inventory,version)
    except AssertionError:pass
    else:raise AssertionError('PDF observation lost its real page')
    with tempfile.TemporaryDirectory()as tmp:
        root=Path(tmp)/'pilot';root.mkdir()
        for folder in ['data','metadata','scripts','catalog','schema','docs']:shutil.copytree(ROOT/folder,root/folder,ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copy(ROOT/'VERSION',root/'VERSION')
        cmd=[sys.executable,str(root/'scripts/build_exports.py')]
        before=hashes(root)
        same=subprocess.run(cmd,capture_output=True,text=True);assert same.returncode==0,same.stderr
        assert json.loads(same.stdout)['status']=='unchanged';assert hashes(root)==before
        optional_art_failures=check_optional_art_failure_protection(root)
        assert hashes(root)==before
        # Wrong number: reject before replacing any release data.
        bad=json.loads(json.dumps(facts));r=next(r for r in bad['observations']if r['quantity_numeric']is not None and r['numeric_origin']=='source_reported');r['quantity_numeric']+=1
        candidate=Path(tmp)/'invalid.json';candidate.write_bytes(builder.encode(bad))
        result=subprocess.run(cmd+['--candidate-facts',str(candidate)],capture_output=True,text=True)
        assert result.returncode!=0 and hashes(root)==before
        # An absent source string cannot turn into an invented numeric zero.
        bad=json.loads(json.dumps(facts));r=next(r for r in bad['observations']if r['numeric_origin']=='source_reported');r['quantity_raw']=None;r['quantity_numeric']=0
        candidate.write_bytes(builder.encode(bad));result=subprocess.run(cmd+['--candidate-facts',str(candidate)],capture_output=True,text=True)
        assert result.returncode!=0 and hashes(root)==before
        # New original observations must satisfy the complete declared shape
        # before the writer can replace any canonical or exported artifact.
        for field,expected in [('numeric_origins','summary_numeric_origins_stale'),('units','summary_unit_rows_stale'),('numeric_support_source_file_versions','summary_fact_source_versions_stale')]:
            bad=json.loads(json.dumps(facts))
            if field=='numeric_origins':bad['summary'][field]['source_reported']-=1
            elif field=='units':bad['summary'][field]['件']-=1
            else:bad['summary'][field]-=1
            candidate.write_bytes(builder.encode(bad));result=subprocess.run(cmd+['--candidate-facts',str(candidate)],capture_output=True,text=True)
            assert result.returncode!=0 and expected in result.stderr and hashes(root)==before,(field,result.stderr)
        for case in ['missing_aggregation_role','year_above_schema_maximum']:
            bad=json.loads(json.dumps(facts))
            if case=='missing_aggregation_role':
                del bad['observations'][-1]['aggregation_role'];expected='review_schema_required'
            else:
                bad['observations'][-1]['data_year']=2101;expected='review_schema_maximum'
            candidate.write_bytes(builder.encode(bad));result=subprocess.run(cmd+['--candidate-facts',str(candidate)],capture_output=True,text=True)
            assert result.returncode!=0 and expected in result.stderr and hashes(root)==before,(case,result.stderr)
        # Actual review evidence fields must match the published nested schema.
        # Reject each malformed candidate before any existing export is replaced.
        for case in ['missing_scope','unknown_evidence_field','boolean_page','page_outside_review']:
            bad=json.loads(json.dumps(facts));review=next(r for r in bad['body_reviews']if any('image_viewed_pdf_pages_1_based'in d for d in r['source_page_reviews']))
            detail=next(d for d in review['source_page_reviews']if 'image_viewed_pdf_pages_1_based'in d)
            if case=='missing_scope':del review['review_scope'];expected='review_schema_required'
            elif case=='unknown_evidence_field':detail['image_page_count']=1;expected='review_schema_additional_property'
            elif case=='boolean_page':detail['image_viewed_pdf_pages_1_based']=[True];expected='review_schema_type'
            else:detail['image_viewed_pdf_pages_1_based']=[99999];expected='review_evidence_outside_reviewed_pages'
            candidate.write_bytes(builder.encode(bad));result=subprocess.run(cmd+['--candidate-facts',str(candidate)],capture_output=True,text=True)
            assert result.returncode!=0 and expected in result.stderr and hashes(root)==before,(case,result.stderr)
        # Broken lineage must not hide a current record or replace prior exports.
        for case in ['self_cycle','two_record_cycle','different_year_parent','different_museum_parent']:
            bad=json.loads(json.dumps(facts));review=next(r for r in bad['body_reviews']if r.get('extends_review_id'));parent=next(r for r in bad['body_reviews']if r['review_id']==review['extends_review_id'])
            if case=='self_cycle':review['extends_review_id']=review['review_id'];expected='review_extension_cycle'
            elif case=='two_record_cycle':parent['extends_review_id']=review['review_id'];expected='review_extension_cycle'
            elif case=='different_year_parent':review['target_data_year']=parent['target_data_year']+1;expected='review_parent_scope_mismatch'
            else:review['organization_id']='synthetic-other-museum';expected='review_parent_scope_mismatch'
            candidate.write_bytes(builder.encode(bad));result=subprocess.run(cmd+['--candidate-facts',str(candidate)],capture_output=True,text=True)
            assert result.returncode!=0 and expected in result.stderr and hashes(root)==before,(case,result.stderr)
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
        # Logically equal SQLite bytes cannot silently replace the manifest-bound artifact.
        shutil.copy(ROOT/'data/observations.csv',target)
        target=root/'data/museum-conservation.sqlite';target.write_bytes(bytes(alternate));broken=hashes(root)
        result=subprocess.run(cmd+['--check'],capture_output=True,text=True)
        assert result.returncode!=0 and hashes(root)==broken
    import check_enrichment
    enriched=check_enrichment.check(ROOT)
    print(json.dumps({'status':'pass','checks':checks,'enrichment':enriched,'csv_jsonl_sqlite_equal':True,'sqlite_portable_content_and_exact_artifact_checks':True,'html_locator_contract':True,'body_review_nested_schema_and_page_scope':True,'invalid_candidate_preserves_previous':True,'changed_source_requires_review':True,'unchanged_writes_zero_files':True,'check_detects_export_corruption_without_writing':True,'optional_art_layers':optional_art,'optional_art_input_failure_protection':optional_art_failures},ensure_ascii=False))
if __name__=='__main__':main()
