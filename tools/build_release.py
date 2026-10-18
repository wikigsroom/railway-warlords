"""Native Windows exports. Keystore credentials stay outside source and logs."""
from pathlib import Path
import subprocess,os,json,secrets,hashlib,argparse,time,re
P=Path(__file__).resolve().parents[1];ROOT=P.parents[1]
ENGINE=ROOT/'.toolchain/godot/Godot_v4.7.2-stable_win64_console.exe'
JAVA=Path('C:/Program Files/Eclipse Adoptium/jdk-21.0.11.10-hotspot')
SDK=Path('C:/Users/carzy/AppData/Local/Android/Sdk')
PRIVATE=ROOT/'.toolchain/signing';CREDENTIALS=PRIVATE/'railway_warlords.json'
def current_version():
    source=(P/'content/content_registry.gd').read_text(encoding='utf-8')
    match=re.search(r'const APP_VERSION="(\d+\.\d+\.\d+)"',source)
    if not match:raise SystemExit('Runtime application version is missing.')
    return match.group(1)

def android_version_code():
    source=(P/'export_presets.cfg').read_text(encoding='utf-8')
    match=re.search(r'^version/code=(\d+)$',source,re.M)
    if not match:raise SystemExit('Android version code is missing.')
    return int(match.group(1))

def source_digest():
    # Full binary identity includes media/export configuration; automated rule and
    # layout freshness follows production code, content and schema, with media
    # checked natively. Opt-in CLI-only QA drivers remain in binary identity;
    # their waits/demo strategies do not change ordinary gameplay or rule tests.
    digest=hashlib.sha256()
    files=[P/'project.godot',P/'export_presets.cfg']
    test_sources=[P/'project.godot']
    for folder in ['app','content','domain','ai','presentation','persistence','audio']:
        scoped=[p for p in (P/folder).rglob('*') if p.is_file() and p.suffix in ['.gd','.tscn','.json']]
        files.extend(scoped);test_sources.extend(p for p in scoped if p not in [P/'app/responsiveness_qa.gd',P/'app/visual_playtest.gd'])
    schemas=list((P/'schemas').glob('*.json'));files.extend(schemas);test_sources.extend(schemas)
    files.extend(p for p in (P/'assets').rglob('*') if p.is_file() and p.suffix in ['.png','.wav','.ogg','.mp3','.otf','.ttf','.json','.txt','.tres','.gdshader','.import'])
    for path in sorted(files):
        digest.update(path.relative_to(P).as_posix().encode());digest.update(path.read_bytes())
    return digest.hexdigest(),max(path.stat().st_mtime for path in test_sources)

def rule_dependencies_digest():
    # Headless AI uses the command kernel, content, saves and its own test driver.
    # A renderer-only fix does not invalidate an unchanged completed AI match.
    files=[]
    for folder in ['domain','ai','content','persistence']:
        files.extend(p for p in (P/folder).rglob('*') if p.is_file() and p.suffix in ['.gd','.json'])
    # JSON schemas are Python-only contract documents. Include them if runtime
    # GDScript starts referring to that directory; otherwise resource_validation
    # checks them separately. Their bytes still enter the full binary digest.
    runtime_gd=[p for folder in ['domain','ai','content','persistence','app','presentation','audio'] for p in (P/folder).rglob('*.gd')]
    if any(re.search(r'schemas[/\\]',p.read_text(encoding='utf-8')) for p in runtime_gd):
        files.extend((P/'schemas').glob('*.json'))
    # The soak script calls AIPlanner/CommandKernel directly. Native worker
    # presentation preparation is checked by rules_worker_test and exported
    # response tests, not by this headless behavior simulation.
    files.extend([P/'tests/soak_test.gd',P/'project.godot'])
    digest=hashlib.sha256()
    for path in sorted(files):
        digest.update(path.relative_to(P).as_posix().encode());digest.update(path.read_bytes())
    return digest.hexdigest(),max(path.stat().st_mtime for path in files)
def run(args,log,env):
    with log.open('w',encoding='utf-8') as f:r=subprocess.run([str(x) for x in args],env=env,stdout=f,stderr=subprocess.STDOUT)
    return r.returncode
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--target',choices=['all','windows','android'],default='all');a=ap.parse_args()
    env=os.environ.copy();env['JAVA_HOME']=str(JAVA);env['ANDROID_HOME']=str(SDK);env['PATH']=str(JAVA/'bin')+os.pathsep+env['PATH']
    for n in ['windows','android']:(P/'build'/n).mkdir(parents=True,exist_ok=True)
    if not CREDENTIALS.exists():
        PRIVATE.mkdir(parents=True,exist_ok=True);keyfile=PRIVATE/'railway_warlords.keystore';password=secrets.token_urlsafe(32)
        env['RAILWAY_STORE_PASS']=password
        code=run([JAVA/'bin/keytool.exe','-genkeypair','-keystore',keyfile,'-storetype','PKCS12','-alias','railway_warlords','-storepass:env','RAILWAY_STORE_PASS','-keypass:env','RAILWAY_STORE_PASS','-keyalg','RSA','-keysize','3072','-validity','10000','-dname','CN=Railway Warlords, O=Railway Warlords, C=CN'],P/'reports/key_creation.log',env)
        if code:raise SystemExit('Keystore creation failed; inspect local diagnostic log.')
        CREDENTIALS.write_text(json.dumps(dict(path=str(keyfile),alias='railway_warlords',password=password),indent=2),encoding='utf-8')
    key=json.loads(CREDENTIALS.read_text(encoding='utf-8'))
    env['GODOT_ANDROID_KEYSTORE_RELEASE_PATH']=key['path'];env['GODOT_ANDROID_KEYSTORE_RELEASE_USER']=key['alias'];env['GODOT_ANDROID_KEYSTORE_RELEASE_PASSWORD']=key['password']
    targets=['windows','android'] if a.target=='all' else [a.target];results=[]
    for target in targets:
        filename='RailwayWarlords.exe' if target=='windows' else 'RailwayWarlords.apk';out=P/'build'/target/filename
        source_hash,_=source_digest();started=time.time();log=P/'reports'/f'export_{target}.log'
        code=run([ENGINE,'--headless','--path',P,'--export-release',target.title(),out],log,env)
        diagnostic=log.read_text(encoding='utf-8',errors='replace')
        errors=[line.strip() for line in diagnostic.splitlines() if re.search(r'(^|\s)(SCRIPT ERROR:|ERROR:|Parse Error:|Export failed)',line)]
        exists=out.exists();fresh=exists and out.stat().st_mtime>=started-2 and out.stat().st_size>1024*1024
        verified=code==0 and fresh and not errors and source_hash==source_digest()[0]
        results.append(dict(target=target,exit_code=code,path=str(out),exists=exists,fresh_artifact=fresh,log_errors=errors,export_verified=verified,runtime_source_sha256=source_hash,bytes=out.stat().st_size if exists else 0,sha256=hashlib.sha256(out.read_bytes()).hexdigest() if exists else None))
        print(f'{target}: exit={code}, fresh={fresh}, export_verified={verified}')
    # Publish complete identity evidence atomically. Windows file watchers can
    # hold the previous JSON open while the two lengthy exports are running.
    results_path=P/'reports/export_results.json'
    results_pending=results_path.with_suffix('.tmp')
    results_pending.write_text(json.dumps(results,indent=2),encoding='utf-8')
    results_pending.replace(results_path)
    raise SystemExit(0 if all(r['export_verified'] for r in results) else 1)
if __name__=='__main__':main()
