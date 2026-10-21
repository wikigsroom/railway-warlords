"""Index verified shipping captures without editing native images or metadata."""
from datetime import datetime, timezone
from pathlib import Path

from build_release import P, current_version, source_digest
from package_delivery import read, require, sha
from package_ui_refinement import write


def main():
    version = current_version()
    runtime = source_digest()[0]
    exe = P / 'build/windows/RailwayWarlords.exe'
    export = next(r for r in read(P / 'reports/export_results.json') if r['target'] == 'windows')
    require(export['export_verified'] and export['runtime_source_sha256'] == runtime
            and export['sha256'] == sha(exe), 'Current shipping binary required')
    folder = P / 'reports/screenshots/map_composition_native' / ('v' + version.replace('.', '')) / 'verified_export'
    path = folder / 'validation.json'
    proof = read(path)
    require(proof['passed'] and proof['mode'] == 'verified_export' and proof['version'] == version
            and proof['runtime_source_sha256'] == runtime
            and proof['capture_driver_sha256'] == sha(P / 'tools/capture_map_composition.py')
            and len(proof['checks']) == 58 and len(proof['captures']) == 7, 'Complete current exported composition run required')
    rows = []
    for row in proof['captures']:
        image = Path(row['image'])
        metadata = Path(row['metadata'])
        require(image.parent == folder and metadata == image.with_suffix('.json')
                and sha(image) == row['sha256'] and sha(metadata) == row['metadata_sha256'],
                'Raw viewport identity differs')
        require(not row['caption_overlaps'] and not row['caption_object_occlusions'], 'Caption collision')
        rows.append(dict(file=image.relative_to(P).as_posix(), sha256=row['sha256'],
            metadata=metadata.relative_to(P).as_posix(), metadata_sha256=row['metadata_sha256'], case=row['name']))
    result = dict(passed=True, version=version, runtime_source_sha256=runtime,
        windows_exe_sha256=sha(exe), created_at_utc=datetime.now(timezone.utc).isoformat(),
        capture_driver_sha256=proof['capture_driver_sha256'],
        groups=[dict(kind='map_composition', report=path.relative_to(P).as_posix(),
            report_sha256=sha(path), checks=len(proof['checks']), passed=True, captures=rows)],
        physical_android_device_tested=False, formal_art_approval=False, ew6_parity_claimed=False,
        source_pngs_modified=False, manual_compositing=False)
    write(P / 'reports/map_composition_native_evidence.json', result)
    print('Current shipping composition evidence sealed: 7 whole viewports, 58 checks.', flush=True)


if __name__ == '__main__':
    main()
