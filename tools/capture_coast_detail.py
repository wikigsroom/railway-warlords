"""Capture all four changed marine maps from the frozen Windows executable."""
from datetime import datetime, timezone
from pathlib import Path
import json
import subprocess
from PIL import Image
from build_release import P, current_version, source_digest
from package_delivery import read, require, sha


def main():
    version = current_version()
    runtime = source_digest()[0]
    exe = P / 'build/windows/RailwayWarlords.exe'
    export = next(r for r in read(P / 'reports/export_results.json') if r['target'] == 'windows')
    require(version in ['0.2.26', '0.2.27'] and export['export_verified']
            and export['sha256'] == sha(exe) and export['runtime_source_sha256'] == runtime,
            'Current frozen Windows export required')
    proof_path = P / 'reports/coast_detail_native_capture_evidence.json'
    driver = sha(Path(__file__))
    if proof_path.exists():
        previous = read(proof_path)
        if (previous.get('passed') and previous.get('runtime_source_sha256') == runtime
                and previous.get('windows_exe_sha256') == export['sha256']
                and previous.get('capture_driver_sha256') == driver
                and {r['map_id'] for r in previous.get('captures', [])} ==
                    {'jingjin', 'jingfeng', 'conquest_china', 'asia_strategic'}
                and all(sha(P / row[field]) == row[field + '_sha256'] for row in previous['captures']
                        for field in ['metadata', 'log'])
                and all(sha(P / row['file']) == row['sha256']
                        and sha(P / ('content/maps/' + row['map_id'] + '.json')) == row['map_sha256']
                        for row in previous['captures'])):
            print('Current frozen-build four-map viewport evidence retained.', flush=True)
            return
    cases = [('jingjin', 'campaign_1920_01', 'tianjin', '0.65'),
             ('jingfeng', 'campaign_1924_03', 'shanhaiguan', '0.88'),
             ('conquest_china', 'conq_1924', 'qingdao', '0.75'),
             ('asia_strategic', 'asia_1927', 'osaka', '1.2')]
    captures = []
    for map_id, scenario, city, zoom in cases:
        source_map = read(P / ('content/maps/' + map_id + '.json'))
        city_record = next(c for c in source_map['cities'] if c['id'] == city)
        center = city_record['render_position']
        focus = min((point for line in source_map['render_coast'] for point in line),
                    key=lambda p: (p[0] - center[0]) ** 2 + (p[1] - center[1]) ** 2)
        folder = P / 'reports/screenshots/coast_detail_native'
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / (map_id + '.png')
        log = P / 'reports' / ('coast_detail_capture_' + map_id + '.log')
        started = datetime.now(timezone.utc).timestamp()
        args = [str(exe), '--resolution', '1920x1080', '--position', '-4000,-3000', '--',
                '--qa-session', '--scenario', scenario, '--focus-point', ','.join(map(str, focus)),
                '--capture-zoom', zoom, '--capture', '--capture-path', str(target)]
        with log.open('w', encoding='utf-8') as stream:
            result = subprocess.run(args, cwd=P, stdout=stream, stderr=subprocess.STDOUT, timeout=300)
        diagnostic = log.read_text(encoding='utf-8', errors='replace')
        meta = read(target.with_suffix('.json'))
        require(result.returncode == 0 and 'SCRIPT ERROR:' not in diagnostic and '\nERROR:' not in diagnostic,
                'Native map capture failed: ' + map_id)
        require(meta['build_version'] == version and meta['raw_godot_capture'] and meta['qa_save_isolated']
                and meta['scenario_id'] == scenario and target.stat().st_mtime >= started - 2,
                'Fresh complete native capture required: ' + map_id)
        hydro = meta['map_bank_visible']['hydrography']
        marine = hydro['marine_geometry']
        require(marine['active'] and marine['pretriangulated'] and hydro['actual_coast_band_draws'] == 1,
                'Actual precompiled coast and batched shoreline draw required: ' + map_id)
        scenario_map = read(P / ('content/scenarios/' + scenario + '.json'))['map_id']
        require(scenario_map == map_id, 'Scenario map identity differs')
        with Image.open(target) as image:
            require(image.size == (1920, 1080), 'Complete native viewport required')
        captures.append(dict(map_id=map_id, scenario_id=scenario, reference_city=city, focus_point=focus,
            focus_point_source='nearest_registered_coast_vertex_to_city_render_position',
            map_sha256=sha(P / ('content/maps/' + map_id + '.json')),
            file=target.relative_to(P).as_posix(), sha256=sha(target),
            metadata=target.with_suffix('.json').relative_to(P).as_posix(),
            metadata_sha256=sha(target.with_suffix('.json')), log=log.relative_to(P).as_posix(),
            log_sha256=sha(log), actual_coast_band_draws=hydro['actual_coast_band_draws']))
        print(json.dumps(dict(passed=True, map_id=map_id)), flush=True)
    require(source_digest()[0] == runtime and sha(exe) == export['sha256'], 'Frozen source or binary changed')
    proof = dict(passed=True, version=version, runtime_source_sha256=runtime,
        windows_exe_sha256=export['sha256'], capture_driver_sha256=driver, captures=captures, raw_godot_captures=True,
        physical_android_device_tested=False, formal_art_approval=False,
        historical_coast_survey_approval=False)
    (P / 'reports/coast_detail_native_capture_evidence.json').write_text(
        json.dumps(proof, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
