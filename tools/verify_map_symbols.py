"""Verify source-entity visibility and semantic zoom in the current native EXE."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from PIL import Image
from build_release import P, current_version, source_digest
from package_delivery import read, require, sha


def main():
    runtime = source_digest()[0]
    version = current_version()
    exe = P / 'build/windows/RailwayWarlords.exe'
    exported = next(row for row in read(P / 'reports/export_results.json') if row['target'] == 'windows')
    require(exported['export_verified'] and exported['runtime_source_sha256'] == runtime
            and exported['sha256'] == sha(exe), 'Current verified Windows export required')
    groups = []
    for profile, resolution, scale in [('windows', '1920x1080', '1.0'), ('x30_layout', '2400x1080', '1.2')]:
        folder = P / 'reports/screenshots/map_symbols_native' / profile
        folder.mkdir(parents=True, exist_ok=True)
        log = P / 'reports' / ('map_symbols_' + profile + '.log')
        command = [str(exe), '--resolution', resolution, '--position', '0,0', '--',
                   '--qa-session', '--ui-scale', scale, '--map-symbol-test', '--map-symbol-output', str(folder)]
        if profile == 'x30_layout':
            command.append('--mobile-ui-test')
        started = datetime.now(timezone.utc).timestamp()
        with log.open('w', encoding='utf-8') as out:
            result = subprocess.run(command, cwd=P, stdout=out, stderr=subprocess.STDOUT, timeout=600)
        diagnostic = log.read_text(encoding='utf-8', errors='replace')
        require(result.returncode == 0 and not any(x in diagnostic for x in ('SCRIPT ERROR:', '\nERROR:', 'WARNING: ObjectDB')),
                'Native map-symbol checks failed: ' + profile + '; inspect ' + log.name)
        path = folder / 'validation.json'
        report = read(path)
        require(report['passed'] and report['build_version'] == version and len(report['checks']) == 110
                and len(report['captures']) == 16 and not report['physical_android_device_tested'],
                'Complete current map-symbol evidence required')
        names = [row['name'] for row in report['checks'] if row['passed']]
        require(sum(name.startswith('reverse_small_zoom_crossing_restores_compact_symbols:') for name in names) == 4
                and sum(name.startswith('compact_counter_click_beats_nearby_city_snap:') for name in names) == 6
                and sum(name.startswith('ordinary_map_click_selects_and_promotes_formation:') for name in names) == 2,
                'Reverse cache crossings, adjacent-city selection and detailed promotion must actually pass')
        captures = []
        for row in report['captures']:
            image = Path(row['path']); metadata = Path(row['metadata'])
            meta = read(metadata)
            require(image.stat().st_mtime >= started-2 and meta['build_version'] == version
                    and meta['raw_godot_capture'] and meta['qa_save_isolated'], 'Current raw native frame required')
            require(meta['map_symbols'] == row['facts'], 'Symbol capture metadata changed')
            facts = row['facts']
            identities = facts['unit_counter_ids'] + facts['unit_detail_ids']
            require(identities and len(identities) == len(set(identities))
                    and not facts['source_units_removed'] and not facts['rule_positions_changed']
                    and not facts['units_aggregated'], 'Formation identities must remain individual and unique')
            with Image.open(image) as frame:
                require(frame.size == tuple(map(int, resolution.split('x'))), 'Wrong native frame dimensions')
            captures.append(dict(file=image.relative_to(P).as_posix(), sha256=sha(image),
                                 metadata=metadata.relative_to(P).as_posix(), metadata_sha256=sha(metadata)))
        groups.append(dict(profile=profile, resolution=resolution, ui_scale=scale,
                           checks=len(report['checks']), report=path.relative_to(P).as_posix(),
                           report_sha256=sha(path), log=log.relative_to(P).as_posix(),
                           log_sha256=sha(log), captures=captures))
        print(json.dumps(dict(profile=profile, passed=True, checks=len(report['checks']), captures=len(captures))), flush=True)
    require(source_digest()[0] == runtime and sha(exe) == exported['sha256'], 'Source or EXE changed during proof')
    proof = dict(passed=True, version=version, runtime_source_sha256=runtime,
                 windows_exe_sha256=exported['sha256'], groups=groups,
                 checks=sum(group['checks'] for group in groups), native_captures=32,
                 visible_formation_identity_verified=True, compact_counter_selection_verified=True,
                 small_zoom_cache_crossings_verified=True, raw_godot_captures=True,
                 manual_image_compositing=False, source_images_modified=False,
                 physical_android_device_tested=False, formal_art_approval=False, ew6_parity_claimed=False)
    (P / 'reports/map_symbol_native_evidence.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(passed=True, checks=proof['checks'], native_captures=32)), flush=True)


if __name__ == '__main__':
    main()
