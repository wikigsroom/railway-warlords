"""Refresh documented media using complete, byte-identical native captures."""
import json, shutil
from build_release import P,current_version,source_digest
from package_delivery import read,sha,require

def main():
    version=current_version();runtime=source_digest()[0]
    proof=read(P/'reports/commander_roster_native_evidence.json')
    require(proof['passed'] and proof['version']==version and proof['runtime_source_sha256']==runtime,'Current commander viewport proof required')
    registered={r['file']:r for g in proof['groups'] for r in g['captures']}
    manifest=read(P/'docs/media/manifest.json')
    for row in manifest['screenshots']:
        if row.get('historical_capture'):continue
        source=P/row['native_source'];meta=source.with_suffix('.json')
        require(source.is_file() and meta.is_file(),'Missing retained native source: '+str(source))
        details=read(meta)
        # Old dated previews may intentionally retain their recorded version.
        if details['build_version']!=version:continue
        target=P/row['file'];shutil.copyfile(source,target)
        destination=P/row['metadata'];shutil.copyfile(meta,destination)
        row.update(version=version,sha256=sha(source),byte_identical_to_native_capture=True)
    additions=[('commander-catalogue-v0228.png','windows/commander_catalogue.png'),
        ('commander-japan-division-v0228.png','windows/japanese_division_commanders.png'),
        ('commander-reserves-v0228.png','windows/scenario_reserve_appointment.png'),
        ('commander-appointed-v0228.png','windows/reserve_appointed.png'),
        ('commander-x30-layout-v0228.png','x30_layout/commander_catalogue.png')]
    replace={'docs/media/'+name for name,_ in additions}
    manifest['screenshots']=[r for r in manifest['screenshots'] if r['file'] not in replace]
    for name,relative in additions:
        source=P/'reports/screenshots/commander_roster_native'/relative;meta=source.with_suffix('.json')
        checked=registered[source.relative_to(P).as_posix()]
        require(sha(source)==checked['sha256'] and sha(meta)==checked['metadata_sha256'],'Commander capture changed')
        target=P/'docs/media'/name;shutil.copyfile(source,target);shutil.copyfile(meta,target.with_suffix('.json'))
        manifest['screenshots'].append(dict(file=target.relative_to(P).as_posix(),version=version,
            native_source=source.relative_to(P).as_posix(),sha256=sha(source),
            metadata=target.with_suffix('.json').relative_to(P).as_posix(),
            byte_identical_to_native_capture=True,historical_capture=False,physical_android_device_tested=False))
    manifest.update(version=version,current_commander_native_evidence='reports/commander_roster_native_evidence.json',
        notice='Complete current Windows native viewports copied without pixel processing. Explicitly dated old stills and battle GIFs keep their recorded versions. Desktop X30 proportions do not constitute physical phone acceptance.')
    (P/'docs/media/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=True,screenshots=len(manifest['screenshots']),new_commander_captures=len(additions))),flush=True)

if __name__=='__main__':main()
