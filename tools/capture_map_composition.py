"""Untouched native scene captures and independent screen-rectangle checks.

Development-engine evidence is explicitly separate from verified shipping EXE
evidence. No screenshot is resized, cropped, painted or assembled here.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from PIL import Image
from build_release import ENGINE, P, current_version, source_digest


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def intersects(a, b):
    return a[0] < b[0]+b[2]-.05 and b[0] < a[0]+a[2]-.05 and a[1] < b[1]+b[3]-.05 and b[1] < a[1]+a[3]-.05


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--development', action='store_true')
    parser.add_argument('--expected-content-hash')
    parser.add_argument('--evidence-root', help='New evidence directory, preserving earlier attempts.')
    args=parser.parse_args()
    version=current_version()
    driver_sha=sha(__file__)
    print('MAP_COMPOSITION_BEGIN '+version+'; hashing the current runtime and immutable media.',flush=True)
    runtime=source_digest()[0]
    exe=P/'build/windows/RailwayWarlords.exe'
    if not args.development:
        exports=json.loads((P/'reports/export_results.json').read_text(encoding='utf-8'))
        record=next(row for row in exports if row['target']=='windows')
        assert record['export_verified'] and record['runtime_source_sha256']==runtime and record['sha256']==sha(exe), 'A current verified export is required'
    mode='development_engine' if args.development else 'verified_export'
    folder=P/'reports/screenshots/map_composition_native'/('v'+version.replace('.',''))/mode
    if args.evidence_root:
        folder=Path(args.evidence_root)
        if not folder.is_absolute():folder=P/folder
        folder=folder.resolve()
        assert folder.is_relative_to((P/'reports').resolve()) and not folder.exists(), 'Use a new directory inside reports'
    folder.mkdir(parents=True,exist_ok=True)
    jobs=[
        ('wuhan','legion_07','1920x1080','1.0',['--focus-city','hankou','--capture-zoom','1.05'],{'hankou','hanyang','wuchang'}),
        ('beijing','campaign_1924_05','1920x1080','1.0',['--focus-city','beijing','--capture-zoom','.9'],{'beijing'}),
        ('coast','campaign_1924_03','1920x1080','1.0',['--focus-city','shanhaiguan','--capture-zoom','.88'],{'shanhaiguan'}),
        ('village','campaign_1924_03','1920x1080','1.0',['--focus-place','place_dongjiakou','--capture-zoom','1.15'],{'place_dongjiakou'}),
        ('wuhan_regional','legion_07','1920x1080','1.0',['--focus-city','hankou','--capture-zoom','.32'],{'hankou'}),
        ('wuhan_x30_layout','legion_07','2400x1080','1.2',['--focus-city','hankou','--capture-zoom','1.05','--mobile-ui-test'],{'hankou','hanyang','wuchang'}),
        ('wuhan_large_text','legion_07','1280x720','1.5',['--focus-city','hankou','--capture-zoom','1.05'],{'hankou','hanyang','wuchang'}),
    ]
    captures=[];failures=[];checks=[]
    def check(ok, name):
        checks.append(dict(name=name,passed=bool(ok)))
        if not ok:failures.append(name)
    for name,scenario,resolution,scale,flags,required in jobs:
        image=folder/(name+'.png');log=folder/(name+'.log')
        command=[str(ENGINE),'--path',str(P)] if args.development else [str(exe)]
        command+=['--resolution',resolution,'--position','0,0','--log-file',str(log),'--','--qa-session','--scenario',scenario,'--ui-scale',scale,*flags,'--capture','--capture-path',str(image)]
        started=datetime.now(timezone.utc).timestamp()
        with log.with_suffix('.stdout.log').open('w',encoding='utf-8') as stream:
            process=subprocess.run(command,cwd=P,stdout=stream,stderr=subprocess.STDOUT,timeout=240)
        diagnostic=log.read_text(encoding='utf-8',errors='replace')
        assert process.returncode==0 and 'SCRIPT ERROR:' not in diagnostic and '\nERROR:' not in diagnostic, 'Native scene failed: '+name
        metadata=image.with_suffix('.json')
        facts=json.loads(metadata.read_text(encoding='utf-8'))
        composition=facts['map_composition'];labels=composition['labels'];objects=composition['objects']
        check(image.stat().st_mtime>=started-2 and facts['raw_godot_capture'] and facts['build_version']==version,name+':current_raw_viewport')
        check(not facts['physical_android_device_tested'] and facts['qa_save_isolated'],name+':honest_isolated_desktop_scope')
        with Image.open(image) as frame:check(frame.size==tuple(map(int,resolution.split('x'))),name+':whole_viewport_dimensions')
        check(composition['operation_hex_radius_world']==48 and not composition['geographic_anchors_changed'],name+':operation_grid_and_node_anchors_preserved')
        check(required<={row['city_id'] for row in labels},name+':required_node_names_present')
        overlaps=[(a['city_id'],b['city_id']) for i,a in enumerate(labels) for b in labels[i+1:] if intersects(a['screen_rect'],b['screen_rect'])]
        occlusions=[(a['city_id'],b['id']) for a in labels for b in objects if intersects(a['screen_rect'],b['screen_rect'])]
        check(not overlaps,name+':captions_do_not_overlap_each_other')
        check(not occlusions,name+':captions_clear_models_units_and_crossings')
        if args.expected_content_hash:check(facts['content_hash']==args.expected_content_hash,name+':map_and_rule_catalogue_identity_preserved')
        captures.append(dict(name=name,scenario=scenario,image=str(image),sha256=sha(image),metadata=str(metadata),metadata_sha256=sha(metadata),labels=len(labels),objects=len(objects),caption_overlaps=overlaps,caption_object_occlusions=occlusions))
        print(json.dumps(dict(case=name,labels=len(labels),objects=len(objects),overlaps=len(overlaps),occlusions=len(occlusions)),ensure_ascii=True),flush=True)
    check(source_digest()[0]==runtime,'runtime_source_unchanged_during_capture_set')
    check(sha(__file__)==driver_sha,'capture_driver_unchanged_during_capture_set')
    report=dict(passed=not failures,version=version,mode=mode,runtime_source_sha256=runtime,capture_driver_sha256=driver_sha,expected_content_hash=args.expected_content_hash,created_at_utc=datetime.now(timezone.utc).isoformat(),checks=checks,failures=failures,captures=captures,physical_android_device_tested=False,formal_art_approval=False,ew6_parity_claimed=False,source_pngs_modified=False,manual_image_compositing=False)
    report_path=folder/'validation.json'
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=report['passed'],checks=len(checks),report=str(report_path),failures=failures),ensure_ascii=True),flush=True)
    return int(bool(failures))


if __name__=='__main__':raise SystemExit(main())
