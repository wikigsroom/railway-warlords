"""Archive production evidence and publish hashes of locally retained research."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, shutil, zipfile
from build_release import P, ROOT, current_version
from package_delivery import read, sha, require

def main():
    base=ROOT/'output/commander_expansion'; raw=ROOT/'output/imagegen/warlord/commander_expansion_v0228'
    target=P/'docs/commander-production'; target.mkdir(parents=True,exist_ok=True)
    names=['martyr_commanders','ndl_commanders','deputy_commanders','cpc_commanders',
        'eccp_commanders','boorman_commanders','essential_commanders']
    proofs=[read(raw/(name+'_generation.json')) for name in names]
    require(all(r['terminal'] and r['passed'] and not r['failed'] for r in proofs)
        and sum(r['generated'] for r in proofs)==1180,'All seven portrait cohorts must finish before archival')
    originals=[]
    for proof in proofs:originals.extend(proof['records'])
    require(len({r['id'] for r in originals})==1180,'Duplicate portrait production identity')
    copied=[]
    for path in sorted(base.glob('*')):
        if not path.is_file() or path.suffix not in {'.py','.json'}:continue
        if path.name=='portrait_cohort_progress.json':continue
        dest=target/'workspace'/path.name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,dest);copied.append(dest)
    for name in names:
        path=raw/(name+'_generation.json');dest=target/'generation'/path.name
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest);copied.append(dest)
    # Keep complete downloaded publications in the research workspace. Public
    # source delivery includes the source URLs, authored facts and byte index.
    members=[];research_files=[]
    for path in sorted((base/'research').rglob('*')):
        if not path.is_file() or path.suffix not in {'.html','.txt','.pdf','.json'}:continue
        name=path.relative_to(base/'research').as_posix();research_files.append((path,name))
        members.append(dict(file=name,sha256=sha(path),bytes=path.stat().st_size))
    bundle=base/'archival/historical-source-cache.zip';bundle.parent.mkdir(parents=True,exist_ok=True)
    previous=target/'historical-source-cache.zip'
    if previous.exists():
        require(not bundle.exists(),'Research archive already exists at both locations')
        shutil.move(str(previous),str(bundle))
    if not bundle.exists():
        with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as archive:
            for path,name in research_files:archive.write(path,name)
    with zipfile.ZipFile(bundle) as archive:
        require(archive.testzip() is None,'Research archive CRC failed')
        require(sorted(archive.namelist())==sorted(r['file'] for r in members),'Research archive members changed')
        for row in members:
            with archive.open(row['file']) as stream:
                require(hashlib.file_digest(stream,'sha256').hexdigest()==row['sha256'],
                    'Research archive bytes changed: '+row['file'])
    public_cache=dict(version=current_version(),included_in_public_source=False,
        note='Complete research publications stay in the local workspace; public provenance contains URLs, authored facts and member hashes.',
        source_urls='content/definitions/commander_sources.json',
        local_archive=bundle.relative_to(ROOT).as_posix(),archive_sha256=sha(bundle),
        archive_bytes=bundle.stat().st_size,members=members)
    cache_index=target/'historical-source-cache-index.json'
    cache_index.write_text(json.dumps(public_cache,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    copied.append(cache_index)
    index=dict(version=current_version(),production_terminal=True,generated_originals=1180,
        route='sub2-image-gen/gpt-image-2.5/high',source_rasters_modified=False,
        formal_art_approval=False,historical_likeness_approval=False,
        full_service_tenures_verified=False,complete_historical_orders_of_battle=False,
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        original_images='assets/portrait: engine files retain each generated PNG byte; not duplicated in this research folder',
        prompts='docs/asset-prompts: immutable prompt copies, SHA-bound by assets/manifest.json',
        files=[dict(file=p.relative_to(P).as_posix(),sha256=sha(p),bytes=p.stat().st_size) for p in copied],
        historical_cache_members=members,historical_cache_included_in_public_source=False)
    (target/'index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=True,archived_files=len(copied),cached_source_files=len(members),originals=1180)),flush=True)

if __name__=='__main__':main()
