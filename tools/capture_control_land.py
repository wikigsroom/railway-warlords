"""Verify real sea pixels and shared minimap geometry in the current release EXE."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from PIL import Image
from build_release import P, current_version, source_digest
from package_delivery import read, sha, require


def main():
    version = current_version()
    runtime = source_digest()[0]
    exe = P / 'build/windows/RailwayWarlords.exe'
    exported = next(row for row in read(P / 'reports/export_results.json') if row['target'] == 'windows')
    require(exported['export_verified'] and exported['sha256'] == sha(exe)
            and exported['runtime_source_sha256'] == runtime, 'Current verified Windows export required')
    groups = []
    for profile, resolution, scale in [('windows', '1920x1080', '1.0'), ('x30_layout', '2400x1080', '1.2')]:
        folder = P / 'reports/screenshots/control_land_native' / profile
        folder.mkdir(parents=True, exist_ok=True)
        log = P / 'reports' / ('control_land_' + profile + '.log')
        started = datetime.now(timezone.utc).timestamp()
        command = [str(exe), '--resolution', resolution, '--position', '-4000,-3000', '--', '--qa-session',
                   '--ui-scale', scale, '--control-land-test', '--control-land-output', str(folder)]
        if profile == 'x30_layout':
            command.append('--mobile-ui-test')
        with log.open('w', encoding='utf-8') as stream:
            result = subprocess.run(command, cwd=P, stdout=stream, stderr=subprocess.STDOUT, timeout=480)
        diagnostic = log.read_text(encoding='utf-8', errors='replace')
        require(result.returncode == 0 and 'SCRIPT ERROR:' not in diagnostic and '\nERROR:' not in diagnostic,
                'Native coast check failed: ' + profile + '; inspect ' + log.name)
        report_path = folder / 'validation.json'
        report = read(report_path)
        require(report['passed'] and report['build_version'] == version and report['normal_shipping_renderer']
                and report['qa_save_isolated'] and len(report['cases']) == 5 and len(report['captures']) == 10,
                'Complete normal-renderer coast evidence required')
        require(report['clip_data_sha256'] == sha(P / 'presentation/data/control_land_clip.json'), 'Stale native clip data')
        require(all(row['water_max_channel_delta'] <= 2 and row['minimap_water_max_channel_delta'] <= 2
                    and row['water_pixels'] >= 9 and row['minimap_water_pixels'] >= 12 for row in report['cases']),
                'Real water pixel proof failed')
        captures = []
        for row in report['captures']:
            path = Path(row['path']); metadata = Path(row['metadata'])
            meta = read(metadata)
            require(path.stat().st_mtime >= started - 2 and meta['build_version'] == version
                    and meta['raw_godot_capture'] and meta['control_land_clip']['land_clipped'], 'Stale native coast frame')
            with Image.open(path) as im:
                require(im.size == tuple(map(int, resolution.split('x'))), 'Wrong native coast resolution')
            captures.append(dict(file=path.relative_to(P).as_posix(), sha256=sha(path),
                                 metadata=metadata.relative_to(P).as_posix(), metadata_sha256=sha(metadata)))
        groups.append(dict(profile=profile, resolution=resolution, ui_scale=scale, checks=len(report['checks']),
                           report=report_path.relative_to(P).as_posix(), report_sha256=sha(report_path),
                           log=log.relative_to(P).as_posix(), cases=report['cases'], captures=captures))
        print(json.dumps(dict(profile=profile, passed=True, checks=len(report['checks']), captures=len(captures))), flush=True)
    require(source_digest()[0] == runtime and sha(exe) == exported['sha256'], 'Native source or EXE changed')
    proof = dict(passed=True, version=version, runtime_source_sha256=runtime, windows_exe_sha256=exported['sha256'],
                 clip_data_sha256=sha(P / 'presentation/data/control_land_clip.json'), groups=groups,
                 raw_godot_captures=True, manual_image_compositing=False, physical_android_device_tested=False, ew6_parity_claimed=False)
    (P / 'reports/control_land_native_evidence.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
