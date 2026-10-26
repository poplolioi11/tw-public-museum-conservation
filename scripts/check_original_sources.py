#!/usr/bin/env python3
"""Opt-in source byte revalidation; downloads stay outside the repository.

python scripts/check_original_sources.py --cache-dir /absolute/cache --download
Without --download, check only files already present in the named cache directory.
The published package does not contain source PDFs. No candidate is overwritten.
"""
import argparse, concurrent.futures, hashlib, json, os, tempfile, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check(source,cache,download):
    h=source['original_file_sha256'];kind=source['original_file_type'];target=cache/(h+('.pdf'if kind=='PDF'else'.html'))
    result={'source_id':source['source_id'],'expected_sha256':h,'expected_bytes':source['original_file_bytes']}
    if not target.exists():
        if not download:return result|{'status':'not_in_cache_not_revalidated'}
        if not source['official_file_url']:return result|{'status':'file_url_not_yet_resolved'}
        temp=None
        try:
            req=urllib.request.Request(source['official_file_url'],headers={'User-Agent':'museum-conservation-data-source-check/0.1'})
            with urllib.request.urlopen(req,timeout=35)as response,tempfile.NamedTemporaryFile(dir=cache,delete=False)as f:
                temp=Path(f.name);total=0
                while b:=response.read(1024*1024):
                    total+=len(b)
                    if total>180*1024*1024:raise ValueError('source exceeds download bound')
                    f.write(b)
            actual=hashlib.sha256(temp.read_bytes()).hexdigest()
            if actual!=h or temp.stat().st_size!=source['original_file_bytes']:
                return result|{'status':'source_changed_review_required','actual_sha256':actual,'actual_bytes':temp.stat().st_size}
            os.replace(temp,target);temp=None
        except Exception as e:return result|{'status':'fetch_failed_not_zero','error_type':type(e).__name__}
        finally:
            if temp and temp.exists():temp.unlink()
    actual=hashlib.sha256(target.read_bytes()).hexdigest()
    ok=actual==h and target.stat().st_size==source['original_file_bytes']and(kind!='PDF'or target.open('rb').read(5)==b'%PDF-')
    return result|{'status':'bytes_match_recorded_version'if ok else'cache_mismatch_review_required','actual_sha256':actual}
def main():
    p=argparse.ArgumentParser();p.add_argument('--cache-dir',type=Path,required=True);p.add_argument('--download',action='store_true');p.add_argument('--workers',type=int,default=2);args=p.parse_args()
    cache=args.cache_dir.resolve();assert ROOT!=cache and ROOT not in cache.parents,'Keep original source cache outside the public checkout.'
    cache.mkdir(parents=True,exist_ok=True)
    data=json.loads((ROOT/'data/facts.json').read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,min(4,args.workers)))as pool:results=list(pool.map(lambda s:check(s,cache,args.download),data['sources']))
    print(json.dumps({'dataset_version':data['dataset_version'],'source_byte_checks_only_not_content_reinterpretation':True,'results':results},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
