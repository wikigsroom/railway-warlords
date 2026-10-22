"""Archive the explicitly viewed whole frames and completed development scope."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json

P = Path(__file__).resolve().parents[1]
R = P / 'reports/river_cartography_v0236'
CASES = {
    'mountains03': 'Rounded tributary bends and muted center lines; gridded source pattern, repeated mountains and uniform lowland remain conspicuous.',
    'village01': 'Whole sourced village view checked; softer streams remain schematic and large ground areas have similar texture.',
    'coast01': 'Fine streams use the revised profile. Stepped coast, broad polygon color boundaries and repeated units remain visible.',
    'yangtze02': 'Wide main-river gradients and water texture remain continuous. Port/ferry labels persist; repeated ports and empty ground remain unfinished.'
}


def read(path):
    return json.loads(Path(path).read_bytes())


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_new(path, data):
    with Path(path).open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def review():
    records = []
    for case, observation in CASES.items():
        folder = R / 'revised' / case
        result = read(folder / 'result.json')
        metadata = read(folder / 'viewport.json')
        command = read(folder / 'command.json')
        assert result['passed'] and result['native_exit_code'] == 0 and result['dependencies_unchanged']
        assert sha(folder / 'viewport.png') == result['sha256']
        assert sha(folder / 'viewport.json') == result['metadata_sha256']
        assert metadata['raw_godot_capture'] and metadata['qa_save_isolated']
        assert not metadata['physical_android_device_tested']
        assert all(sha(P / name) == checksum for name, checksum in command['code_and_data_sha256'].items())
        records.append(dict(case=case, file=result['file'], sha256=result['sha256'],
                            metadata_sha256=result['metadata_sha256'], whole_viewport_opened=True,
                            source_identity_current=True, observation=observation))
    report = dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(), controller_sha256=sha(__file__),
                  review_method='All four complete native PNG viewports individually opened using view_image; observations are manual, not inferred from test counts.',
                  whole_final_frames_viewed=4, raster_postprocessing=False, development_only=True,
                  shipping_exe=False, physical_android_device_tested=False, formal_art_approval=False,
                  ew6_quality_goal_complete=False, records=records)
    write_new(R / 'visual_review01.json', report)
    print('WHOLE_NATIVE_VIEWS_RECORDED 4', flush=True)


def summary():
    paths = ['geometry_audit03.json', 'contact_graph01.json', 'protected_scope01.json',
             'repository_documentation01.json', 'visual_review01.json',
             'revised/geometry03/result.json', 'revised/river_rules01/result.json',
             'revised/surface_rules01/result.json', 'revised/material_rules01/result.json',
             'revised/perf_desktop01/result.json', 'revised/perf_touch_dimensions01/result.json']
    records = []
    for name in paths:
        path = R / name
        result = read(path)
        assert result.get('passed', name == 'visual_review01.json')
        records.append(dict(file=path.relative_to(P).as_posix(), sha256=sha(path)))
    geometry = read(R / 'geometry_audit03.json')
    graph = read(R / 'contact_graph01.json')
    scope = read(R / 'protected_scope01.json')
    report = dict(passed=True, recorded_at_utc=datetime.now(timezone.utc).isoformat(),
                  controller_sha256=sha(__file__), development_only=True,
                  runtime_version_constant='0.2.35', evidence_iteration='v0236',
                  current_shipping_packages='Unchanged 0.2.35 / Android code40; this development source is not in them.',
                  native_content_hash=geometry['native_content_hash'], actual_reaches=geometry['actual_reaches_checked'],
                  revised_display_reaches=geometry['actual_display_reaches_changed'],
                  maximum_sampled_symmetric_distance_m=geometry['maximum_sampled_symmetric_hausdorff_m'],
                  preserved_hydrorivers_contacts=sum(row.get('source_contact_pairs', 0) for row in graph['maps']),
                  protected_unchanged_files=scope['protected_unchanged_files'], unchanged_png_files=scope['unchanged_png_files'],
                  native_geometry_checks=12, existing_river_geography_material_checks=126,
                  independent_contact_graph_checks=len(graph['checks']),
                  independent_repeated_per_reach_checks=len(geometry['checks']),
                  full_30_group_regression_rerun=False, shipping_binary_rebuilt=False,
                  physical_android_device_tested=False, formal_art_approval=False,
                  ew6_quality_goal_complete=False, new_raster_assets=False, new_music=False,
                  future_music_route='music-gen-remote-YuE2 / native Windows to remote RTX 3080; instrumental.',
                  remaining=['Stepped coasts', 'Repeated ground and mountain originals in the full scene',
                             'Source-grid straight river segments', 'Panning frame-time spikes',
                             'Complete unit action families', 'Known historical starting-state issues',
                             'Physical Motorola X30 acceptance'], evidence=records)
    write_new(R / 'development_summary01.json', report)
    print(json.dumps({key: report[key] for key in ['passed', 'actual_reaches', 'revised_display_reaches',
                                                 'preserved_hydrorivers_contacts', 'shipping_binary_rebuilt']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('kind', choices=['review', 'summary'])
    args = parser.parse_args()
    review() if args.kind == 'review' else summary()
