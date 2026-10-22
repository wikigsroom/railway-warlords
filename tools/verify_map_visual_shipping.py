"""Check the exported program, preserving every whole viewport and attempt."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time

from build_release import P, current_version, source_digest


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    assert out.is_relative_to((P / 'reports').resolve()) and not out.exists()
    out.mkdir(parents=True)
    exe = P / 'build/windows/RailwayWarlords.exe'
    exported = next(row for row in read(P / 'reports/export_results.json') if row['target'] == 'windows')
    version, runtime, identity = current_version(), source_digest()[0], sha(exe)
    assert exported['export_verified'] and exported['sha256'] == identity and exported['runtime_source_sha256'] == runtime
    commands, captures = [], []
    cases = [
        ('gpu', ['--ground-continuity-test', '--ground-continuity-output', str(out / 'gpu')]),
        ('ui_smoke', ['--scenario', 'campaign_1924_02', '--ui-test', '--capture-path', str(out / 'ui_smoke.png')]),
        ('home', ['--capture', '--capture-path', str(out / 'home.png')]),
        ('mountains', ['--scenario', 'campaign_1924_03', '--focus-point', '16848,7000', '--capture-zoom', '1.05', '--capture', '--capture-path', str(out / 'mountains.png')]),
    ]
    for name, flags in cases:
        log = out / (name + '.log')
        command = [str(exe), '--resolution', '1920x1080', '--position', '0,0', '--log-file', str(log), '--', '--qa-session', *flags]
        started = time.time()
        with (out / (name + '.stdout.log')).open('w', encoding='utf-8') as stream:
            child = subprocess.Popen(command, cwd=P, stdout=stream, stderr=subprocess.STDOUT)
            try:
                code = child.wait(timeout=360)
            except subprocess.TimeoutExpired:
                child.kill(); child.wait(timeout=15)
                raise
        text = log.read_text(encoding='utf-8', errors='replace')
        assert code == 0 and not any(marker in text for marker in ['SCRIPT ERROR:', 'SHADER ERROR:', '\nERROR:'])
        commands.append(dict(name=name, command=command, exit_code=code, owned_native_pid=child.pid))
        if name == 'gpu':
            result = read(out / 'gpu/validation.json')
            assert result['passed'] and result['build_version'] == version and len(result['checks']) == 48 and len(result['samples']) == 26
            assert all(row['maximum_channel_delta'] <= 2 and row['pixels'] >= 500 for row in result['samples'] if 'family' in row)
        else:
            if name == 'ui_smoke': assert 'UI_SMOKE_PASS' in text
            path = out / (name + '.png'); metadata = path.with_suffix('.json'); data = read(metadata)
            assert path.stat().st_mtime >= started - 2 and data['build_version'] == version and data['qa_save_isolated'] and data['raw_godot_capture'] and not data['physical_android_device_tested']
            captures.append(dict(path=path.relative_to(P).as_posix(), sha256=sha(path), metadata=metadata.relative_to(P).as_posix(), metadata_sha256=sha(metadata)))
        print(name + ' verified', flush=True)
    assert sha(exe) == identity and source_digest()[0] == runtime
    report = dict(passed=True, version=version, mode='verified_shipping_exe', runtime_source_sha256=runtime,
                  windows_exe_sha256=identity, shipping_binary_unchanged=True, capture_driver_sha256=sha(__file__),
                  completed_at_utc=datetime.now(timezone.utc).isoformat(), commands=commands, captures=captures,
                  gpu_report=(out / 'gpu/validation.json').relative_to(P).as_posix(), gpu_report_sha256=sha(out / 'gpu/validation.json'),
                  gpu_checks=48, ui_smoke_passed=True, physical_android_device_tested=False, formal_art_approval=False,
                  ew6_parity_claimed=False, manual_image_compositing=False)
    (out / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('SHIPPING_MAP_VISUALS_VERIFIED', flush=True)


if __name__ == '__main__':
    main()
