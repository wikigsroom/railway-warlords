"""Additional commander gates; retain the existing UI, map and dual-export gates."""
from build_release import P, current_version
from package_delivery import read, sha, require

def validate_commander_content(runtime):
    audit = read(P / 'reports/commander_pool_scope_audit.json')
    require(audit['passed'] and audit['version'] == current_version()
        and audit['runtime_source_sha256'] == runtime and not audit['unexpected_changed_files']
        and audit['preserved_existing_originals'] == 1327 and audit['added_portrait_originals'] == 1180,
        'Current commander scope audit required')
    services = read(P / 'content/definitions/commander_service.json')
    generals = read(P / 'content/definitions/generals.json')
    sources = {r['id']: r for r in read(P / 'content/definitions/commander_sources.json')}
    require(len(services) == len(generals) == 324 and {r['id'] for r in services} == {r['id'] for r in generals},
        'Complete implemented military roster required')
    full_command = [r for r in services if r['command_level'] not in {'deputy_division', 'army_political_co_command'}]
    require(len(full_command) >= 300 and all(r['documented_title'] and r['source_ids']
        and all(s in sources for s in r['source_ids']) for r in services), 'At least 300 sourced brigade/division-or-higher commanders required')
    reviewed = read(P / 'reports/commander_portrait_source_review.json')['viewed_originals']
    installed = read(P / 'reports/commander_portrait_installation.json')
    require(len(reviewed) == installed['installed_expansion_originals'] == 1180
        and not installed['source_rasters_modified'] and not installed['manual_compositing']
        and not installed['formal_art_approval'] and not installed['historical_likeness_approval'],
        'All 1,180 expansion originals must have individual inspection and unchanged-byte installation')
    assets = {a['id']: a for a in read(P / 'assets/manifest.json')['assets']}
    require(len({r['id'] for r in reviewed}) == 1180, 'Duplicate source inspection')
    for row in reviewed:
        asset = assets[row['id']]
        require(row['viewed_complete_original'] and row['usable_for_in_engine_review']
            and row['notes'] and not row['formal_art_approval'] and not row['historical_likeness_approval']
            and asset['source_kind'] == 'sub2_image_gen' and asset['model'] == 'gpt-image-2.5'
            and asset['quality'] == 'high' and not asset['image_modified']
            and sha(P / asset['engine_path'].removeprefix('res://')) == asset['source_sha256'] == row['sha256']
            and sha(P / 'docs/asset-prompts' / (row['id'] + '.txt')) == asset['prompt_sha256'],
            'Uninspected, modified or untraceable expansion portrait: ' + row['id'])
    coverage = read(P / 'reports/commander_coverage.json')
    deployments = read(P / 'content/definitions/commander_deployments.json')
    reserves = read(P / 'content/definitions/commander_recall_pools.json')
    starting_ids = {e['general_id'] for s in deployments for rows in s['factions'].values() for e in rows}
    reserve_ids = {e['general_id'] for s in reserves for rows in s['factions'].values() for e in rows}
    available_ids = starting_ids | reserve_ids
    unrated = sum(r.get('balance_profile') == 'unrated_command_role_baseline_v1' for r in generals)
    require(unrated == 295, 'Current individual-balance status differs from the documented baseline')
    require(coverage['distinct_starting_commanders'] == len(starting_ids) == 68
        and coverage['distinct_optional_reserve_commanders'] == len(reserve_ids) == 65
        and coverage['distinct_commanders_with_authored_gameplay_availability'] == len(available_ids) == 114
        and coverage['catalogue_only_pending_dated_deployment'] == len(generals) - len(available_ids) == 210,
        'Catalogue size must not be represented as the number with authored gameplay availability')
    require(coverage['military_commanders'] == coverage['military_people_with_four_portrait_stages'] == 324
        and coverage['scenario_roster_snapshots'] == 61 and coverage['initial_roster_entries'] == 280
        and coverage['optional_free_world_reserve_entries'] == 89
        and not coverage['all_qualifying_asian_commanders_covered']
        and not coverage['complete_historical_orders_of_battle'] and not coverage['full_service_tenures_verified'],
        'Coverage must match actual implementations and disclose remaining historical work')
    proof = read(P / 'reports/commander_roster_native_evidence.json')
    require(proof['capture_driver_sha256'] == sha(P / 'tools/capture_commander_roster.py')
        and {g['profile'] for g in proof['groups']} == {'windows', 'x30_layout', 'large_text'},
        'Current complete commander capture driver and three layouts required')
    for group in proof['groups']:
        report = read(P / group['report'])
        require(report['passed'] and report['all_portraits_complete']
            and report['people_with_four_registered_portraits'] == 328
            and report['military_commanders'] == 324 and len(report['captures']) == 6
            and sha(P / group['log']) == group['log_sha256'],
            'Full commander browsing and actual reserve assignment required')
    archive = read(P / 'docs/commander-production/index.json')
    require(archive['production_terminal'] and archive['generated_originals'] == 1180,
        'Reproducible final production archive required')
    for row in archive['files']:
        require(sha(P / row['file']) == row['sha256'], 'Production archive changed: ' + row['file'])
    paths = {P / 'reports' / name for name in ['commander_pool_scope_audit.json', 'commander_coverage.json',
        'commander_portrait_installation.json', 'commander_portrait_source_review.json']}
    paths.update({P / 'docs/data/commanders.csv', P / 'docs/data/scenario_commanders.csv', P / 'docs/commander-production/index.json'})
    paths.update(P / row['file'] for row in archive['files'])
    summary = dict(full_brigade_or_higher_commanders=len(full_command), commander_sources=len(sources),
        initial_roster_entries=coverage['initial_roster_entries'],
        optional_free_world_reserve_entries=coverage['optional_free_world_reserve_entries'],
        non_training_sides_without_authored_commander=coverage['non_training_sides_without_authored_commander'],
        distinct_starting_commanders=len(starting_ids), distinct_optional_reserve_commanders=len(reserve_ids),
        distinct_commanders_with_authored_gameplay_availability=len(available_ids),
        catalogue_only_pending_dated_deployment=len(generals)-len(available_ids),
        all_registered_commanders_have_current_scenario_availability=False,
        unrated_baseline_military_definitions=unrated, individual_commander_balance_complete=False,
        all_qualifying_asian_commanders_covered=False, complete_historical_orders_of_battle=False,
        full_service_tenures_verified=False, old_map_geography_preserved=True,
        independent_side_rosters=True, actual_reserve_appointment_tested=True)
    return summary, paths
