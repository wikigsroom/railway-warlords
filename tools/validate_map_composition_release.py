"""Additional composition checks; the common validator retains every prior gate."""
from build_release import P, current_version
from package_delivery import read, require, sha


def validate_map_composition(runtime):
    require(current_version() == '0.2.29', 'Unexpected composition release')
    batch = read(P / 'reports/regression_hash_batch_equivalence.json')
    sealed = read(P / 'reports/regression_dependency_evidence.json')
    require(batch['passed'] and batch['game_version'] == current_version()
        and batch['module_sha256'] == sha(P / 'tools/regression_dependencies.py')
        and len(batch['checks']) == 6 and all(row['passed'] for row in batch['checks'])
        and not batch['persistent_hash_cache'] and not batch['metadata_used_instead_of_bytes']
        and batch['actual_dependency_identities'] == {
            row['check']: row['dependency_sha256_at_seal'] for row in sealed['checks']},
        'Batch hashes require current legacy-algorithm equivalence and unchanged dependency bytes')
    audit = read(P / 'reports/map_composition_scope_audit.json')
    require(audit['passed'] and audit['version'] == current_version()
        and audit['runtime_source_sha256'] == runtime and audit['preserved_raster_originals'] == 2507
        and audit['new_raster_originals'] == 0 and audit['map_geography_preserved'] and audit['rules_preserved']
        and audit['media_and_prompts_preserved'], 'Complete retained-content audit required')
    native = read(P / 'reports/map_composition_native_evidence.json')
    require(native['capture_driver_sha256'] == sha(P / 'tools/capture_map_composition.py'), 'Capture driver differs')
    group = native['groups'][0]
    proof = read(P / group['report'])
    require(proof['mode'] == 'verified_export' and proof['expected_content_hash'] == audit['content_hash']
        and len(proof['checks']) == 58 and all(r['passed'] for r in proof['checks'])
        and {r['case'] for r in group['captures']} == {'wuhan', 'beijing', 'coast', 'village',
            'wuhan_regional', 'wuhan_x30_layout', 'wuhan_large_text'}, 'Seven complete authored map cases required')
    review = read(P / 'reports/map_composition_native_review.json')
    reviewed = {r['file']: r['sha256'] for r in review['viewed_complete_captures']}
    require(all(reviewed.get(r['file']) == r['sha256'] for r in group['captures']),
        'All seven shipping viewports require actual complete-image inspection')
    require(not review['formal_art_approval'] and not review['ew6_parity_claimed']
        and not review['physical_android_device_tested'], 'Pending acceptance must remain explicit')
    quality = read(P / 'reports/quality_goal_turn_v0229.json')
    require(quality['version'] == current_version() and quality['runtime_source_sha256'] == runtime
        and quality['scoped_implementation_and_validation_complete']
        and not quality['overall_goal_complete'] and not quality['ew6_parity_claimed']
        and not quality['physical_android_device_tested'], 'Current scoped quality disclosure required')
    reports = {P / 'reports/map_composition_scope_audit.json', P / 'reports/map_composition_native_review.json',
        P / 'reports/map_composition_native_evidence.json', P / group['report'], P / 'reports/quality_goal_turn_v0229.json',
        P / 'reports/regression_hash_batch_equivalence.json'}
    require(all(path.is_file() for path in reports), 'Composition evidence file missing')
    return dict(map_composition_checks=58, map_composition_captures=7,
        retained_originals_from_0228=2507, retained_0228_content_hash=audit['content_hash'],
        all_seven_composition_captures_manually_viewed=True, overall_goal_complete=False), reports
