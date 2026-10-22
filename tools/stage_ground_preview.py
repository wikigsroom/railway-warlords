"""Native sibling checkout for preview validation; preserve old release reports.

Copies all source/art bytes. Only Godot's disposable imported-resource cache is
shared through an NTFS directory junction. No VM/container/emulator is used.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
import json
import shutil
import subprocess

P=Path(__file__).resolve().parents[1];ROOT=P.parents[1]
STAGE=ROOT/'game/railway_warlords_review_0237'
R=P/'reports/geographic_ground_v0237'


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    if STAGE.exists():raise FileExistsError('Refuse to replace a preview validation tree')
    STAGE.mkdir();(STAGE/'reports').mkdir()
    for name in ['project.godot','export_presets.cfg','AGENTS.md']:
        shutil.copy2(P/name,STAGE/name)
    for folder in ['app','content','domain','ai','presentation','persistence','audio','schemas','tests','tools','assets']:
        shutil.copytree(P/folder,STAGE/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        print('Copied native preview directory '+folder,flush=True)
    cache=STAGE/'.godot';cache.mkdir()
    for name in ['global_script_class_cache.cfg','uid_cache.bin']:
        if (P/'.godot'/name).exists():shutil.copy2(P/'.godot'/name,cache/name)
    # Fixed literal paths, no recursive move/delete or shell-built path commands.
    link=cache/'imported';target=P/'.godot/imported'
    command='New-Item -ItemType Junction -Path '+"'"+str(link).replace("'","''")+"' -Target '"+str(target).replace("'","''")+"' | Out-Null"
    subprocess.run(['powershell.exe','-NoProfile','-Command',command],check=True)
    for path in [R/'source_probes01.json']:
        dest=STAGE/path.relative_to(P);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    files=[]
    for folder in ['app','content','domain','ai','presentation','persistence','audio','schemas','tests','tools','assets']:
        files.extend(p for p in (P/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    files.extend([P/'project.godot',P/'export_presets.cfg',P/'AGENTS.md'])
    identities={}
    for f in sorted(files):
        name=f.relative_to(P).as_posix();original=sha(f);copied=sha(STAGE/name)
        if original!=copied:raise RuntimeError('Preview copy differs: '+name)
        identities[name]=original
    proof=dict(passed=True,created_at_utc=datetime.now(timezone.utc).isoformat(),
               controller_sha256=sha(__file__),authority_project=str(P),validation_project=str(STAGE),
               original_project_reports_preserved=True,files_copied_and_byte_verified=len(identities),
               file_sha256=identities,shared_disposable_cache=str(target),
               native_windows=True,virtualization_used=False,physical_android_device_tested=False)
    with (R/'preview_stage01.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(proof,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in proof.items() if k!='file_sha256'}),flush=True)


if __name__=='__main__':main()
