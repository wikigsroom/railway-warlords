"""Verify the current native Windows EXE actually decodes/transitions scores."""
import json
import subprocess
from build_release import P,current_version,source_digest
from package_delivery import read,sha,require

def main():
    version=current_version();runtime=source_digest()[0];exe=P/'build/windows/RailwayWarlords.exe'
    export=next(row for row in read(P/'reports/export_results.json') if row['target']=='windows')
    require(export['export_verified'] and export['sha256']==sha(exe) and export['runtime_source_sha256']==runtime,'Current Windows EXE required')
    log=P/'reports/music_native.log';target=P/'reports/music_native_tests.json'
    with log.open('w',encoding='utf-8') as stream:
        result=subprocess.run([str(exe),'--resolution','1280x720','--position','-4000,-3000','--','--qa-session','--music-test','--music-output',str(target)],cwd=P,stdout=stream,stderr=subprocess.STDOUT,timeout=120)
    text=log.read_text(encoding='utf-8',errors='replace')
    require(result.returncode==0 and 'SCRIPT ERROR:' not in text and '\nERROR:' not in text,'Native music playback failed; inspect music_native.log')
    report=read(target)
    require(report['passed'] and report['build_version']==version and len(report['checks'])==18,'Complete current native music report required')
    require(runtime==source_digest()[0] and sha(exe)==export['sha256'],'Music native identity changed')
    report.update(runtime_source_sha256=runtime,windows_exe_sha256=sha(exe),log_sha256=sha(log),native_export_tested=True)
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=True,checks=len(report['checks']),tracks=3)))

if __name__=='__main__':main()
