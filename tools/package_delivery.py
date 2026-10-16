"""Package verified native artifacts and portable source; never edits media or copies secrets."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile
import argparse
from datetime import datetime, timezone
from build_release import source_digest, rule_dependencies_digest, current_version
from regression_dependencies import modified as dependency_modified

P = Path(__file__).resolve().parents[1]
ROOT = P.parents[1]
VERSION = current_version()
TAG = 'v' + VERSION.replace('.', '')
OUT = ROOT / 'output/releases' / ('railway-warlords-' + VERSION)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def require(value, message):
    if not value:
        raise SystemExit(message)


def add_tree(archive, folder, relative_to, allowed=None):
    for path in sorted(folder.rglob('*')):
        if not path.is_file():
            continue
        relative = path.relative_to(relative_to)
        if any(part in {'.godot', '.git', '.toolchain', '__pycache__', 'build'} for part in relative.parts):
            continue
        if any(word in path.name.lower() for word in ('keystore', 'credential', 'password', '.download', '.partial')):
            continue
        if allowed is not None and path.suffix.lower() not in allowed:
            continue
        archive.write(path, relative.as_posix())


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--allow-domain-timing-limited-beta',action='store_true',help='Keep performance.passed=false; only permit a test build when native rendering, response, semantic, integrity and all functional checks pass.')
    options=parser.parse_args()
    fixture = read(P / 'reports/sample_state_v2.json')
    fingerprint = fixture['content_hash']
    scenario_catalog = read(P / 'content/scenarios/catalog.json')
    short_ai_expected = sum(3 if read(P / 'content/scenarios' / f'{scenario_id}.json').get('mode') == 'campaign' else 1 for scenario_id in scenario_catalog['scenarios'])
    scale = read(P / 'reports/map_scale_tests.json')
    require(scale['passed'] and scale['content_hash'] == fingerprint and scale['game_version'] == VERSION, 'Complete current fivefold geography and save roundtrip evidence is required.')
    scale_baseline = read(P / 'reports/map_scale_baseline_verified.json')
    logistics = read(P / 'reports/scaled_logistics_tests.json')
    movement = read(P / 'reports/movement_cache_tests.json')
    places = read(P / 'reports/historical_places_tests.json')
    snapshots = read(P / 'reports/snapshot_optimization_tests.json')
    require(snapshots['game_version']==VERSION and snapshots['failed']==0 and snapshots['trace_commands']>=300 and len(snapshots['traces'])==4, 'Current archived-kernel transaction and all-state/RNG equivalence is required.')
    place_geography = read(P / 'reports/settlement_geography_validation.json')
    place_compile = read(P / 'reports/settlement_compilation.json')
    # This historical dataset remains version 0.2.3 across runtime-only updates.
    # Include its actual generation logs instead of relabeling old evidence.
    place_tag = 'v' + place_compile['version'].replace('.', '')
    place_sha = sha(P / 'presentation/data/settlements_v023.json')
    require(places['passed'] and not places['failures'] and places['content_hash']==fingerprint and place_geography['passed'] and place_compile['passed'] and place_compile['places']==67 and all(row['presentation_data_sha256']==place_sha for row in (places, place_geography, place_compile)), 'Current sourced settlement geography and native interaction checks are required.')
    require(scale_baseline['passed'] and len(scale_baseline['maps']) == 3, 'Fivefold map baseline must match the preserved 0.2.2 source archive.')
    require(all(report['passed'] and report['content_hash'] == fingerprint and not report['failures'] for report in (logistics, movement)), 'Full supply and movement cache semantic-equivalence checks must pass.')
    resource = read(P / 'reports/resource_validation.json')
    rules = read(P / 'reports/rule_tests.json')
    acceptance = read(P / 'reports/acceptance_tests.json')
    inputs = read(P / 'reports/input_tests.json')
    geography = read(P / 'reports/geography_tests.json')
    progression = read(P / 'reports/progression_tests.json')
    transaction = read(P / 'reports/transaction_tests.json')
    strategic = read(P / 'reports/strategic_history_tests.json')
    asia = read(P / 'reports/asia_content_tests.json')
    atlas = read(P / 'reports/atlas_render_tests.json')
    map_detail = read(P / 'reports/map_detail_boundary_motion_tests.json')
    preserved_geography = read(P / 'reports/atlas_detail_geography.json')
    combat = read(P / 'reports/combat_presentation_tests.json')
    automation = read(P / 'reports/automation_tests.json')
    worker = read(P / 'reports/rules_worker_tests.json')
    visual = read(P / 'reports/visual_playtest.json')
    support = read(P / 'reports/support_playtest.json')
    native_evidence = read(P / 'reports/native_visual_evidence.json')
    territory=read(P/'reports/territory_visual_tests.json')
    require(territory['passed'] and territory['build_version']==VERSION and territory['content_hash']==fingerprint and territory['published_scenario_unchanged'] and territory['state_and_random_stream_unchanged'] and len(territory['measured_factions'])>=8, 'Current native territory pixels must distinguish many actual factions without changing the match.')
    soak = read(P / 'reports/ai_soak.json')
    ai_evidence = read(P / 'reports/ai_dependency_evidence.json')
    rule_hash, rule_modified = rule_dependencies_digest()
    require(ai_evidence['content_hash'] == fingerprint and ai_evidence['rules_dependency_sha256'] == rule_hash and all(sha(P/'reports'/r['file']) == r['sha256'] for r in ai_evidence['reports']), 'Completed AI evidence must match unchanged rule dependencies and report bytes.')
    reconciliation=read(P/'reports/ai_log_reconciliation.json')
    require(reconciliation['passed'] and reconciliation['rules_dependency_sha256']==rule_hash and all(sha(P/'reports'/row['file'])==row['sha256'] for row in reconciliation['logs']+reconciliation['reports']), 'Recovered native AI aggregate fields and complete source logs must retain their verified bytes.')
    exports = read(P / 'reports/export_results.json')
    source_hash, source_modified = source_digest()
    visual_modified=max(source_modified,(P/'app/visual_playtest.gd').stat().st_mtime)
    require(all((P/'reports'/name).stat().st_mtime>=visual_modified for name in ['visual_playtest.json','support_playtest.json']) and support.get('player_defense_performed',False) and support.get('setup_replay_same_final_state',False), 'Current legal defense/construction/support demo and complete replay are required.')
    require(native_evidence['passed'] and native_evidence['runtime_source_sha256'] == source_hash and native_evidence['video']['sha256'] == sha(P/'reports/atlas_v2_native_final.mp4'), 'Current native video, screenshot and raster provenance evidence is required.')
    color_proof=native_evidence['territory_color_evidence']
    require(color_proof['sha256']==sha(P/'reports/territory_visual_tests.json') and all(row['sha256']==sha(P/row['file']) for row in color_proof['captures']), 'Native territory color evidence must preserve the measured raw captures.')
    performance = read(P / 'reports/performance_evidence.json')
    allowed_performance=performance['passed'] or (options.allow_domain_timing_limited_beta and performance.get('native_and_semantic_checks_passed',False) and not performance.get('domain_performance_targets_passed',True))
    require(allowed_performance and performance['version'] == VERSION and performance['runtime_source_sha256'] == source_hash and all(sha(P/'reports'/row['file']) == row['sha256'] for row in performance['reports']), 'Current native maximum-map performance and semantic/pixel evidence must match the runtime and original report bytes. Domain timing misses require an explicitly identified limited test build.')
    require(performance['fixture_file_sha256'] == sha(P/'tests/fixtures/capacity_full_conquest.json') and all(sha(P/row['file']) == row['sha256'] for row in performance['native_comparison_images']), 'The measured real-geography fixture and raw complete-view captures must preserve their verified bytes.')
    require(worker['failed'] == 0 and worker['passed'] >= 347 and worker['game_version'] == VERSION and worker['content_hash'] == fingerprint and performance['ui_eight_millisecond_slice_verified'], 'Current serialized worker, cancellation, save I/O and native 8 ms handoff evidence is required.')
    apk_content = read(P / 'reports/apk_content_validation.json')
    preflight = read(P / 'reports/delivery_preflight.json')
    require(preflight['passed'] and preflight['previous_releases_preserved'] and len(preflight['preserved_releases']) >= 32, 'Public files and all nine preserved previous releases must pass preflight.')
    require(resource['passed'] and not resource['errors'], 'Resource/schema checks must pass before packaging.')
    require(rules['failed'] == 0 and acceptance['failed'] == 0, 'Rule/acceptance checks must pass.')
    require(asia['failed'] == 0 and asia['content_hash'] == fingerprint and asia['passed'] >= 600, 'Seven Asia timelines, formations, free-world starts and province-scoped missions must pass.')
    require(strategic['failed'] == 0 and strategic['passed'] >= 46 and strategic['ruleset_version'] == fixture['ruleset_version'], 'Historical event and conquest settlement checks must pass.')
    require(atlas['failed'] == 0 and atlas['passed'] >= 66 and preserved_geography['passed'] and len(preserved_geography['maps']) == 5 and all(row['rule_fields_unchanged'] and row['historical_administration_unchanged'] for row in preserved_geography['maps']), 'All five atlas layouts and preservation of rule geometry and period administration must pass.')
    require(map_detail['passed'] and not map_detail['failures'] and map_detail['content_hash'] == fingerprint and map_detail['game_version'] == VERSION, 'Strategic terrain detail, campaign theatre camera bounds and unit-family movement evidence must pass.')
    require(combat['failed'] == 0 and automation['failed'] == 0 and visual['passed'] and visual['artillery_visible'] and support['passed'], 'Native movement, artillery, dice, air and automatic command checks must pass.')
    require(progression['failed'] == 0 and progression['achievement_criteria_covered'] == 24 and transaction['failed'] == 0, 'Progression and immutable-map transaction checks must pass.')
    require(not inputs['failures'] and not geography['failures'], 'Input/geography checks must pass.')
    require(soak['invariants_passed'] and soak['cases'] == short_ai_expected, f'Current complete short AI regression ({short_ai_expected} scene/difficulty cases) is required.')
    require(all(d['content_hash'] == fingerprint for d in (rules, acceptance, geography, progression, transaction, strategic, atlas, soak, combat, automation, visual, support, asia, map_detail)), 'Test reports must match the packaged content.')
    require(apk_content['passed'] and not apk_content['private_files_detected'], 'APK contents must match the tested source.')
    require(apk_content['raster_manifest_byte_verified'] and len(apk_content['raster_import_files_verified']) == resource['raster_count'] and all(item['current_import_bytes_match'] for item in apk_content['raster_import_files_verified']), 'Current imported raster bytes must be verified inside the APK.')
    require(apk_content['artifact_sha256'] == sha(P/'build/android/RailwayWarlords.apk'), 'APK verification must match the current binary.')
    require(all(r['export_verified'] and r['sha256'] == sha(Path(r['path'])) for r in exports), 'Fresh verified exports are required.')
    require(all(r['runtime_source_sha256'] == source_hash for r in exports), 'Exported source must match the packaged runtime.')
    from run_validation import CHECKS
    for check in CHECKS:
        report_name='rule_tests.json' if check=='run_tests' else check.removesuffix('_test')+'_tests.json'
        log_name=check+'_'+TAG+'.log'
        require(min((P/'reports'/report_name).stat().st_mtime,(P/'reports'/log_name).stat().st_mtime)>=dependency_modified(check), 'Regression must finish after its transitive source/data dependencies: '+check)
    regression_evidence=read(P/'reports/regression_dependency_evidence.json')
    require(regression_evidence['passed'] and regression_evidence['runtime_source_sha256']==source_hash and len(regression_evidence['checks'])==len(CHECKS) and all(sha(P/'reports'/row['report'])==row['report_sha256'] and sha(P/'reports'/row['log'])==row['log_sha256'] for row in regression_evidence['checks']), 'All transitive regression sources and native report bytes must be sealed against the packaged runtime.')
    signature = (P / 'reports/apk_signature.log').read_text(encoding='utf-8')
    require('Verified using v2 scheme (APK Signature Scheme v2): true' in signature, 'APK signature verification is required.')
    captures = ['map_final_windows', 'map_x30_layout', 'map_large_text', 'map_historical_atlas', 'map_bohai_coast', 'map_jingfeng_overview', 'map_desktop_benchmark', 'legion_deployment_windows', 'legion_deployment_x30', 'map_1925_calendar_fixture', 'asia_1840_overview', 'asia_1840_field_v033', 'asia_forest_detail_v030', 'asia_forest_detail_v033', 'asia_forest_detail_v034', 'asia_forest_detail_v035', 'asia_forest_detail_v038', 'asia_strategic_landcover_v032', 'asia_strategic_landcover_v033', 'asia_strategic_landcover_v034', 'asia_strategic_landcover_v037', 'asia_greater_khingan_v039']
    captures += ['settlements_country','settlement_village_details','settlement_county_details','settlement_market_details','settlement_capital_details','settlement_village_x30']
    for name in captures:
        meta = read(P / 'reports/screenshots' / (name + '.json'))
        require(meta['content_hash'] == fingerprint and meta['raw_godot_capture'], 'Current native capture required: ' + name)
        if name != 'map_1925_calendar_fixture':
            require(meta['build_version'] == VERSION and meta['qa_save_isolated'], 'Current native version and isolated QA saves are required: ' + name)
        if name.startswith('settlement'):
            require(meta['historical_places']['presentation_data_sha256']==place_sha and (P/'reports/screenshots'/(name+'.png')).stat().st_mtime>=source_modified, 'Fresh exported place map capture is required: '+name)
    require('UI_SMOKE_PASS' in (P / 'reports/exported_windows_native.log').read_text(encoding='utf-8'), 'Exported Windows executable smoke test is required.')
    require(read(P / 'reports/desktop_benchmark.json')['content_hash'] == fingerprint, 'Current desktop rendering evidence is required.')
    for name in ['legion_deployment_windows', 'legion_deployment_x30']:
        validation = read(P / 'reports/screenshots' / (name + '_validation.json'))
        require(validation['passed'] and validation['content_hash'] == fingerprint and validation['stack'] == 2, 'Current exported progression UI controls are required.')
    require(read(P / 'reports/screenshots/map_x30_layout.json')['mobile_layout_profile'] and read(P / 'reports/screenshots/legion_deployment_x30.json')['mobile_layout_profile'], 'X30 profiles must exercise mobile controls, not only a wide desktop window.')
    calendar = read(P / 'reports/screenshots/map_1925_calendar_fixture.json')
    require(calendar['passed'] and calendar['calendar_fixture_only'] and not calendar['gameplay_completed_to_this_date'], 'Calendar-only native scene evidence must remain explicitly identified.')
    full = read(P / 'reports/ai_full_conquest.json')
    require(full['invariants_passed'] and full['content_hash'] == fingerprint and full['cases'] == 6 and full['full_match_run'] and full['meets_80_round_conquest'], 'Complete strong/weak conquest regression with real 80-round coverage is required.')
    require(all((P/'reports'/name).stat().st_mtime >= rule_modified for name in ['ai_soak.json','ai_full_conquest.json']), 'AI regression must finish after the final edits to its rule dependencies.')

    OUT.mkdir(parents=True, exist_ok=True)
    apk = OUT / f'RailwayWarlords-{VERSION}.apk'
    shutil.copyfile(P / 'build/android/RailwayWarlords.apk', apk)
    windows = OUT / f'RailwayWarlords-Windows-{VERSION}.zip'
    with zipfile.ZipFile(windows, 'w', zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
        archive.write(P / 'build/windows/RailwayWarlords.exe', 'RailwayWarlords.exe')
        archive.writestr('README.md', f'# 铁道烽烟：军阀时代 {VERSION} Windows\n\n运行同目录RailwayWarlords.exe，资源已嵌入，无需Godot/Python。鼠标点击选中、拖动平移、滚轮缩放；目标再次点击或确认按钮执行。Tab选待命部队；Space在演出时跳过，空闲时打开结束阶段确认；Esc取消待执行命令或暂停。设置可调演出速度。\n\n完整操作见docs/01_运行与操作.md；容量性能见docs/12_容量性能与渲染等价.md；历史地图依据见docs/07_历史地理与地图美术.md；系列对照与修复见docs/11_系列对标与实机修复.md；实际验收范围见docs/05_测试与验收.md。\n\n这是可玩测试版。Windows已实际运行；Android APK与完整Godot工程分别提供。字体和引擎/地图数据许可随包保留。\n')
        add_tree(archive, P / 'docs', P)
        add_tree(archive, P / 'assets/legal', P)
        for path in (P / 'assets/font').glob('OFL*.txt'):
            archive.write(path, 'licenses/' + path.name)

    source = OUT / f'RailwayWarlords-Godot-{VERSION}.zip'
    report_names = [
        'rule_tests.json', 'run_tests_'+TAG+'.log', 'acceptance_tests.json', 'acceptance_test_'+TAG+'.log',
        'input_tests.json', 'input_test_'+TAG+'.log', 'geography_tests.json', 'geography_test_'+TAG+'.log',
        'ai_soak.json', 'ai_dependency_evidence.json', 'sample_state_v2.json', 'resource_validation.json',
        'progression_tests.json', 'progression_test_'+TAG+'.log', 'transaction_tests.json', 'transaction_test_'+TAG+'.log', 'ai_full_conquest.json', 'ai_long_'+TAG+'.log', 'ai_short_'+TAG+'.log',
        'strategic_history_tests.json', 'strategic_history_test_'+TAG+'.log', 'atlas_render_tests.json', 'atlas_render_test_'+TAG+'.log', 'atlas_detail_geography.json', 'calendar_capture_'+TAG+'.log', 'historical_source_fetch.json', 'map_compilation.json', 'art_review.json', 'desktop_benchmark.json', 'export_results.json',
        'combat_presentation_tests.json', 'combat_presentation_test_'+TAG+'.log', 'automation_tests.json', 'automation_test_'+TAG+'.log', 'visual_playtest.json', 'visual_playtest_final_'+TAG+'.log', 'support_playtest.json', 'support_playtest_'+TAG+'.log', 'atlas_v2_generation.json', 'atlas_v2_asset_audit.json', 'native_visual_evidence.json', 'movie_encode_'+TAG+'.log',
        'export_windows.log', 'export_android.log', 'exported_windows_native.log',
        'apk_signature.log', 'apk_badging.log', 'apk_permissions.log', 'apk_content_validation.json',
        'android_devices.log', 'final_import.log', 'metadata_export.log', 'delivery_preflight.json',
    ]
    report_names += ['capacity_geography.json', 'capacity_domain_'+TAG+'.json', 'capacity_domain_'+TAG+'.log', 'performance_equivalence.json', 'performance_equivalence_'+TAG+'.log', 'unit_layer_native.json', 'unit_layer_native.log', 'unit_layer_pixel_validation.json', 'capacity_windows_'+TAG+'.json', 'capacity_windows_'+TAG+'.log', 'capacity_x30_'+TAG+'.json', 'capacity_x30_'+TAG+'.log', 'performance_evidence.json', 'capacity_domain_v020.json', 'capacity_domain_v020.log', 'capacity_render_v020.json', 'capacity_render_v020.log', 'capacity_draw_baseline.json', 'capacity_draw_baseline_draw_profile.json', 'capacity_profile_v020.json', 'capacity_profile_v020.log']
    report_names += ['map_scale_tests.json', 'map_scale_test_'+TAG+'.log', 'map_scale_v023.json', 'map_scale_baseline_verified.json', 'scaled_logistics_tests.json', 'scaled_logistics_test_'+TAG+'.log', 'movement_cache_tests.json', 'movement_cache_test_'+TAG+'.log']
    report_names += ['rules_worker_tests.json', 'rules_worker_test_'+TAG+'.log']
    report_names += ['asia_content_tests.json', 'asia_content_test_'+TAG+'.log']
    report_names += ['historical_places_tests.json','historical_places_test_'+TAG+'.log','settlement_geography_validation.json','settlement_geography_validation_'+place_tag+'.log','settlement_compilation.json','settlement_compilation_'+place_tag+'.log','settlement_asset_generation.json']
    report_names += ['snapshot_optimization_tests.json','snapshot_optimization_test_'+TAG+'.log','snapshot_reference_validation.json','regression_dependency_evidence.json']
    report_names += ['ew6_asset_generation.json','ew6_asset_generation_initial.json','territory_visual_tests.json','territory_visual_'+TAG+'.log','map_detail_boundary_motion_tests.json','map_detail_boundary_motion_test_'+TAG+'.log']
    report_names += ['ai_log_reconciliation.json','ai_full_conquest_'+TAG+'_original.json']
    report_names += ['design_document_validation_v025.log','design_document_validation_v025_initial.log']
    report_names += ['unit_layer_native_v025_initial.json','unit_layer_pixel_validation_v025_initial.json','unit_layer_pixel_attempt_v025_initial.json']
    # An initial performance seal is an optional historical attempt. Keep it
    # when it exists, but never manufacture or relabel a current final seal as
    # an initial measurement.
    initial_performance_seal = P / 'reports' / ('performance_evidence_' + TAG + '_initial_seal.json')
    if initial_performance_seal.exists():
        report_names.append(initial_performance_seal.name)
    report_names += ['snapshot_reference_validation_'+TAG+'.log']
    # Keep actual measurements under their original versioned names. A new
    # release must not relabel an old failed attempt as a current measurement.
    attempt_patterns=['capacity_domain_v*_initial.*','capacity_domain_v*_second.*',
        'capacity_domain_v*_final_attempt.*','capacity_domain_v*_under_concurrent_soak.*',
        'capacity_domain_v*_isolated_attempt.*','capacity_domain_v*_coordinate_keys_and_visibility.*','capacity_windows_v*_initial*',
        'capacity_windows_v*_font_only*','capacity_profile_v024_*',
        'query_equality_profile_v024.*','capacity_breakdown_v024.*','ai*_v024_pre_coordinate_keys.*']
    report_names += sorted({path.name for pattern in attempt_patterns for path in (P/'reports').glob(pattern)
                            if path.suffix in ('.json','.log')})
    report_names=list(dict.fromkeys(report_names))
    for profile in ('windows','x30'):
        report_names += ['responsiveness_'+profile+'_'+TAG+'.json', 'responsiveness_'+profile+'_'+TAG+'.log']
    for name in report_names:
        if name.endswith('.log') and name not in ['android_devices.log']:
            text = (P / 'reports' / name).read_text(encoding='utf-8', errors='replace')
            require('SCRIPT ERROR:' not in text and '\nERROR:' not in text, 'Verification log contains an error: ' + name)
    with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
        for directory in ('app', 'content', 'domain', 'ai', 'persistence', 'presentation', 'audio', 'assets', 'schemas', 'tests', 'tools', 'docs'):
            add_tree(archive, P / directory, ROOT)
        for name in ('project.godot', 'export_presets.cfg', 'README.md', 'README.en.md', 'SOUND_DESIGN.md', 'LICENSE-NOTICE.md', 'AGENTS.md', '.gitignore', '.gitattributes', '.editorconfig'):
            path = P / name
            if path.exists():
                archive.write(path, path.relative_to(ROOT).as_posix())
        archive.write(ROOT / 'AGENTS.md', 'AGENTS.md')
        archive.write(P / 'reports/.gdignore', 'game/railway_warlords/reports/.gdignore')
        for name in report_names:
            path = P / 'reports' / name
            archive.write(path, path.relative_to(ROOT).as_posix())
        for name in captures:
            for suffix in ('.png', '.json'):
                path = P / 'reports/screenshots' / (name + suffix)
                archive.write(path, path.relative_to(ROOT).as_posix())
        for name in ['legion_deployment_windows', 'legion_deployment_x30']:
            path = P / 'reports/screenshots' / (name + '_validation.json')
            archive.write(path, path.relative_to(ROOT).as_posix())
        add_tree(archive, ROOT / 'design/铁道烽烟', ROOT)
        add_tree(archive, ROOT / 'design/geodata', ROOT, {'.shp', '.shx', '.dbf', '.prj', '.cpg', '.gpkg', '.zip', '.json', '.txt', '.md', '.pdf', '.html', '.tif'})
        raw = ROOT / 'output/imagegen/warlord/raw'
        for path in sorted(raw.rglob('*')):
            if path.is_file() and path.name in {'source.png', 'prompt.txt'}:
                archive.write(path, path.relative_to(ROOT).as_posix())
        for folder in ('atlas_v2','settlements_v023','ew6_v025'):
            for path in sorted((ROOT/'output/imagegen/warlord'/folder).rglob('*')):
                if path.is_file() and path.name in {'source.png', 'prompt.txt','review.json','provenance.json'}:
                    archive.write(path, path.relative_to(ROOT).as_posix())
        add_tree(archive,P/'reports/screenshots/territory',ROOT,{'.png'})
        research=ROOT/'output/research/european_war_6/sources.json'
        archive.write(research,research.relative_to(ROOT).as_posix())
        add_tree(archive,P/'reports/screenshots/visual_playtest',ROOT,{'.png','.json'})
        add_tree(archive,P/'reports/screenshots/unit_layers',ROOT,{'.png'})
        add_tree(archive,P/'reports/screenshots/unit_layers_v025_initial',ROOT,{'.png'})
        for profile in ('windows','x30'):
            path=P/'reports/screenshots'/('responsiveness_'+profile+'_'+TAG+'.png')
            archive.write(path,path.relative_to(ROOT).as_posix())
        for profile in ('windows','x30'):
            for suffix in ('.png','.json'):
                path=P/'reports/screenshots'/('capacity_'+profile+'_'+TAG+suffix)
                archive.write(path,path.relative_to(ROOT).as_posix())
        reference = ROOT / 'output/imagegen/15_warlord_railways_full_gameplay.png'
        archive.write(reference, reference.relative_to(ROOT).as_posix())
        reference_prompt = ROOT / 'output/imagegen/prompts/15_warlord_railways_full_gameplay.txt'
        archive.write(reference_prompt, reference_prompt.relative_to(ROOT).as_posix())
        archive.writestr('requirements-dev.txt', 'Pillow\njsonschema\nreferencing\npyshp\nshapely\npyproj\nnumpy\n')
        archive.writestr('README.md', f'# 铁道烽烟 Godot {VERSION} 工程\n\n用 Godot 4.7.2 打开 game/railway_warlords/project.godot。原设计、地理资料、原始图片与提示词、测试和程序文档随包保留。\n\n开发复现先安装同版官方导出模板；Python资料重编可使用 requirements-dev.txt。tools/build_release.py 的Godot/Java/SDK路径按本机配置调整。私有签名密钥与Sub2网关凭据不在此包。禁止Docker/WSL/虚拟化。\n')

    video = OUT / '实机战斗演示.mp4'
    require((P/'reports/atlas_v2_native_final.mp4').is_file(), 'Current native combat movie is required.')
    shutil.copyfile(P/'reports/atlas_v2_native_final.mp4', video)
    files = []
    for path, kind in ((windows, 'windows_portable'), (apk, 'android_release_apk'), (source, 'godot_source_and_provenance'), (video, 'native_godot_combat_video')):
        if path.suffix == '.zip':
            with zipfile.ZipFile(path) as archive:
                require(archive.testzip() is None, 'ZIP integrity failed: ' + path.name)
                names = archive.namelist()
                require(not any(any(token in name.lower() for token in ('.toolchain/', '.godot/', 'keystore', 'serif_blob.download')) for name in names), 'Private/cache file in archive.')
        files.append({'name': path.name, 'kind': kind, 'bytes': path.stat().st_size, 'sha256': sha(path)})
    ew6_assets = [item for item in resource.get('assets', []) if '/ew6_v025/' in item.get('source_file', '')] if isinstance(resource.get('assets'), list) else [item for item in read(P/'assets/manifest.json')['assets'] if '/ew6_v025/' in item.get('source_file', '')]
    if not ew6_assets:
        ew6_assets = [item for item in read(P/'assets/manifest.json')['assets'] if '/ew6_v025/' in item.get('source_file', '')]
    directional_unit_assets = [item for item in ew6_assets if item.get('style_version') == 'warlord_ew6_v025_directional_r001']
    manifest = {
        'created_at_utc': datetime.now(timezone.utc).isoformat(), 'version': VERSION, 'stage': 'playable_test_build', 'formal_release_ready': False,
        'domain_timing_limited_beta':not performance['passed'],
        'godot': '4.7.2.stable.official.ed1daf0bf', 'schema_version': 2, 'ruleset_version': fixture['ruleset_version'],
        'content_hash': fingerprint, 'runtime_source_sha256': source_hash, 'files': files,
        'assets': {'raster_png': resource['raster_count'], 'native_audio_wav': resource['audio_count'], 'ofl_fonts': resource['font_count'], 'raster_route': 'sub2-image-gen/gpt-image-2.5', 'manual_compositing': False, 'original_bytes_preserved': True},
        'ew6_art_direction': {'new_independent_rasters':len(ew6_assets),'base_ew6_rasters':len(ew6_assets)-len(directional_unit_assets),'directional_unit_rasters':len(directional_unit_assets),'unit_direction_source_views':96,'territory_opacity':0.26,'strategic_control_field_opacity':[0.20,0.23],'strategic_control_field':map_detail.get('territory_field',{}),'terrain_layer_toggle':True,'sourced_crossing_markers':any(row.get('name','')=='tactical_map_draws_sourced_bridge_and_ferry_markers' and row.get('passed',False) for row in map_detail.get('checks',[])),'terrain_foreground_tint':0.10,'measured_factions':len(territory['measured_factions']),'native_territory_color_checks':len(territory['checks']),'native_map_detail_checks':len(map_detail.get('checks',[])),'sourced_landcover_feature_count':int(map_detail.get('landcover_feature_count',8)),'terrain_surface_variants':'deterministic_plain_second_material','terrain_depth_bevel':'upper_left_highlight_lower_right_shadow','commercial_visual_parity_formally_approved':False},
        'historical_places': {'additional_nodes':67,'kinds':place_compile['kinds'],'interaction_checks':len(places['checks']),'geography_checks':len(place_geography['checks']),'presentation_data_sha256':place_sha,'current_city_ownership_colors':True,'sourced_dated_province_and_land_geometry':True,'historical_county_or_military_border_claimed':False},
        'tests': {'rules': rules['passed'], 'acceptance': acceptance['passed'], 'input': len(inputs['checks']), 'geography': len(geography['checks']), 'asia_content': asia['passed'], 'asia_timelines': asia['timeline_count'], 'asia_formations': asia['formations'], 'progression': progression['passed'], 'transaction': transaction['passed'], 'strategic_history': strategic['passed'], 'atlas_render': atlas['passed'], 'detail_geometry_maps': len(preserved_geography['maps']), 'combat_presentation': combat['passed'], 'automation': automation['passed'], 'rules_worker': worker['passed'], 'fivefold_map':len(scale['checks']), 'scaled_logistics':len(logistics['checks']), 'movement_cache':len(movement['checks']), 'achievement_criteria_covered': 24, 'failures': 0, 'ai_cases': soak['cases'], 'ai_aggregate_rounds': soak['completed_rounds'], 'ai_commands': soak['commands'], 'ai_rejected_commands': sum(r['rejects'] for r in soak['results']), 'single_match_100_rounds': full['single_match_100_rounds'], 'full_conquest_cases': full['cases'], 'full_conquest_completed_rounds': full['completed_rounds'], 'full_conquest_commands': full['commands'], 'full_conquest_rejects': sum(r['rejects'] for r in full['results']), 'meets_80_round_conquest': full['meets_80_round_conquest']},
        'windows': {'architecture': 'x86_64', 'embedded_resources': True, 'exported_executable_smoke_tested': True, 'authenticode_signed': False},
        'android': {'package': 'org.railwaywarlords.game', 'min_sdk': 24, 'target_sdk': 36, 'abis': ['arm64-v8a', 'armeabi-v7a'], 'apk_signature_v2_v3_verified': True, 'requested_permissions': [], 'source_json_files_byte_verified': len(apk_content['files']), 'target_device': 'Motorola X30', 'desktop_layout_resolution': [2400, 1080], 'desktop_layout_ui_scale': 1.2, 'physical_device_tested': False},
        'maximum_map_performance': {'passed': performance['passed'], 'real_usable_cells':71386, 'actual_cells':74762, 'active_units':240, 'native_windows_profiles':2, 'sustained_pan_zoom_seconds_per_profile':60, 'real_battle_measured':True, 'semantic_checks':performance['semantic_checks'], 'whole_viewport_pixel_pairs':performance['pixel_comparisons'], 'physical_android_device_tested':False, 'ui_eight_millisecond_slice_verified':performance['ui_eight_millisecond_slice_verified'], 'ui_slice_scope':performance['ui_slice_scope']},
        'pending_release_acceptance': ['完整军事起局/装备/县界历史审核', '全部素材正式发行审核', '21个亚洲史实战役人工策略与难度平衡', 'Motorola X30物理设备安装/触摸/持续性能'],
        'no_docker_wsl_virtualization': True,
    }
    manifest['tests']['snapshot_optimization']=snapshots['passed']
    manifest['tests']['snapshot_comparison_commands']=snapshots['trace_commands']
    if not performance['passed']:manifest['pending_release_acceptance'].append('最大地图完整AI阶段等规则层性能门槛；实际未达标分布和耗时见performance_evidence.json')
    (OUT / 'release_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    shutil.copyfile(P / 'docs/07_历史地理与地图美术.md', OUT / '历史地理与地图美术.md')
    shutil.copyfile(P / 'docs/05_测试与验收.md', OUT / '测试与验收.md')
    shutil.copyfile(P / 'docs/08_养成与事务回归.md', OUT / '养成与事务回归.md')
    shutil.copyfile(P / 'docs/09_历史事件与征服结算.md', OUT / '历史事件与征服结算.md')
    shutil.copyfile(P / 'docs/10_地图绘制与可读性.md', OUT / '地图绘制与可读性.md')
    shutil.copyfile(P / 'docs/11_系列对标与实机修复.md', OUT / '系列对标与实机修复.md')
    shutil.copyfile(P / 'docs/12_容量性能与渲染等价.md', OUT / '容量性能与渲染等价.md')
    shutil.copyfile(P / 'docs/13_后台规则与响应性.md', OUT / '后台规则与响应性.md')
    shutil.copyfile(P / 'docs/14_地图比例与五倍格网.md', OUT / '地图比例与五倍格网.md')
    shutil.copyfile(P / 'docs/15_历史聚落与势力地图.md', OUT / '历史聚落与势力地图.md')
    shutil.copyfile(P / 'docs/16_欧陆战争6对标与美术改版.md', OUT / '欧陆战争6对标与美术改版.md')
    shutil.copyfile(P / 'docs/19_亚洲全境时间线与史实数据.md', OUT / '亚洲全境时间线与史实数据.md')
    shutil.copyfile(P / 'docs/20_亚洲战役系统与自由世界.md', OUT / '亚洲战役系统与自由世界.md')
    shutil.copyfile(P / 'docs/21_经济物资士气与多元军队.md', OUT / '经济物资士气与多元军队.md')
    note = f'# 铁道烽烟：军阀时代 {VERSION}\n\nWindows解压便携包后运行RailwayWarlords.exe；Android安装APK；Godot工程包包含源代码、原设计、地理资料、原始素材及提示词。程序、工程与原生战斗录像的SHA256见release_manifest.json。\n\n本版保留京津、京奉和东部中国地图的五倍视野与48像素操作蜂窝，并新增20°E–180°E、10°S–80°N的亚洲全境战略层：7个真实时间锚点、81个真实城市节点、7668个物理陆海格、河流/海岸几何、历史控制色块和22条战略运输走廊。亚洲战略层明确采用自然地理与城市坐标抽象，不把城市影响区冒充历史县界；省级战役范围、时间、人物和编制记录见亚洲全境时间线与史实数据.md、亚洲战役系统与自由世界.md。\n\n最大既有地图为74762总格/71386有效格。两套导出EXE布局均进行了60秒持续平移缩放和真实攻击测试；详细帧率、AI阶段、存档耗时、命令与整幅画面等价证据见容量性能与渲染等价.md。本版按欧陆战争6方向登记{len(ew6_assets)}项独立Sub2素材，其中{len(directional_unit_assets)}项是16个兵种族的四方位独立源图；运行时保留96个方向源视图（原有斜向源图与新增北/东/南/西源图），采用自然地形、立体军阵、清晰势力分色与钢灰HUD。加入路径行军、开火弹道、受击、阵亡、反击、骰子交战小窗、航空演出与可停止的自动作战。战斗骰流随存档保存，预览显示区间；单位经验与晋升参与实际规则。逐项对照、来源和修复范围见系列对标与实机修复.md，实际原生运行与规则证据见测试与验收.md。\n\n实机战斗演示.mp4直接编码自Godot MovieWriter：双方按发布关卡的正常命令交战，没有插入假坐标、伤害或骰面，没有手工拼接画面。地图资料精度见历史地理与地图美术.md，完整设计稿保留在Godot工程包中。\n\nWindows便携程序已实际运行；Android已完成签名、版本、ABI与内容核对。X30的2400×1080移动布局在桌面Godot中验证，手机安装和性能尚未实测。\n\n养成档案可沿用；0.1.0–0.1.3的进行中战局请使用保留的对应旧版继续。本版采用ruleset{fixture['ruleset_version']}和新地图坐标；0.2.0–0.2.2进行中的战局使用对应保留旧包继续。\n'
    note += f'\n本版按欧陆战争6方向接入{len(ew6_assets)}项独立Sub2素材，重做自然地表、立体军阵、钢灰HUD和战场背景。当前战术城池势力以约26%半透明连续色块、战略城市归属场以20–23%半透明控制场、地形上层轻染和清晰边界区分，原生像素检查覆盖8个势力及战术缩放，地图细节专项与边界/运动回归按当前源码重跑，状态和随机流不变。新增平原第二材质、六边形明暗边缘、山地/河网/海岸/铁路分层及8处有来源且按年代门控的林地地名节点；单位保留缓入缓出、随路径转向、独立四方位兵种源图、瞄准前摇、后坐、弹道和命中结算。研究依据、核心结构对照、素材记录与实际范围见欧陆战争6对标与美术改版.md、地图细节边界与单位动效改版.md。\n'
    note += '\n串行原生后台规则与存档队列：计算期间地图继续平移、缩放和暂停；恢复只提交一次，停止自动作战、读档和返回菜单会使旧结果失效。回合后的资源栏和面板分帧刷新。两套最终EXE布局各测25条实际命令的主线程提交，含真实结束回合及同步信号回调；测量范围和线程/存档回归见后台规则与响应性.md。\n'
    note += '\n本版另外增加67处有历史名称/位置依据的地方节点（56县城、9村落、2省城），并将原有集镇按年代分级。点选可查询地方详情；当前势力色块沿真实年代省级轮廓和陆地绘制，随城市控制更新。新增4张Sub2原始聚落素材、67处位置与资料出处、交互和几何验收及完整PNG/提示词随工程保留。详见历史聚落与势力地图.md。\n'
    if not performance['passed']:
        slowest=max(row['timings']['ai_phase_ms_max'] for row in performance['domain_results'])
        note += f'\n当前包为带性能限制的可玩测试版：最大地图完整AI阶段最慢实测{slowest/1000:.2f}秒，超过5秒目标；总性能验收保持false，正式发行待优化。原生渲染、8ms主线程提交、功能与完整状态/随机流等价检查须全部通过才允许此测试包交付。此前未达标实测报告保留在工程内。\n'
    (OUT / '交付说明.md').write_text(note, encoding='utf-8')
    print(json.dumps({'release_directory': str(OUT), 'files': files, 'content_hash': fingerprint}, ensure_ascii=False))


if __name__ == '__main__':
    main()
