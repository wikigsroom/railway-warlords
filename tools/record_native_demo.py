"""Record Godot MovieWriter output, without montage or synthetic gameplay.

The runtime's older fixed report paths are protected byte for byte. Failed takes
remain outside the repository, and older public recordings are never replaced.
"""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from build_release import ENGINE, P, ROOT, current_version, source_digest


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def prepare_driver(folder):
    """Reuse the canonical legal-command demonstration with a shared map snapshot.

    This is an explicitly separate source-engine QA driver. It changes snapshot
    allocation and output paths, never the campaign, commands or presentation.
    """
    original=P/'app/visual_playtest.gd'
    source=original.read_text(encoding='utf-8')
    source=source.split('static func run_support(',1)[0]
    assert source.startswith('class_name VisualPlaytest\n')
    source=source.removeprefix('class_name VisualPlaytest\n')
    evidence=folder/'evidence'
    evidence.mkdir()
    changes={
        'var original=app.match_controller.state.duplicate(true)':
            'var original=StateAccess.clone_transaction(app.match_controller.state)',
        'var directory="res://reports/screenshots/visual_playtest"':
            'var directory='+json.dumps(evidence.as_posix(),ensure_ascii=False),
        'FileAccess.open("res://reports/visual_playtest.json",FileAccess.WRITE)':
            'FileAccess.open('+json.dumps((evidence/'visual_playtest.json').as_posix(),ensure_ascii=False)+',FileAccess.WRITE)',
    }
    for old,new in changes.items():
        assert source.count(old)==1, 'Canonical demonstration changed: '+old
        source=source.replace(old,new)
    generated=P/'reports'/('native_movie_driver_v'+current_version().replace('.',''))/folder.name
    generated.mkdir(parents=True,exist_ok=False)
    driver=generated/'visual_playtest.gd'
    driver.write_text(source,encoding='utf-8')
    relative='res://'+driver.relative_to(P).as_posix()
    wrapper=generated/'run.gd'
    wrapper.write_text('extends SceneTree\n'
        +'const Driver=preload('+json.dumps(relative)+')\n'
        +'func _initialize() -> void:\n\tstart.call_deferred()\n'
        +'func start() -> void:\n'
        +'\tvar app=load("res://app/main.tscn").instantiate()\n'
        +'\troot.add_child(app)\n\tawait process_frame\n\tawait Driver.run(app)\n',encoding='utf-8')
    for path in [driver,wrapper]:
        shutil.copyfile(path,folder/path.name)
    return wrapper,dict(canonical_driver='app/visual_playtest.gd',canonical_driver_sha256=sha(original),
        actual_driver_sha256=sha(driver),wrapper_sha256=sha(wrapper),
        changes=['Use the production transaction clone for the initial replay snapshot.',
            'Use an isolated output directory and no global class name.',
            'Run only the existing legal-command campaign demo, without its separate support demo.'],
        commands_changed=False,published_campaign_modified=False,presentation_modified=False,
        shipping_movie_acceptance_claimed=False)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--attempt',type=int,default=1)
    parser.add_argument('--development',action='store_true',
        help='Use the native editor engine with the exact export source; never claim shipping-video acceptance.')
    args=parser.parse_args()
    assert args.attempt>0
    assert args.development, 'The shipping template forbids this runtime res:// output route. Select --development explicitly.'
    version=current_version()
    progress=ROOT/'output/map_composition_validation_progress.json'
    validation=json.loads(progress.read_text(encoding='utf-8'))
    assert validation['version']==version and validation['terminal'] and validation['passed'], \
        'Finish retained native validation first; MovieWriter must not overlap its native scenes.'
    folder=ROOT/'output'/('native_movie_v'+version.replace('.',''))/('attempt_'+str(args.attempt).zfill(2))
    folder.mkdir(parents=True, exist_ok=False)
    exe=P/'build/windows/RailwayWarlords.exe'
    expected=next(r for r in json.loads((P/'reports/export_results.json').read_text(encoding='utf-8')) if r['target']=='windows')
    assert expected['export_verified'] and sha(exe)==expected['sha256'], 'Verified shipping EXE required'
    if args.development:
        print('NATIVE_MOVIE_HASHING_EXACT_EXPORT_SOURCE',flush=True)
        assert source_digest()[0]==expected['runtime_source_sha256'], 'Current source differs from the verified export'
    names=['01_command_preview.png','02_marching.png','03_dice_rolling.png','04_impact.png','05_battle_complete.png']
    roots=[folder, exe.parent, P]
    protected={}
    for root in roots[1:]:
        for path in [root/'reports/visual_playtest.json',*[root/'reports/screenshots/visual_playtest'/n for n in names]]:
            protected[path]=path.read_bytes() if path.is_file() else None
    for root in roots:
        (root/'reports/screenshots/visual_playtest').mkdir(parents=True,exist_ok=True)
    raw=folder/'recording.avi'
    log=folder/'movie.log'
    wrapper,driver_facts=prepare_driver(folder)
    command=[str(ENGINE),'--path',str(P),'--script',str(wrapper)]
    command+=['--resolution','1440x810','--position','0,0',
        '--log-file',str(log),'--write-movie',str(raw),'--fixed-fps','30','--','--qa-session']
    started=datetime.now(timezone.utc)
    receipt=dict(version=version, started_at_utc=started.isoformat(), runtime_source_sha256=expected['runtime_source_sha256'],
        executable_sha256=sha(ENGINE) if args.development else expected['sha256'],command=command,
        native_movie_writer=True, shipping_executable=not args.development,
        mode='native_development_engine_exact_export_source' if args.development else 'verified_shipping_executable',
        driver=driver_facts,
        physical_android_device_tested=False, full_frame=True, overlays=False, manual_image_compositing=False,
        synthetic_frames=False, playback_speed=1.0, passed=False)
    write(folder/'recording_identity.json',receipt)
    print('NATIVE_MOVIE_BEGIN '+str(folder),flush=True)
    try:
        with (folder/'stdout.log').open('w',encoding='utf-8') as stream:
            process=subprocess.run(command,cwd=folder,stdout=stream,stderr=subprocess.STDOUT,timeout=900)
        assert process.returncode==0, 'Native movie process failed'
        diagnostic=log.read_text(encoding='utf-8',errors='replace')
        assert 'SCRIPT ERROR:' not in diagnostic and '\nERROR:' not in diagnostic, 'Native diagnostics failed'
        reports=[folder/'evidence/visual_playtest.json',*[root/'reports/visual_playtest.json' for root in roots]]
        reports=[p for p in reports if p.is_file() and p.stat().st_mtime>=started.timestamp()-2]
        assert len(reports)==1, 'Exactly one fresh native report required'
        report_path=reports[0]
        report=json.loads(report_path.read_text(encoding='utf-8'))
        assert report['passed'] and report['build_version']==version and report['published_scenario_unchanged']
        assert report['unmodified_campaign_deployment'] and report['replay_same_final_state']
        assert report['artillery_visible'] and report['muzzle_visible'] and report['impact_visible']
        assert report['qa_save_isolated'] and not report['physical_android_device_tested']
        assert report['dice_rolls']*2==report['final_combat_random']['draws']-report['initial_combat_random']['draws']
        destination=folder/'evidence'
        destination.mkdir(exist_ok=True)
        if report_path.resolve()!=(destination/'visual_playtest.json').resolve():
            shutil.copyfile(report_path,destination/'visual_playtest.json')
        captures=[]
        for name in names:
            source=report_path.parent/name
            assert source.is_file() and source.stat().st_mtime>=started.timestamp()-2, 'Fresh native frame missing: '+name
            if source.resolve()!=(destination/name).resolve():
                shutil.copyfile(source,destination/name)
            captures.append(dict(file=name,sha256=sha(source),whole_native_viewport=True))
        assert sha(exe)==expected['sha256'], 'Shipping EXE changed during recording'
        if args.development:
            assert source_digest()[0]==expected['runtime_source_sha256'], 'Frozen source changed during recording'
        assert raw.is_file() and raw.stat().st_size>1000000
        mp4=folder/'gameplay.mp4'
        encode=['ffmpeg','-n','-i',str(raw),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p',
            '-c:a','aac','-b:a','128k','-movflags','+faststart',str(mp4)]
        with (folder/'encode.log').open('w',encoding='utf-8') as stream:
            subprocess.run(encode,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=600)
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(mp4)],text=True,encoding='utf-8'))
        video=next(row for row in probe['streams'] if row['codec_type']=='video')
        assert (video['width'],video['height'])==(1440,810) and video['avg_frame_rate']=='30/1'
        receipt.update(passed=True,ended_at_utc=datetime.now(timezone.utc).isoformat(),
            native_report_sha256=sha(destination/'visual_playtest.json'),captures=captures,
            raw_avi=dict(file=str(raw),sha256=sha(raw),bytes=raw.stat().st_size),
            mp4=dict(file=str(mp4),sha256=sha(mp4),bytes=mp4.stat().st_size),
            encode_command=encode,probe=probe)
        write(folder/'recording_identity.json',receipt)
        print('NATIVE_MOVIE_PASSED '+str(mp4),flush=True)
    except Exception as error:
        receipt.update(passed=False,failure=type(error).__name__+': '+str(error))
        raise
    finally:
        for path,previous in protected.items():
            if previous is None:
                if path.is_file():
                    path.unlink()
            elif not path.is_file() or path.read_bytes()!=previous:
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(previous)
        restored=all((not p.exists()) if b is None else p.is_file() and p.read_bytes()==b for p,b in protected.items())
        receipt['older_public_movie_evidence_preserved']=restored
        write(folder/'recording_identity.json',receipt)
        assert restored, 'Older movie evidence changed'


if __name__=='__main__':
    main()
