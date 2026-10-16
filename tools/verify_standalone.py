"""Launch the exact portable archive from a folder with no Godot project/runtime."""
import json
import struct
import subprocess
import zipfile
from pathlib import Path
from package_delivery import OUT, P, sha


def main():
    manifest = json.loads((OUT/'release_manifest.json').read_text(encoding='utf-8'))
    item = next(f for f in manifest['files'] if f['kind'] == 'windows_portable')
    archive_path = OUT/item['name']
    if sha(archive_path) != item['sha256']:
        raise SystemExit('Portable archive no longer matches its release manifest.')
    folder = OUT/'Windows便携版'
    folder.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        for name in archive.namelist():
            if not (folder/name).resolve().is_relative_to(folder.resolve()):
                raise SystemExit('Archive member escapes portable folder.')
        archive.extractall(folder)
    exe = folder/'RailwayWarlords.exe'
    native_log = OUT/'独立运行原生日志.log'
    stdout_log = OUT/'独立运行标准输出.log'
    capture = OUT/'独立运行原生截图.png'
    with stdout_log.open('w', encoding='utf-8') as stream:
        result = subprocess.run([str(exe), '--resolution', '1920x1080',
            '--log-file', str(native_log), '--', '--qa-session', '--scenario',
            'campaign_1924_02', '--ui-test', '--capture-path', str(capture)],
            cwd=folder, stdout=stream, stderr=subprocess.STDOUT, timeout=90)
    text = native_log.read_text(encoding='utf-8', errors='replace')
    meta = json.loads(capture.with_suffix('.json').read_text(encoding='utf-8'))
    header = capture.read_bytes()[:24]
    dimensions = struct.unpack('>II', header[16:24])
    checks = {
        'exit_zero': result.returncode == 0,
        'ui_smoke_completed': 'UI_SMOKE_PASS' in text,
        'native_log_clean': not any(x in text for x in ('SCRIPT ERROR:', '\nERROR:', 'WARNING: ObjectDB')),
        'embedded_executable_matches_export': sha(exe) == sha(P/'build/windows/RailwayWarlords.exe'),
        'working_folder_has_no_project_or_pck': not any(folder.rglob('project.godot')) and not any(folder.rglob('*.pck')),
        'native_capture_1920x1080': header.startswith(b'\x89PNG\r\n\x1a\n') and dimensions == (1920, 1080),
        'current_version_and_content': meta['build_version'] == manifest['version'] and meta['content_hash'] == manifest['content_hash'],
        'qa_saves_isolated': meta['qa_save_isolated'],
        'raw_godot_capture': meta['raw_godot_capture'],
        'historical_place_data_embedded':meta['historical_places']['additional_markers']==32 and meta['historical_places']['presentation_data_sha256']==manifest['historical_places']['presentation_data_sha256'],
    }
    report = {'passed': all(checks.values()), 'version': manifest['version'],
        'checks': checks, 'archive_sha256': sha(archive_path),
        'executable_sha256': sha(exe), 'capture_sha256': sha(capture),
        'native_log_sha256': sha(native_log), 'physical_android_device_tested': False,
        'scope': 'Exact packaged Windows EXE; real UI controls; independent working directory; embedded resources.'}
    (OUT/'独立运行复核.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'checks': len(checks), 'version': manifest['version']}, ensure_ascii=False))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
