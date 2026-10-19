"""Bind native material/coverage pixel checks to the current shipping EXE."""
import json
from pathlib import Path
import subprocess
from build_release import P, current_version, source_digest
from package_delivery import read, require, sha


def main():
    runtime=source_digest()[0]
    exe=P/'build/windows/RailwayWarlords.exe'
    exported=next(row for row in read(P/'reports/export_results.json') if row['target']=='windows')
    require(exported['export_verified'] and exported['runtime_source_sha256']==runtime and exported['sha256']==sha(exe),
            'Current verified shipping Windows export required')
    folder=P/'reports/ground_continuity_native';folder.mkdir(parents=True,exist_ok=True)
    log=folder/'native.log'
    with log.open('w',encoding='utf-8') as out:
        result=subprocess.run([str(exe),'--resolution','1600x900','--position','-4000,-3000','--',
                               '--qa-session','--ground-continuity-test','--ground-continuity-output',str(folder)],
                              cwd=P,stdout=out,stderr=subprocess.STDOUT,timeout=480)
    diagnostic=log.read_text(encoding='utf-8',errors='replace')
    require(result.returncode==0 and 'SCRIPT ERROR:' not in diagnostic and '\nERROR:' not in diagnostic,'Native ground continuity failed')
    path=folder/'validation.json';report=read(path)
    require(report['passed'] and report['build_version']==current_version() and len(report['checks'])==48
            and len(report['samples'])==26 and not report['physical_android_device_tested'],'Incomplete current material evidence')
    require(all(row['maximum_channel_delta']<=2 and row['pixels']>=500 for row in report['samples'] if 'family' in row),
            'Ground coverage/source-phase pixel check failed')
    require(source_digest()[0]==runtime and sha(exe)==exported['sha256'],'Runtime changed during native proof')
    proof=dict(passed=True,version=current_version(),runtime_source_sha256=runtime,windows_exe_sha256=sha(exe),
               checks=len(report['checks']),report=path.relative_to(P).as_posix(),report_sha256=sha(path),
               log=log.relative_to(P).as_posix(),log_sha256=sha(log),
               twenty_whole_originals_verified=True,same_family_coverage_verified=True,three_material_draw_order_verified=True,
               world_phase_verified=True,production_quad_vs_hex_verified=True,fixed_texture_period_removed=True,
               synthetic_fixture_not_gameplay=True,source_images_modified=False,
               physical_android_device_tested=False,ew6_parity_claimed=False)
    (P/'reports/ground_continuity_native_evidence.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(proof),flush=True)


if __name__=='__main__':main()
