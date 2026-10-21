"""Disclose the current exported static sample, including any failed FPS target."""
import json, shutil
from build_release import P,current_version,source_digest
from package_delivery import read,sha,require

def main():
    require(current_version() in {'0.2.28','0.2.29'},'Unexpected performance observation version')
    export=next(r for r in read(P/'reports/export_results.json') if r['target']=='windows')
    exe=P/'build/windows/RailwayWarlords.exe';runtime=source_digest()[0]
    require(export['export_verified'] and export['sha256']==sha(exe)
        and export['runtime_source_sha256']==runtime,'Current verified executable required')
    raw=read(P/'reports/desktop_benchmark.json')
    require(raw['sample_frames']==180,'Complete current static benchmark sample required')
    target=P/'reports/water_map_performance';target.mkdir(exist_ok=True)
    names=[('reports/desktop_benchmark.json','desktop_benchmark.json'),
        ('reports/benchmark_native.log','native.log'),('reports/benchmark_stdout.log','stdout.log'),
        ('reports/screenshots/map_desktop_benchmark.png','viewport.png'),
        ('reports/screenshots/map_desktop_benchmark.json','viewport.json')]
    files=[]
    for relative,name in names:
        source=P/relative;dest=target/name;shutil.copyfile(source,dest)
        files.append(dict(file=dest.relative_to(P).as_posix(),sha256=sha(dest)))
    require(read(target/'viewport.json')['build_version']==current_version(),'Stale benchmark capture')
    result=dict(observation_recorded=True,version=current_version(),runtime_source_sha256=runtime,
        windows_exe_sha256=sha(exe),sample_frames=180,average_fps=raw['average_fps'],
        frame_ms_p95=raw['frame_ms_p95'],target_fps=60,target_met=raw['average_fps']>=60,
        window_focus_or_occlusion_recorded=False,matched_old_build_baseline=False,
        physical_android_device_tested=False,files=files,
        limitation='One static RTX 3060 desktop sample from verify_exports. Not a controlled comparative benchmark, sustained battle test or physical phone measurement. Retained report paths serve current shared release gates; this is not a new water-art revision.')
    (P/'reports/water_map_performance_observation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result),flush=True)

if __name__=='__main__':main()
