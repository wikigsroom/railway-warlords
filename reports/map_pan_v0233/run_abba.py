"""Four sequential fresh-process comparisons of the same source draw paths."""
from pathlib import Path
import subprocess,json,sys,statistics,hashlib
P=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(P/'tools'))
from build_release import source_digest
root=P/'reports/map_pan_v0233'
runtime=source_digest()[0];stages=[]
for name in ['perf_01_legacy','perf_02_optimized','perf_03_optimized','perf_04_legacy']:
 subprocess.run([sys.executable,str(root/'invoke_profile.py'),name],cwd=P,check=True)
 result=json.loads((root/name/'profile.json').read_text(encoding='utf-8'))
 identity=json.loads((root/name/'source_identity.json').read_text(encoding='utf-8'))
 assert identity['production_file_restored'] and result['state_unchanged'] and result['focused_frames']==180
 frames=sorted(result['frame_ms']);cpu=result['static_atlas_ms']
 stages.append(dict(name=name,legacy_methods=result['legacy_methods'],frames=180,focused_frames=result['focused_frames'],p95_ms=frames[int(len(frames)*.95)-1],max_ms=max(frames),mean_ms=statistics.mean(frames),static_draw_mean_ms=statistics.mean(cpu),static_draw_max_ms=max(cpu),synchronous_misses_during_pan=result['prefetch_after']['sync_misses']-result['prefetch_before']['sync_misses'],backdrop_rebuilds=result['backdrop_rebuilds'],report=(root/name/'profile.json').relative_to(P).as_posix()))
 print('ABBA_STAGE '+json.dumps(stages[-1]),flush=True)
assert source_digest()[0]==runtime
(root/'abba_summary.json').write_text(json.dumps(dict(passed=True,version='0.2.33',runtime_source_sha256=runtime,comparison='Fresh-process copied 0.2.32 static-atlas and fine-mesh methods versus current methods; same development engine and source state. Not a comparison between two shipping binaries.',gpu='NVIDIA RTX 3060',resolution=[1920,1080],vsync=False,fps_uncapped=True,other_application_gpu_cpu_load_controlled=False,physical_android_device_tested=False,stages=stages),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('ABBA_COMPARISON_COMPLETE',flush=True)
