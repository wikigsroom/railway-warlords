"""Direct captures of the exported EXE; never edit or assemble the PNGs."""
import json
import subprocess
from build_release import P, current_version


def main():
    tag='v'+current_version().replace('.','')
    jobs=[
        ('asia_forest_refined_'+tag,'1920x1080',['--scenario','asia_1927','--focus-point','4896,1912','--capture-zoom','0.72']),
        ('asia_forest_x30_'+tag,'2400x1080',['--scenario','asia_1927','--focus-point','4896,1912','--capture-zoom','0.72','--ui-scale','1.2','--mobile-ui-test']),
        ('terrain_mountain_'+tag,'1920x1080',['--scenario','campaign_1924_03','--focus-point','16848,7000','--capture-zoom','1.05']),
    ]
    for name,resolution,arguments in jobs:
        png=P/'reports/screenshots'/(name+'.png')
        with (P/'reports'/(name+'_exported.log')).open('w',encoding='utf-8') as log:
            result=subprocess.run([str(P/'build/windows/RailwayWarlords.exe'),'--resolution',resolution,
                '--','--qa-session',*arguments,'--capture','--capture-path',str(png)],
                cwd=P,stdout=log,stderr=subprocess.STDOUT,timeout=90)
        meta=json.loads(png.with_suffix('.json').read_text(encoding='utf-8'))
        if result.returncode or meta['build_version']!=current_version() or not meta['raw_godot_capture']:
            raise SystemExit('Native capture failed: '+name)
        print(name+': passed',flush=True)


if __name__=='__main__':main()
