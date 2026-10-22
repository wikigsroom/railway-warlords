"""Run labelled native map-layer diagnosis; never edits source PNG artwork."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import time
import shutil

P = Path(__file__).resolve().parents[1]
ENGINE = P.parents[1] / '.toolchain/godot/Godot_v4.7.2-stable_win64.exe'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('attempt')
    parser.add_argument('--case', choices=['layers','control','rules','relief'], default='layers')
    args = parser.parse_args()
    out = P / 'reports/ground_layers_v0238' / args.attempt
    out.mkdir(parents=True, exist_ok=False)
    files = [P / 'project.godot']
    for folder in ['app', 'content', 'domain', 'ai', 'presentation', 'persistence', 'audio', 'tests']:
        files += [p for p in (P / folder).rglob('*') if p.is_file() and p.suffix in ['.gd', '.json', '.tscn', '.gdshader']]
    identity = {p.relative_to(P).as_posix(): sha(p) for p in sorted(files)}
    command = [str(ENGINE), '--path', str(P), '--log-file', str(out / 'native.log')]
    script = None
    if args.case in ['rules','relief']:
        script = 'tests/'+('control_land_clip_test' if args.case=='rules' else 'geographic_relief_test')+'.gd'
        command += ['--headless','--script','res://'+script,'--','--report-output',str(out/'validation.json')]
    elif args.case == 'control':
        command += ['--resolution','1920x1080','--position','0,0','--','--qa-session','--ui-scale','1.0',
                    '--control-land-test','--control-land-output',str(out)]
    else:
        script='tests/ground_layers_native_test.gd'
        command += ['--resolution','1920x1080','--position','0,0','--script','res://'+script,
                    '--','--qa-session','--ui-scale','1.0','--output',str(out)]
    proof = dict(command=command, controller_sha256=sha(Path(__file__)), engine_sha256=sha(ENGINE),
                 source_commit_at_start=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=P, text=True).strip(),
                 working_code_and_data_sha256=identity, shipping_exe=False,
                 labelled_ablation_not_art_acceptance=True, source_pngs_modified=False)
    (out / 'identity.json').write_text(json.dumps(proof, indent=2)+'\n', encoding='utf-8')
    shutil.copyfile(__file__,out/'controller.py.txt')
    if script:shutil.copyfile(P/script,out/'native_test.gd.txt')
    start = time.monotonic()
    with (out / 'stdout.log').open('w', encoding='utf-8') as stream:
        child = subprocess.Popen(command, cwd=P, stdout=stream, stderr=subprocess.STDOUT)
        print('OWNED_NATIVE_PID', child.pid, flush=True)
        try:
            code = child.wait(timeout=540)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=15)
            raise
    log = (out / 'native.log').read_text(encoding='utf-8', errors='replace')
    assert code == 0 and not any(m in log for m in ['SCRIPT ERROR:', 'SHADER ERROR:', '\nERROR:']), log[-2200:]
    assert all(sha(P / name) == expected for name, expected in identity.items()), 'Source changed during capture'
    report = json.loads((out / 'validation.json').read_bytes())
    assert report['passed']
    if args.case=='layers':
        assert len(report['captures']) == 8
        assert all(sha(out / c['file']) == c['sha256'] for c in report['captures'])
    result = dict(passed=True, native_exit_code=code, elapsed_seconds=round(time.monotonic()-start, 2),
                  completed_at_utc=datetime.now(timezone.utc).isoformat(), source_unchanged_during_run=True,
                  validation_sha256=sha(out / 'validation.json'), shipping_exe=False,
                  physical_android_device_tested=False, formal_art_approval=False)
    (out / 'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
