"""Record completed scoped work without closing the broader game-quality goal."""
from datetime import datetime, timezone
from pathlib import Path
import json

P = Path(__file__).resolve().parents[2]
R = P / 'reports/map_pan_v0233'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main():
    exports = read(P / 'reports/export_results.json')
    runtime = exports[0]['runtime_source_sha256']
    assert len(exports) == 2 and all(row['export_verified'] and row['runtime_source_sha256'] == runtime for row in exports)
    components = read(R / 'final_components_02/runs.json')
    shipping = read(R / 'shipping_01/validation.json')
    maps = read(P / 'reports/screenshots/map_composition_native/v0233/verified_export_01/validation.json')
    docs = read(P / 'reports/repository_documentation_validation.json')
    visual = read(R / 'visual_review.json')
    pan = read(R / 'abba_summary.json')
    apk = read(P / 'reports/apk_content_validation.json')
    assert all(row['passed'] for row in [components, shipping, maps, docs, pan, apk])
    assert shipping['runtime_source_sha256'] == maps['runtime_source_sha256'] == docs['runtime_source_sha256'] == pan['runtime_source_sha256'] == runtime
    checks = sum(o['checks'] for row in components['runs'] for o in row['outputs'])
    assert checks == 625 and len(visual['actually_viewed_complete_images']) == 10
    record = dict(
        recorded_at_utc=datetime.now(timezone.utc).isoformat(), version='0.2.33', result='progress',
        goal_completed=False, whole_goal_achieved=False, formal_art_approval=False, ew6_parity_claimed=False,
        runtime_source_sha256=runtime, content_hash='d9932b5aa389f0a482bf3def34201b14209071584bb4e06dc5f2c255dd010ef6',
        previous_turn_result='progress', previous_pushed_commit='6aa0246451ab73be6a03c530ad0e36ab685f851b',
        previous_evidence_used='The previous checkpoint still had panning stalls. CPU-phase profiling identified synchronous whole-image reads and repeated province/control/rail/fine-mesh work, which determined the implementation below.',
        changes=[
            'Bounded prefetch of nearby whole original scenery textures, two active tasks and 128 wanted IDs; existing 384-texture cache limit retained.',
            'Conservative source-line visibility index, original rail-curve and sleeper geometry cache, and reusable fine-detail meshes for sixteen-cell chunks.',
            'Application exit consumes only its own bounded outstanding texture loads; no exit leak warning in final input regression.'
        ],
        current_targeted_checks=checks + shipping['gpu_checks'] + len(maps['checks']), component_groups=16,
        component_checks=checks, shipping_gpu_checks=shipping['gpu_checks'], shipping_map_layout_checks=len(maps['checks']),
        final_shipping_whole_images_actually_viewed=10, fixed_view_pixel_identical_pairs=3,
        new_independent_pngs=0, registered_pngs=2509, protected_rule_and_data_files_byte_unchanged=158,
        android=dict(exported=True, version_code=38, raster_payloads_verified=len(apk['raster_import_files_verified']),
                     abi=['arm64-v8a', 'armeabi-v7a'], physical_device_tested=False, adb_connected_devices=0),
        documentation=dict(passed=True, scope=docs['scope'], links_checked=docs['local_links_checked'], full_native_release_gates_checked=False),
        archive_directory=str(P.parents[1] / 'output/releases/railway-warlords-0.2.33'),
        delivery_manifest='reports/map_pan_preview_v0233.json', archive_status_recorded_separately=True,
        new_music_generated=False, future_music_route='music-gen-remote-YuE2', existing_local_music_provenance_preserved=True,
        performance=dict(mode='native_development_fresh_process_legacy_current_current_legacy', stages=pan['stages'],
                         shipping_binary_comparison=False, other_application_gpu_cpu_load_controlled=False,
                         abrupt_jump_stalls_eliminated=False, physical_android_performance_tested=False),
        full_thirty_group_regression_repeated=False, long_ai_matches_repeated=False,
        remaining_priorities=[
            'Sourced Wuhan framing/context, more varied mountain miniatures, alluvial ground and detailed waterways.',
            'Complete direction-specific movement, attack and hurt animation cycles for remaining unit families.',
            'Correct Asian historical starts and finish evidence-backed commander deployments and individual ability balance.',
            'Physical Motorola X30 acceptance and further first-load / cross-region panning profiling.'
        ])
    path = P / 'reports/quality_goal_turn_v0233.json'
    assert not path.exists()
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('QUALITY_GOAL_PROGRESS_RECORDED ' + str(record['current_targeted_checks']), flush=True)


if __name__ == '__main__':
    main()
