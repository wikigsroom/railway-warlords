"""Check every pre-existing content/presentation JSON against delivered 0.2.25."""
import hashlib
import json
import subprocess
from build_release import P,current_version,source_digest

BASELINE='1d4a9c95d3d1cf214490dac69d166dab6f19e9a7'
MAPS=['asia_strategic','conquest_china','jingfeng','jingjin']
ALLOWED={'content/geography_sources.json','presentation/data/control_land_clip.json',
         'presentation/data/ground_coverage.json','presentation/data/hydrography_fine.json'}
ALLOWED.update('content/maps/'+mid+'.json' for mid in MAPS)
ALLOWED.update('presentation/data/ground_coverage_'+mid+'.json' for mid in MAPS)


def main():
    tree=subprocess.check_output(['git','ls-tree','-r','-z',BASELINE,'--','content','presentation/data'],cwd=P)
    rows=[]
    for entry in tree.split(b'\0'):
        if not entry:continue
        header,name=entry.split(b'\t',1);relative=name.decode('utf-8')
        if not relative.endswith('.json'):continue
        data=(P/relative).read_bytes();old=header.split()[2].decode('ascii')
        actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        rows.append(dict(file=relative,baseline_git_blob=old,current_git_blob=actual,
                         preserved=old==actual,sha256=hashlib.sha256(data).hexdigest()))
    changed={row['file'] for row in rows if not row['preserved']};unexpected=sorted(changed-ALLOWED)
    geography=json.loads((P/'reports/coast_detail_geography_audit.json').read_text(encoding='utf-8'))
    bound=geography['passed'] and all(row['map_sha256']==hashlib.sha256((P/f"content/maps/{row['map_id']}.json").read_bytes()).hexdigest() for row in geography['maps'])
    result=dict(passed=bool(rows) and not unexpected and bound,version=current_version(),
        runtime_source_sha256=source_digest()[0],baseline_commit=BASELINE,
        checked_existing_json_files=len(rows),preserved_json_files=sum(r['preserved'] for r in rows),
        allowed_changed_files=sorted(ALLOWED),actual_changed_files=sorted(changed),unexpected_changed_files=unexpected,
        independent_raw_geography_audit_bound=bound,files=rows,
        scope='Only four marine drawing fields/source registration and recompiled land-dependent display meshes may change. Every other pre-existing JSON retains its delivered bytes. Nonvisual map fields and all old geographic source records have a separate independent source audit.')
    (P/'reports/coast_detail_scope_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='files'}),flush=True)
    raise SystemExit(0 if result['passed'] else 1)


if __name__=='__main__':main()
