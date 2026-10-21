"""Time unchanged renderer methods through a QA-only MapView subclass."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

P=Path(__file__).resolve().parents[2]
folder=P/'reports/map_pan_v0233'/sys.argv[1]
assert folder.is_dir() and not (folder/'source_identity.json').exists()
main=P/'app/main.gd'; original=main.read_bytes()
old=b'map_view=MapView.new();'
new=('map_view=load("res://'+(folder/'profiled_map_view.gd').relative_to(P).as_posix()+'").new();').encode()
assert original.count(old)==1
record=dict(base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=P,text=True).strip(),
    base_main_sha256=hashlib.sha256(original).hexdigest(),
    base_map_view_sha256=hashlib.sha256((P/'presentation/map_view.gd').read_bytes()).hexdigest(),
    temporary_change='Temporary factory only; renderer modes and overrides are declared in the QA script. All production bytes are restored after the run.',
    production_file_restored=False,timed_out=False)
engine=P.parents[1]/'.toolchain/godot/Godot_v4.7.2-stable_win64_console.exe'
renderer=P/'presentation/map_view.gd';renderer_original=renderer.read_bytes()
(folder/'source_identity.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
try:
    if (folder/'renderer_patch.json').exists():
        patched=renderer_original
        for before,after in json.loads((folder/'renderer_patch.json').read_text(encoding='utf-8')):
            # Preserve mixed source line endings by matching each original span.
            a=before.encode();b=after.encode()
            if patched.count(a)!=1:
                a=a.replace(b'\n',b'\r\n');b=b.replace(b'\n',b'\r\n')
            assert patched.count(a)==1,before
            patched=patched.replace(a,b)
        renderer.write_bytes(patched)
        record['instrumented_map_view_sha256']=hashlib.sha256(patched).hexdigest()
    temporary=original.replace(old,new)
    if (folder/'profiled_asset_library.gd').exists():
        assert temporary.count(b'assets=AssetLibrary.new()')==1
        factory=('assets=load(\"res://'+(folder/'profiled_asset_library.gd').relative_to(P).as_posix()+'\").new()').encode()
        temporary=temporary.replace(b'assets=AssetLibrary.new()',factory)
    main.write_bytes(temporary)
    with (folder/'stdout.log').open('w',encoding='utf-8') as output:
        child=subprocess.Popen([str(engine),'--path',str(P),'--resolution','1920x1080',
            '--position','0,0','--script','res://'+(folder/'run.gd').relative_to(P).as_posix(),
            '--log-file',str(folder/'native.log'),'--','--qa-session'],stdout=output,stderr=subprocess.STDOUT)
        try:record['native_exit_code']=child.wait(timeout=240)
        except subprocess.TimeoutExpired:
            record['timed_out']=True
            subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],stdout=output,stderr=subprocess.STDOUT)
            raise
finally:
    main.write_bytes(original);renderer.write_bytes(renderer_original)
    record['production_file_restored']=main.read_bytes()==original and renderer.read_bytes()==renderer_original
    (folder/'source_identity.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
text=(folder/'native.log').read_text(encoding='utf-8',errors='replace');print(text[-6000:])
assert record['native_exit_code']==0 and 'SCRIPT ERROR:' not in text and '\nERROR:' not in text
