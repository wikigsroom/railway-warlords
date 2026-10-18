"""Bind four native source-coast/city numerical fixtures to the current EXE."""
import json
import subprocess
from PIL import Image
from build_release import P,current_version,source_digest
from package_delivery import read,sha,require

def main():
    version=current_version();runtime=source_digest()[0];exe=P/'build/windows/RailwayWarlords.exe'
    exported=next(row for row in read(P/'reports/export_results.json') if row['target']=='windows')
    require(exported['export_verified'] and exported['sha256']==sha(exe) and exported['runtime_source_sha256']==runtime,'Current Windows export required')
    folder=P/'reports/ground_coverage_native';folder.mkdir(exist_ok=True)
    log=P/'reports/ground_coverage_native.log'
    with log.open('w',encoding='utf-8') as stream:
        result=subprocess.run([str(exe),'--resolution','1280x720','--position','-4000,-3000','--','--qa-session','--ground-coverage-test','--ground-coverage-output',str(folder)],cwd=P,stdout=stream,stderr=subprocess.STDOUT,timeout=240)
    diagnostic=log.read_text(encoding='utf-8',errors='replace')
    require(result.returncode==0 and 'SCRIPT ERROR:' not in diagnostic and '\nERROR:' not in diagnostic,'Source ground native test failed; inspect log')
    report=read(folder/'validation.json')
    require(report['passed'] and report['build_version']==version and len(report['cases'])==4,'Four current source fixtures required')
    files=[folder/'validation.json',log]
    for case in report['cases']:
        image=folder/(case['map']+'.png')
        with Image.open(image) as opened:require(opened.size==(384,384),'Native fixture dimensions differ')
        files.append(image)
    require(source_digest()[0]==runtime and sha(exe)==exported['sha256'],'Ground native identity changed')
    proof=dict(passed=True,version=version,runtime_source_sha256=runtime,windows_exe_sha256=sha(exe),checks=len(report['checks']),cases=report['cases'],files=[dict(file=path.relative_to(P).as_posix(),sha256=sha(path)) for path in files],physical_android_device_tested=False,numerical_fixtures_not_gameplay_screenshots=True,formal_art_approval=False,ew6_parity_claimed=False)
    (P/'reports/ground_coverage_native_evidence.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=True,checks=len(report['checks']),fixtures=4)))

if __name__=='__main__':main()
