"""Native resumable HTTP-range retrieval of the unchanged official ZIP.

Each response is checked against Content-Range. The final bytes must match the
source server's SHA-1 and ZIP CRCs before the archive enters the source folder.
This joins network byte ranges; it never reads, generates or combines images.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import hashlib
import json
import re
import time
import urllib.request
import zipfile
from fetch_surface_geodata import DEST, ROOT, download

URL='https://data.hydrosheds.org/file/HydroRIVERS/HydroRIVERS_v10_as_shp.zip'
CACHE=ROOT/'.toolchain/geodata_download_cache/hydrorivers_as'
UA='RailwayWarlordsGeographicSourceAudit/0.2.12'


def response(start,end):
    return urllib.request.urlopen(urllib.request.Request(URL,headers={
        'Range':f'bytes={start}-{end}','User-Agent':UA}),timeout=60)


def main():
    CACHE.mkdir(parents=True,exist_ok=True)
    with response(0,1023) as stream:
        total=int(stream.headers['Content-Range'].split('/')[-1])
        expected_sha1=stream.headers['x-bz-content-sha1']
        if len(stream.read())!=1024:raise RuntimeError('Probe byte range truncated')
    chunk_size=512*1024
    ranges=[(start,min(start+chunk_size,total)-1) for start in range(0,total,chunk_size)]
    cached=[]
    for path in CACHE.glob('*.part'):
        match=re.fullmatch(r'(\d+)-(\d+)\.part',path.name)
        if match:
            first,last=map(int,match.groups())
            if path.stat().st_size==last-first+1:cached.append((first,last,path))

    def get(item):
        start,end=item;path=CACHE/f'{start:012d}-{end:012d}.part'
        if path.exists() and path.stat().st_size==end-start+1:return path
        for first,last,prior in cached:
            if first<=start<=end<=last:
                data=prior.read_bytes()[start-first:end-first+1]
                path.write_bytes(data);return path
        for attempt in range(4):
            try:
                with response(start,end) as stream:
                    expected=f'bytes {start}-{end}/{total}'
                    if stream.status!=206 or stream.headers['Content-Range']!=expected:
                        raise RuntimeError('Server ignored requested range')
                    chunks=[];started=time.monotonic()
                    while block:=stream.read(64*1024):
                        chunks.append(block)
                        if time.monotonic()-started>75:raise TimeoutError('Slow source range; retry exact bytes')
                    data=b''.join(chunks)
                if len(data)!=end-start+1:raise RuntimeError('Truncated network range')
                path.write_bytes(data);return path
            except Exception:
                if attempt==3:raise
                time.sleep(3*(attempt+1))

    completed={}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures={pool.submit(get,item):item[0] for item in ranges}
        for future in as_completed(futures):
            completed[futures[future]]=future.result()
            if len(completed)%8==0 or len(completed)==len(ranges):
                print(f'HydroRIVERS verified byte ranges {len(completed)}/{len(ranges)}',flush=True)
    target=DEST/'HydroRIVERS_v10_as_shp.zip';temp=CACHE/'verified_archive.zip'
    digest=hashlib.sha1()
    with temp.open('wb') as output:
        for start in sorted(completed):
            data=completed[start].read_bytes();digest.update(data);output.write(data)
    if digest.hexdigest()!=expected_sha1:raise RuntimeError('Official source SHA-1 mismatch')
    with zipfile.ZipFile(temp) as archive:
        if archive.testzip() is not None:raise RuntimeError('Official ZIP CRC mismatch')
    if target.exists():
        if hashlib.sha256(target.read_bytes()).digest()!=hashlib.sha256(temp.read_bytes()).digest():
            raise RuntimeError('Refuse to overwrite a different original')
    else:temp.replace(target)
    record=download(URL)
    (DEST/'hydrorivers_download_verification.json').write_text(json.dumps(dict(
        record=record,official_server_sha1=expected_sha1,sha1_matches=True,zip_crc_verified=True,
        original_source_modified=False,download_method='native HTTP byte ranges'),indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
