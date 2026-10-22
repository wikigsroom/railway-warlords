"""Measure ordinary native-game draw intervals, without replacing source files."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import statistics
import subprocess
import time

P = Path(__file__).resolve().parents[1]
ENGINE = P.parents[1] / '.toolchain/godot/Godot_v4.7.2-stable_win64.exe'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('layout', choices=['desktop', 'touch_dimensions'])
    parser.add_argument('--attempt', default='01')
    args = parser.parse_args()
    out = P / 'reports/river_cartography_v0236/revised' / ('perf_' + args.layout + args.attempt)
    out.mkdir(parents=True, exist_ok=False)
    command = [str(ENGINE), '--path', str(P), '--resolution', '1920x1080' if args.layout == 'desktop' else '2400x1080',
               '--position', '0,0', '--log-file', str(out / 'native.log'), '--script', 'res://tests/river_pan_native_test.gd',
               '--', '--qa-session', '--report-output', str(out / 'pan.json')]
    if args.layout == 'touch_dimensions':
        command += ['--mobile-ui-test', '--ui-scale', '1.2']
    files = [P / 'project.godot', P / 'tests/river_pan_native_test.gd']
    for folder in ['app', 'content', 'domain', 'ai', 'presentation', 'persistence', 'audio']:
        files += [path for path in (P / folder).rglob('*') if path.is_file() and path.suffix in ['.gd', '.tscn', '.json', '.gdshader']]
    identity = {path.relative_to(P).as_posix(): sha(path) for path in sorted(files)}
    proof = dict(command=command, engine_sha256=sha(ENGINE), controller_sha256=sha(__file__),
                 code_and_data_sha256=identity, production_source_overrides=False,
                 scope='Native Windows; touch dimensions are not a phone or emulator.')
    (out / 'command.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    started = time.monotonic()
    with (out / 'stdout.log').open('w', encoding='utf-8') as stream:
        child = subprocess.Popen(command, cwd=P, stdout=stream, stderr=subprocess.STDOUT)
        print('NATIVE_PAN_PID ' + str(child.pid), flush=True)
        try:
            code = child.wait(timeout=360)
        except subprocess.TimeoutExpired:
            child.kill(); child.wait(timeout=15)
            raise
    native_log = (out / 'native.log').read_text(encoding='utf-8', errors='replace')
    assert code == 0 and not any(marker in native_log for marker in ['SCRIPT ERROR:', 'SHADER ERROR:', '\nERROR:']), native_log[-1500:]
    report = json.loads((out / 'pan.json').read_bytes())
    assert report['passed'] and report['qa_save_isolated']
    assert all(sha(P / name) == value for name, value in identity.items())
    frames = sorted(report['frame_ms'])
    result = dict(passed=True, native_exit_code=code, native_process_id=child.pid,
                  completed_at_utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=round(time.monotonic() - started, 2),
                  dependencies_unchanged=True, frames=len(frames), mean_ms=statistics.mean(frames),
                  median_ms=statistics.median(frames), p95_ms=frames[int(.95 * (len(frames) - 1))], max_ms=max(frames),
                  focused_frames=report['focused_frames'], file=(out / 'pan.json').relative_to(P).as_posix(),
                  sha256=sha(out / 'pan.json'), physical_android_device_tested=False,
                  other_application_gpu_cpu_load_controlled=False, shipping_exe=False, formal_art_approval=False)
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
