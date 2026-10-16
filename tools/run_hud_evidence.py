"""Native Windows viewports, including X30 dimensions; no Android emulator."""
import json, subprocess
from build_release import P, ENGINE, current_version, source_digest

def main():
    runs=[('1920x1080','1.0',[]),('2400x1080','1.2',['--mobile-ui-test']),('1280x720','1.5',[])]
    cases=[]
    for resolution,scale,extra in runs:
        name=resolution+'_'+str(round(float(scale)*100)).zfill(3)+('_mobile' if extra else '')
        log=P/'reports'/('hud_native_'+name+'.log')
        with log.open('w',encoding='utf-8') as out:
            result=subprocess.run([str(ENGINE),'--path',str(P),'--resolution',resolution,'--script','tests/hud_native_test.gd','--','--ui-scale',scale,*extra],cwd=P,stdout=out,stderr=subprocess.STDOUT,timeout=240)
        text=log.read_text(encoding='utf-8',errors='replace');report=P/'reports'/('hud_native_'+name+'.json')
        value=json.loads(report.read_text(encoding='utf-8')) if report.exists() else {}
        if result.returncode or not value.get('passed') or any(marker in text for marker in ['SCRIPT ERROR:','\nERROR:','WARNING: ObjectDB']):raise SystemExit('Native HUD verification failed: '+name+'; see '+str(log))
        if value['build_version']!=current_version():raise SystemExit('Wrong HUD binary version')
        cases.append(dict(name=name,report=report.relative_to(P).as_posix(),checks=len(value['checks']),viewport=value['viewport'],physical_android_device_tested=False));print(name+': passed',flush=True)
    (P/'reports/hud_native_tests.json').write_text(json.dumps(dict(passed=True,build_version=current_version(),runtime_source_sha256=source_digest()[0],cases=cases,checks=sum(row['checks'] for row in cases),manual_compositing=False,physical_android_device_tested=False),indent=2),encoding='utf-8')

if __name__=='__main__':main()
