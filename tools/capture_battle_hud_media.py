"""Capture whole shipping-EXE viewports, verifying the EXE bytes before/after."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
import subprocess
import time

from PIL import Image
from build_release import P, current_version


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'[a-z0-9_]+', args.attempt), 'Use a simple new attempt name.'
    folder = P / 'reports/battle_hud_shipping_v0230' / args.attempt
    folder.mkdir(parents=True, exist_ok=False)
    exe = P / 'build/windows/RailwayWarlords.exe'
    identity = sha(exe)
    row = next(r for r in read(P / 'reports/export_results.json') if r['target'] == 'windows')
    hud = read(P / 'reports/battle_hud_native_v0230/final_04/validation.json')
    assert row['export_verified'] and hud['passed'] and row['sha256'] == identity
    assert row['runtime_source_sha256'] == hud['runtime_source_sha256']
    driver = sha(P / 'tools/capture_battle_hud_media.py')
    captures = []
    jobs = [('wuhan_opening', ['--scenario', 'legion_07', '--capture']),
            ('home', ['--capture']),
            ('ui_smoke', ['--scenario', 'campaign_1924_02', '--ui-test'])]
    for name, flags in jobs:
        frame = folder / (name + '.png')
        log = folder / (name + '.log')
        command = [str(exe), '--resolution', '1920x1080', '--position', '0,0',
                   '--log-file', str(log), '--', '--qa-session', '--ui-scale', '1.0',
                   *flags, '--capture-path', str(frame)]
        started = time.time()
        with (folder / (name + '.stdout.log')).open('w', encoding='utf-8') as stream:
            result = subprocess.run(command, cwd=P, stdout=stream, stderr=subprocess.STDOUT, timeout=240)
        output = log.read_text(encoding='utf-8', errors='replace')
        assert result.returncode == 0 and 'SCRIPT ERROR:' not in output and '\nERROR:' not in output
        if name == 'ui_smoke':
            assert 'UI_SMOKE_PASS' in output, 'The actual exported UI smoke did not finish.'
        metadata = frame.with_suffix('.json')
        facts = read(metadata)
        assert facts['build_version'] == current_version() and facts['raw_godot_capture']
        assert facts['qa_save_isolated'] and not facts['physical_android_device_tested']
        assert frame.stat().st_mtime >= started - 2
        with Image.open(frame) as image:
            assert image.size == (1920, 1080)
        captures.append(dict(name=name, path=frame.relative_to(P).as_posix(), sha256=sha(frame),
            metadata=metadata.relative_to(P).as_posix(), metadata_sha256=sha(metadata), command=command))
        print(name + ': whole shipping viewport verified', flush=True)
    assert sha(exe) == identity and sha(P / 'tools/capture_battle_hud_media.py') == driver
    report = dict(passed=True, version=current_version(), runtime_source_sha256=row['runtime_source_sha256'],
        windows_exe_sha256=identity, capture_driver_sha256=driver, mode='verified_export_default_opening_and_ui_smoke',
        created_at_utc=datetime.now(timezone.utc).isoformat(), captures=captures,
        shipping_binary_unchanged=True, source_directory_hashing_performed=False,
        source_identity_reference='reports/export_results.json', ui_smoke_passed=True,
        raw_full_viewports=True, manual_image_compositing=False,
        physical_android_device_tested=False, formal_art_approval=False)
    (folder / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('SHIPPING_MEDIA_RESULT True', flush=True)


if __name__ == '__main__':
    main()
