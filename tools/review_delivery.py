"""Review the packaged current beta without rewriting older release archives."""
import hashlib
import json
import posixpath
import re
import zipfile
from pathlib import Path
from package_delivery import OUT, P, ROOT, sha
from build_release import source_digest


def member_sha(archive, name):
    digest=hashlib.sha256()
    with archive.open(name) as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    manifest=json.loads((OUT/'release_manifest.json').read_text(encoding='utf-8'))
    files={item['kind']:item for item in manifest['files']}
    file_checks=[{'name':item['name'],'matches':sha(OUT/item['name'])==item['sha256'],'bytes_match':(OUT/item['name']).stat().st_size==item['bytes']} for item in manifest['files']]
    checks=[]
    with zipfile.ZipFile(OUT/files['windows_portable']['name']) as archive:
        checks.append({'name':'windows_executable_matches_verified_export','passed':member_sha(archive,'RailwayWarlords.exe')==sha(P/'build/windows/RailwayWarlords.exe')})
    with zipfile.ZipFile(OUT/files['godot_source_and_provenance']['name']) as archive:
        names=set(archive.namelist())
        selected=[P/'project.godot',P/'content/content_registry.gd',P/'domain/historical_rules.gd',P/'domain/victory_rules.gd',P/'domain/movement_rules.gd',P/'domain/combat_random.gd',P/'domain/veterancy_rules.gd',P/'presentation/atlas_relief.gd',P/'presentation/atlas_surface.gd',P/'presentation/map_view.gd',P/'presentation/battle_playback.gd',P/'presentation/battle_cinema.gd',P/'docs/09_历史事件与征服结算.md',P/'docs/10_地图绘制与可读性.md',P/'docs/11_系列对标与实机修复.md',P/'docs/12_容量性能与渲染等价.md',P/'app/capacity_fixture.gd',P/'app/match_controller.gd',P/'app/rules_job.gd',P/'app/rules_worker.gd',P/'domain/rules_query_cache.gd',P/'docs/13_后台规则与响应性.md',P/'reports/rules_worker_tests.json',P/'ai/ai_planner.gd',P/'reports/performance_evidence.json',P/'tests/fixtures/reference_v020.json',P/'assets/scenery/scenery_recon_biplane.png',ROOT/'output/imagegen/15_warlord_railways_full_gameplay.png']
        selected.extend([P/'docs/14_地图比例与五倍格网.md', P/'reports/map_scale_tests.json', P/'reports/scaled_logistics_tests.json', P/'persistence/save_service.gd', P/'domain/logistics_rules.gd', P/'tools/enlarge_maps.py', P/'tests/fixtures/map_scale_baseline_v022.json'])
        selected.extend([P/'reports/movement_cache_tests.json', P/'reports/map_scale_baseline_verified.json', P/'tests/fixtures/logistics_reference_v022.gd', P/'tests/fixtures/capacity_full_conquest.json', ROOT/'design/geodata/terrain_tiles/scaled_samples.json'])
        selected.extend([P/'docs/16_欧陆战争6对标与美术改版.md',P/'docs/22_地图细节边界与单位动效改版.md',P/'docs/25_欧陆战争6地图资源差距评估.md',P/'docs/26_欧陆战争6_UI结构与视觉对标.md',P/'tests/territory_visual_test.gd',P/'reports/territory_visual_tests.json',P/'reports/ew6_asset_generation.json',P/'reports/ai_log_reconciliation.json',P/'presentation/data/asia_landcover_features.json',ROOT/'output/research/european_war_6/sources.json'])
        selected.extend([P/'content/maps/asia_strategic.json',P/'content/history/asia_timeline.json',P/'content/history/asia_order_of_battle.json',P/'tests/asia_content_test.gd',P/'reports/asia_content_tests.json',P/'docs/19_亚洲全境时间线与史实数据.md',P/'docs/20_亚洲战役系统与自由世界.md',P/'docs/21_经济物资士气与多元军队.md'])
        selected.extend([P/'reports/screenshots/asia_1840_overview.png',P/'reports/screenshots/asia_1840_overview.json'])
        selected.extend(path for path in (ROOT/'output/imagegen/warlord/ew6_v025').rglob('*') if path.is_file() and path.name in {'source.png','prompt.txt','review.json','provenance.json'})
        selected.extend((P/'reports/screenshots/territory').glob('*.png'))
        selected.extend([P/'presentation/historical_places.gd',P/'presentation/data/settlements_v023.json',P/'tests/historical_places_test.gd',P/'tools/compile_settlements.py',P/'tools/validate_settlements.py',P/'reports/settlement_compilation.json',P/'reports/settlement_geography_validation.json',P/'reports/historical_places_tests.json',P/'docs/15_历史聚落与势力地图.md',P/'assets/legal/GEONAMES-NOTICE.txt',ROOT/'design/geodata/settlements/CN.txt',ROOT/'design/geodata/settlements/readme.txt'])
        selected.extend(path for path in (ROOT/'output/imagegen/warlord/settlements_v023').rglob('*') if path.is_file() and path.name in {'source.png','prompt.txt'})
        selected.extend((ROOT/'design/geodata/historical_records').glob('*'))
        selected.append(ROOT/'output/imagegen/prompts/15_warlord_railways_full_gameplay.txt')
        selected.extend([P/'app/prepared_sight_cache.gd',P/'presentation/historical_places.gd',P/'presentation/data/settlements_v023.json',P/'docs/15_历史聚落与势力地图.md'])
        selected.extend([P/'tests/snapshot_optimization_test.gd',P/'tests/immutable_state_fingerprint.gd',
            P/'tests/fixtures/reference_access_v023.gd',P/'tests/fixtures/reference_kernel_v023.gd',
            P/'tests/fixtures/reference_v023.json',P/'tests/fixtures/reference_cache_v023.gd',P/'reports/snapshot_optimization_tests.json',
            P/'reports/snapshot_reference_validation.json',P/'tools/verify_snapshot_reference.py'])
        for path in selected:
            if not path.is_file():continue
            name=path.relative_to(ROOT).as_posix()
            checks.append({'name':'source_bytes:'+name,'passed':name in names and member_sha(archive,name)==sha(path)})
        dem_paths=list((ROOT/'design/geodata/terrain_tiles').rglob('*.tif'))
        checks.append({'name':'all_355_numeric_dem_tiles_preserved','passed':len(dem_paths)==355 and all(path.relative_to(ROOT).as_posix() in names and member_sha(archive,path.relative_to(ROOT).as_posix())==sha(path) for path in dem_paths),'tiles_checked':len(dem_paths)})
        missing=[];link_count=0
        for name in sorted(n for n in names if n.startswith('game/railway_warlords/docs/') and n.endswith('.md')):
            for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',archive.read(name).decode('utf-8')):
                target=target.strip('<>').split('#',1)[0]
                if not target or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',target):continue
                resolved=posixpath.normpath(posixpath.join(posixpath.dirname(name),target));link_count+=1
                if resolved not in names and not any(n.startswith(resolved.rstrip('/')+'/') for n in names):missing.append({'document':name,'target':target})
        checks.append({'name':'source_document_links','passed':not missing,'links_checked':link_count,'missing':missing})
        checks.append({'name':'no_private_tools_or_editor_caches','passed':not any(token in name.lower() for name in names for token in ('.toolchain/','.godot/','keystore','sub2_image_gen.py'))})
    checks.append({'name':'apk_matches_verified_export','passed':sha(OUT/files['android_release_apk']['name'])==sha(P/'build/android/RailwayWarlords.apk')})
    checks.append({'name':'runtime_matches_verified_build','passed':manifest['runtime_source_sha256']==source_digest()[0]})
    # The current direction intentionally extends the baseline with sourced
    # Asian factions and generals. Preserve the baseline IDs and require the
    # validator's explicit delta ledger instead of demanding byte identity.
    resource = json.loads((P/'reports/resource_validation.json').read_text(encoding='utf-8'))
    deltas = resource.get('baseline_definition_deltas', {})
    checks.append({'name':'original_definition_tables_preserved',
                   'passed':bool(deltas) and all(not row.get('missing_ids') for row in deltas.values()),
                   'baseline_ids_preserved':bool(deltas) and all(not row.get('missing_ids') for row in deltas.values()),
                   'intentional_extensions_recorded':deltas})
    report={'version':manifest['version'],'passed':all(item['matches'] and item['bytes_match'] for item in file_checks) and all(item['passed'] for item in checks),'artifact_hash_checks':file_checks,'checks':checks,'tests':manifest['tests'],'content_hash':manifest['content_hash'],'physical_android_device_tested':False,'formal_release_ready':False,'pending_release_acceptance':manifest['pending_release_acceptance']}
    (OUT/'交付复核.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'version':report['version'],'passed':report['passed'],'artifact_hashes':len(file_checks),'checks':len(checks),'physical_android_device_tested':False},ensure_ascii=True))
    raise SystemExit(0 if report['passed'] else 1)


if __name__=='__main__':main()
