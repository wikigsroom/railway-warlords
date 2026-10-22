"""Export a clearly labelled review build from the byte-verified native copy.

The source identity is a canonical per-file SHA256 map. Immutable art hashes
come from the complete copy verification; current code/data are rehashed.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
import json
import os
import subprocess
import time
from build_release import ENGINE,JAVA,SDK,CREDENTIALS

P=Path(__file__).resolve().parents[1];ROOT=P.parents[1]
STAGE=ROOT/'game/railway_warlords_review_0237'
R=P/'reports/geographic_ground_v0237'
FOLDERS={'app','content','domain','ai','presentation','persistence','audio','schemas','assets'}


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    receipt=R/'preview_export01.json'
    if receipt.exists():raise FileExistsError('Immutable review export receipt')
    stage_proof=json.loads((R/'preview_stage01.json').read_bytes())
    seal_time=datetime.fromisoformat(stage_proof['created_at_utc']).timestamp()
    expected={n:s for n,s in stage_proof['file_sha256'].items()
              if n.split('/')[0] in FOLDERS or n in ['project.godot','export_presets.cfg']}
    stamps={};identities={}
    for name,checksum in expected.items():
        file=STAGE/name;stat=file.stat()
        # Raw art was fully hashed in both authority and copy. Nothing in the
        # test/export flow writes original art. Rehash any later-touched file.
        retained=name.startswith('assets/') and stat.st_mtime<=seal_time
        actual=checksum if retained else sha(file)
        if actual!=checksum:raise ValueError('Preview source differs from sealed copy: '+name)
        identities[name]=actual;stamps[name]=(stat.st_size,stat.st_mtime_ns)
    canonical=json.dumps(identities,sort_keys=True,separators=(',',':')).encode()
    merkle=hashlib.sha256(canonical).hexdigest()
    env=os.environ.copy();env['JAVA_HOME']=str(JAVA);env['ANDROID_HOME']=str(SDK)
    env['PATH']=str(JAVA/'bin')+os.pathsep+env['PATH']
    key=json.loads(CREDENTIALS.read_bytes())
    env['GODOT_ANDROID_KEYSTORE_RELEASE_PATH']=key['path']
    env['GODOT_ANDROID_KEYSTORE_RELEASE_USER']=key['alias']
    env['GODOT_ANDROID_KEYSTORE_RELEASE_PASSWORD']=key['password']
    results=[]
    for target,preset,filename in [('windows','Windows','RailwayWarlords.exe'),('android','Android','RailwayWarlords.apk')]:
        out=STAGE/'build'/target/filename;out.parent.mkdir(parents=True,exist_ok=True)
        if out.exists():raise FileExistsError('Refuse to replace review binaries')
        log=R/('preview_export_'+target+'01.log')
        command=[str(ENGINE),'--headless','--path',str(STAGE),'--export-release',preset,str(out)]
        started=time.monotonic()
        with log.open('x',encoding='utf-8') as stream:
            child=subprocess.Popen(command,cwd=STAGE,env=env,stdout=stream,stderr=subprocess.STDOUT)
            print(f'PREVIEW_EXPORT {target} PID {child.pid}',flush=True)
            try:code=child.wait(timeout=2400)
            except subprocess.TimeoutExpired:
                child.kill();child.wait(timeout=15);raise
        diagnostic=log.read_text(encoding='utf-8',errors='replace')
        errors=[line for line in diagnostic.splitlines() if any(m in line for m in ['SCRIPT ERROR:','SHADER ERROR:','\nERROR:','Export failed']) or line.startswith('ERROR:')]
        if code or errors or not out.exists() or out.stat().st_size<1000000:raise RuntimeError(f'Preview {target} export failed: '+str(errors[-4:]))
        for name,stamp in stamps.items():
            file=STAGE/name;stat=file.stat()
            if (stat.st_size,stat.st_mtime_ns)!=stamp and sha(file)!=identities[name]:
                raise RuntimeError('Source changed during preview export: '+name)
        results.append(dict(target=target,passed=True,exit_code=code,path=str(out),bytes=out.stat().st_size,
                            sha256=sha(out),elapsed_seconds=round(time.monotonic()-started,2),
                            log=log.relative_to(P).as_posix(),log_sha256=sha(log),command=command,
                            runtime_source_merkle_sha256=merkle))
        print(json.dumps(results[-1]),flush=True)
    proof=dict(passed=True,version='0.2.37',android_version_code=42,channel='development_review',
               created_at_utc=datetime.now(timezone.utc).isoformat(),controller_sha256=sha(__file__),
               stage_copy_receipt_sha256=sha(R/'preview_stage01.json'),
               identity_method='SHA256 of canonical sorted runtime file-name/SHA256 map; complete copy SHA256 plus current code/data and changed-file checks',
               runtime_source_merkle_sha256=merkle,runtime_file_sha256=identities,artifacts=results,
               official_release=False,formal_art_approval=False,physical_android_device_tested=False)
    with receipt.open('x',encoding='utf-8',newline='\n') as stream:json.dump(proof,stream,indent=2);stream.write('\n')


if __name__=='__main__':main()
