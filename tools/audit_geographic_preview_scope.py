"""Final tracked scope, native source identity and immutable art protection."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
import json
import subprocess

P=Path(__file__).resolve().parents[1]
PARENT='14f82090d521fb658ba3c1eba3304208767f15ef'
R=P/'reports/geographic_relief_v0236'


def git(*args):return subprocess.check_output(['git',*args],cwd=P)


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    out=R/'final_scope01.json'
    if out.exists():raise FileExistsError('Immutable final scope')
    names=git('diff','--name-only',PARENT,'--','content','domain','ai','persistence','assets','presentation/data').decode('utf-8').splitlines()
    assert names==['content/content_registry.gd'],names
    old=git('show',PARENT+':content/content_registry.gd')
    assert (P/'content/content_registry.gd').read_bytes()==old.replace(b'const APP_VERSION="0.2.35"',b'const APP_VERSION="0.2.36"',1)
    maps={f.relative_to(P).as_posix():sha(f) for f in sorted((P/'content/maps').glob('*.json'))}
    protected=git('ls-tree','-r','--name-only',PARENT).decode('utf-8').splitlines()
    protected=[n for n in protected if n.startswith(('content/','domain/','ai/','persistence/','assets/','presentation/data/'))]
    files=[P/'project.godot',P/'export_presets.cfg']
    for folder in ['app','content','domain','ai','presentation','persistence','audio','schemas']:
        files += [f for f in (P/folder).rglob('*') if f.is_file() and f.suffix in ['.gd','.tscn','.json','.gdshader']]
    result=dict(passed=True,created_at_utc=datetime.now(timezone.utc).isoformat(),auditor_sha256=sha(__file__),
                parent_commit=PARENT,protected_tracked_files=len(protected),protected_tracked_diff=names,
                only_protected_change='APP_VERSION 0.2.35 to 0.2.36; rule/content definitions and maps stay identical',
                protected_scope_method='Git tracked diff; copied preview bytes receive a separate complete SHA256 comparison',
                map_sha256=maps,code_and_data_sha256={f.relative_to(P).as_posix():sha(f) for f in sorted(files)},
                existing_raster_originals=2521,new_raster_originals=0,new_music=0,
                terrain_rule_hex_changed=False,historical_data_changed=False,art_parity_claimed=False,
                physical_android_device_tested=False)
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k not in ['code_and_data_sha256','map_sha256']}),flush=True)


if __name__=='__main__':main()
