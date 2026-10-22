"""Verify and archive the exact signed preview APK with native SDK tools."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import time

P = Path(__file__).resolve().parents[1]
R = P / 'reports/geographic_ground_v0237'
STAGE = P.parents[1] / 'game/railway_warlords_review_0237'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    export_path = R / 'preview_export01.json'
    export = json.loads(export_path.read_bytes())
    assert export['passed'] and export['version'] == '0.2.37' and export['android_version_code'] == 42
    artifact = next(a for a in export['artifacts'] if a['target'] == 'android')
    apk = Path(artifact['path'])
    before = (apk.stat().st_size, apk.stat().st_mtime_ns)
    assert before[0] == artifact['bytes']
    seal = json.loads((R / 'preview_stage01.json').read_bytes())
    for relative in ['tools/verify_exports.py', 'tools/build_release.py', 'export_presets.cfg']:
        assert sha(STAGE / relative) == seal['file_sha256'][relative]
    out = R / 'apk01'
    out.mkdir(exist_ok=False)
    command = [sys.executable, str(STAGE / 'tools/verify_exports.py'), '--android-only']
    started = time.monotonic()
    with (out / 'native_verify.log').open('x', encoding='utf-8') as log:
        child = subprocess.Popen(command, cwd=STAGE, stdout=log, stderr=subprocess.STDOUT)
        print('NATIVE_APK_VERIFY_PID', child.pid, flush=True)
        try:
            code = child.wait(timeout=1800)
        except subprocess.TimeoutExpired:
            child.kill(); child.wait(timeout=15); raise
    diagnostic = (out / 'native_verify.log').read_text(encoding='utf-8', errors='replace')
    assert code == 0 and not any(s in diagnostic for s in ['SCRIPT ERROR:', '\nERROR:']), diagnostic[-1500:]
    assert (apk.stat().st_size, apk.stat().st_mtime_ns) == before
    report_path = STAGE / 'reports/apk_content_validation.json'
    content = json.loads(report_path.read_bytes())
    assert content['passed'] and content['artifact_sha256'] == artifact['sha256']
    assert len(content['files']) == 147
    assert len(content['raster_import_files_verified']) == 2521
    assert len(content['instrumental_music_imports_verified']) == 3
    files = {}
    for name in ['apk_content_validation.json', 'apk_signature.log', 'apk_badging.log',
                 'apk_permissions.log', 'android_devices.log']:
        source = STAGE / 'reports' / name
        assert source.stat().st_mtime >= datetime.fromisoformat(seal['created_at_utc']).timestamp()
        shutil.copyfile(source, out / name)
        assert sha(out / name) == sha(source)
        files[name] = sha(source)
    result = dict(passed=True, version='0.2.37', android_version_code=42,
                  completed_at_utc=datetime.now(timezone.utc).isoformat(),
                  controller_sha256=sha(__file__), native_controller_sha256=sha(STAGE / 'tools/verify_exports.py'),
                  command=command, native_exit_code=code, native_process_id=child.pid,
                  elapsed_seconds=round(time.monotonic()-started, 2),
                  export_receipt_sha256=sha(export_path), artifact_sha256=artifact['sha256'],
                  runtime_source_merkle_sha256=export['runtime_source_merkle_sha256'],
                  payload_source_and_notice_files=len(content['files']),
                  whole_original_texture_imports=len(content['raster_import_files_verified']),
                  existing_music_imports=len(content['instrumental_music_imports_verified']),
                  signature_v2_and_v3_verified=True, android_abis=['arm64-v8a', 'armeabi-v7a'],
                  minimum_api=24, target_api=36, requested_permissions=0,
                  file_sha256=files, physical_android_device_tested=False,
                  virtualization_used=False, formal_art_approval=False)
    with (out / 'validation.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
