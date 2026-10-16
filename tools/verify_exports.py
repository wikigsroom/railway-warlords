"""Verify shipped files with native Windows/Godot and Android SDK tools, without emulation."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import zipfile
from PIL import Image
from build_release import current_version, android_version_code

P = Path(__file__).resolve().parents[1]
SDK = Path('C:/Users/carzy/AppData/Local/Android/Sdk')
JAVA = Path('C:/Program Files/Eclipse Adoptium/jdk-21.0.11.10-hotspot')


def run(args, logfile, env=None):
    with logfile.open('w', encoding='utf-8') as log:
        result = subprocess.run([str(a) for a in args], cwd=P, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=90)
    text = logfile.read_text(encoding='utf-8', errors='replace')
    if result.returncode or 'SCRIPT ERROR:' in text or '\nERROR:' in text:
        raise SystemExit('Verification failed: ' + logfile.name)
    return text


def main():
    exe = P / 'build/windows/RailwayWarlords.exe'
    png = P / 'reports/screenshots/map_final_windows.png'
    native_log = P / 'reports/exported_windows_native.log'
    run([exe, '--resolution', '1920x1080', '--log-file', native_log, '--', '--qa-session', '--scenario', 'campaign_1924_02', '--ui-scale', '1.0', '--ui-test', '--capture-path', png], P / 'reports/exported_windows_stdout.log')
    if 'UI_SMOKE_PASS' not in native_log.read_text(encoding='utf-8'):
        raise SystemExit('Exported Windows UI smoke did not complete.')
    benchmark_png = P / 'reports/screenshots/map_desktop_benchmark.png'
    run([exe, '--resolution', '1920x1080', '--log-file', P / 'reports/benchmark_native.log', '--', '--qa-session', '--scenario', 'campaign_1924_02', '--ui-scale', '1.0', '--benchmark', '--benchmark-path', P / 'reports/desktop_benchmark.json', '--capture-path', benchmark_png], P / 'reports/benchmark_stdout.log')
    for path in (png, benchmark_png):
        with Image.open(path) as im:
            if im.size != (1920, 1080):
                raise SystemExit('Unexpected native viewport dimensions.')
    captures = [
        ('map_x30_layout', '2400x1080', ['--scenario', 'campaign_1924_02', '--ui-scale', '1.2', '--mobile-ui-test', '--capture']),
        ('map_large_text', '1920x1080', ['--scenario', 'campaign_1924_02', '--ui-scale', '1.5', '--capture']),
        ('map_historical_atlas', '1920x1080', ['--scenario', 'conq_1922', '--ui-scale', '1.0', '--atlas-view', '--inspect-city', 'qingdao', '--capture']),
        ('asia_1840_overview', '1920x1080', ['--scenario', 'asia_1840', '--ui-scale', '1.0', '--atlas-view', '--capture']),
        ('map_bohai_coast', '1920x1080', ['--scenario', 'campaign_1924_03', '--ui-scale', '1.0', '--focus-city', 'shanhaiguan', '--capture']),
        ('map_jingfeng_overview', '1920x1080', ['--scenario', 'campaign_1924_03', '--ui-scale', '1.0', '--atlas-view', '--capture']),
        ('settlements_country', '1920x1080', ['--scenario', 'conq_1924', '--ui-scale', '1.0', '--atlas-view', '--capture']),
        ('settlement_village_details', '1920x1080', ['--scenario', 'campaign_1924_03', '--ui-scale', '1.0', '--focus-city', 'shanhaiguan', '--inspect-place', 'place_beiyingzi', '--capture']),
        ('settlement_county_details', '1920x1080', ['--scenario', 'campaign_1924_03', '--ui-scale', '1.0', '--focus-place', 'place_lulong', '--inspect-place', 'place_lulong', '--capture']),
        ('settlement_market_details', '1920x1080', ['--scenario', 'campaign_1924_03', '--ui-scale', '1.0', '--focus-place', 'tangshan', '--inspect-place', 'tangshan', '--capture']),
        ('settlement_capital_details', '1920x1080', ['--scenario', 'conq_1924', '--ui-scale', '1.0', '--focus-place', 'place_kaifeng', '--inspect-place', 'place_kaifeng', '--capture']),
        ('settlement_village_x30', '2400x1080', ['--scenario', 'campaign_1924_03', '--ui-scale', '1.2', '--mobile-ui-test', '--focus-city', 'shanhaiguan', '--inspect-place', 'place_beiyingzi', '--capture']),
        ('legion_deployment_windows', '1920x1080', ['--ui-scale', '1.0', '--progression-ui-test']),
        ('legion_deployment_x30', '2400x1080', ['--ui-scale', '1.2', '--mobile-ui-test', '--progression-ui-test']),
    ]
    for name, resolution, arguments in captures:
        capture = P / 'reports/screenshots' / (name + '.png')
        log = P / 'reports' / (name + '_native.log')
        run([exe, '--resolution', resolution, '--log-file', log, '--', '--qa-session', *arguments, '--capture-path', capture], P / 'reports' / (name + '_stdout.log'))
        if '--progression-ui-test' in arguments and 'PROGRESSION_UI_PASS' not in log.read_text(encoding='utf-8'):
            raise SystemExit('Current exported progression controls did not complete: ' + name)
        with Image.open(capture) as im:
            if im.size != tuple(map(int, resolution.split('x'))):
                raise SystemExit('Native layout capture dimensions mismatch: ' + name)
    env = os.environ.copy()
    env['JAVA_HOME'] = str(JAVA)
    apk = P / 'build/android/RailwayWarlords.apk'
    signed = run([SDK / 'build-tools/36.0.0/apksigner.bat', 'verify', '--verbose', '--print-certs', apk], P / 'reports/apk_signature.log', env)
    if 'Verified using v2 scheme (APK Signature Scheme v2): true' not in signed or 'Verified using v3 scheme (APK Signature Scheme v3): true' not in signed:
        raise SystemExit('Current APK signature is invalid.')
    # AAPT's Windows archive reader needs an ASCII relative path, even with a Unicode working directory.
    badging = run([SDK / 'build-tools/36.0.0/aapt.exe', 'dump', 'badging', apk.relative_to(P)], P / 'reports/apk_badging.log')
    if not all(value in badging for value in ("name='org.railwaywarlords.game'", f"versionCode='{android_version_code()}'", f"versionName='{current_version()}'", "sdkVersion:'24'", "targetSdkVersion:'36'")):
        raise SystemExit('APK version/package/SDK metadata mismatch.')
    permissions = run([SDK / 'build-tools/36.0.0/aapt.exe', 'dump', 'permissions', apk.relative_to(P)], P / 'reports/apk_permissions.log')
    if 'uses-permission:' in permissions:
        raise SystemExit('Unexpected requested Android permission.')
    rows = []
    with zipfile.ZipFile(apk) as archive:
        names = archive.namelist()
        files = [p for folder in ('content/definitions', 'content/maps', 'content/scenarios') for p in (P / folder).glob('*.json')]
        files.append(P / 'content/geography_sources.json')
        files.extend(sorted((P/'presentation/data').glob('*.json')))
        files.extend(sorted((P/'assets/legal').glob('*.txt')))
        for path in files:
            relative = path.relative_to(P).as_posix()
            name = 'assets/' + relative
            rows.append({'file': relative, 'included': name in names, 'sha_matches': name in names and hashlib.sha256(archive.read(name)).digest() == hashlib.sha256(path.read_bytes()).digest()})
        asset_manifest=P/'assets/manifest.json'
        if archive.read('assets/assets/manifest.json')!=asset_manifest.read_bytes():raise SystemExit('APK raster provenance manifest does not match current source.')
        raster_rows=[]
        for item in json.loads(asset_manifest.read_text(encoding='utf-8'))['assets']:
            path=P/item['engine_path'].removeprefix('res://')
            imported=path.with_name(path.name+'.import').read_text(encoding='utf-8')
            remaps=re.findall(r'^path(?:\.[A-Za-z0-9_]+)?="res://([^"\n]+)"',imported,re.MULTILINE)
            embedded=[name for name in remaps if 'assets/'+name in names]
            matched=bool(embedded) and all(hashlib.sha256(archive.read('assets/'+name)).digest()==hashlib.sha256((P/name).read_bytes()).digest() for name in embedded)
            raster_rows.append({'id':item['id'],'source_sha256':item['source_sha256'],'embedded_imports':embedded,'current_import_bytes_match':matched})
        if not all(item['current_import_bytes_match'] for item in raster_rows):raise SystemExit('APK imported raster textures do not match current verified engine imports.')
        private = [n for n in names if any(w in n.lower() for w in ('keystore', 'railway_warlords.json', 'sub2_image_gen.py'))]
        abis = sorted({n.split('/')[1] for n in names if n.startswith('lib/') and n.endswith('.so')})
        if abis != ['arm64-v8a', 'armeabi-v7a']:
            raise SystemExit('Unexpected Android architectures.')
        report = {'passed': all(row['sha_matches'] for row in rows), 'files': rows, 'native_libraries': [n for n in names if n.startswith('lib/')], 'private_files_detected': private, 'artifact_sha256': hashlib.sha256(apk.read_bytes()).hexdigest()}
        report.update({'raster_manifest_byte_verified':True,'raster_import_files_verified':raster_rows})
    (P / 'reports/apk_content_validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if not report['passed'] or private:
        raise SystemExit('APK payload mismatch.')
    run([SDK / 'platform-tools/adb.exe', 'devices', '-l'], P / 'reports/android_devices.log')
    print(f'Exported Windows UI/rendering verified; APK signature, ABI, permissions and {len(rows)} source/notice files verified.')


if __name__ == '__main__':
    main()
