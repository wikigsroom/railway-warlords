"""Compare untouched native captures numerically; never save edited or combined images."""
from pathlib import Path
import json
from PIL import Image
from build_release import current_version, source_digest
from package_delivery import sha

P=Path(__file__).resolve().parents[1]

def main():
    native=json.loads((P/'reports/unit_layer_native.json').read_text(encoding='utf-8'))
    runtime,modified=source_digest()
    if not native['passed'] or native['version']!=current_version():raise SystemExit('Current native layer comparisons are required.')
    cases=[]
    for row in native['cases']:
        paths=[P/row[k].removeprefix('res://') for k in ('cached','direct')]
        if not all(path.stat().st_mtime>=modified for path in paths):raise SystemExit('Native captures predate the current runtime.')
        with Image.open(paths[0]) as a,Image.open(paths[1]) as b:
            if a.size!=b.size:raise SystemExit('Native viewport dimensions differ.')
            left=a.convert('RGB').tobytes();right=b.convert('RGB').tobytes()
        total=0;maximum=0;over_three=0
        for a,b in zip(left,right):
            delta=abs(a-b);total+=delta;maximum=max(maximum,delta);over_three+=delta>3
        mean=total/len(left);ratio=over_three/len(left)
        cases.append({'name':row['name'],'mean_channel_difference_0_255':mean,
            'maximum_channel_difference':maximum,'channels_over_three_ratio':ratio,
            'native_images_sha256':[sha(path) for path in paths],
            'unit_order_preserved':row['unit_order_preserved'],'state_and_rng_unchanged':row['state_and_rng_unchanged'],
            'passed':mean<=.01 and maximum<=12 and ratio<=.00001 and row['unit_order_preserved'] and row['state_and_rng_unchanged']})
    report={'passed':len(cases)==4 and all(row['passed'] for row in cases),
        'version':current_version(),'runtime_source_sha256':runtime,'cases':cases,
        'measurement':'Identical paused native whole viewports, direct and cached. Small RGBA8 rounding/antialias differences allowed; no image crops, edits or composite files.'}
    (P/'reports/unit_layer_pixel_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'passed':report['passed'],'pairs':len(cases),'maximum_mean_difference':max(row['mean_channel_difference_0_255'] for row in cases)}))
    raise SystemExit(0 if report['passed'] else 1)

if __name__=='__main__':main()
