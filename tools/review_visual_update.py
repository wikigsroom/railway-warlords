"""Verify the scoped beta's shipped bytes and portable provenance without changing them."""
from pathlib import Path
import hashlib
import json
import posixpath
import re
import zipfile
from build_release import P, ROOT, current_version, source_digest
from package_delivery import sha, read


def member_sha(archive, name):
    digest = hashlib.sha256()
    with archive.open(name) as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    out = ROOT / 'output/releases' / ('railway-warlords-' + current_version())
    manifest = read(out / 'release_manifest.json')
    checks = []

    def check(name, passed, **details):
        checks.append(dict(name=name, passed=bool(passed), **details))

    check('explicit_scoped_beta_acceptance',
          manifest['release_kind'] == 'scoped_map_material_bank_beta'
          and not any(manifest[name] for name in [
              'formal_art_release_approval', 'full_endurance_and_capacity_rerun',
              'physical_android_device_tested', 'ew6_visual_parity_claimed']))
    artifacts = {}
    for row in manifest['artifacts']:
        path = out / row['file']
        check('artifact:' + row['file'], path.is_file()
              and path.stat().st_size == row['bytes'] and sha(path) == row['sha256'])
        artifacts[row['file']] = path
    windows = artifacts[f'RailwayWarlords-Windows-{current_version()}.zip']
    source = artifacts[f'RailwayWarlords-Godot-{current_version()}.zip']
    apk = artifacts[f'RailwayWarlords-{current_version()}.apk']
    for path in [windows, source]:
        with zipfile.ZipFile(path) as archive:
            check('zip_integrity:' + path.name, archive.testzip() is None)
    with zipfile.ZipFile(windows) as archive:
        check('windows_contains_verified_export',
              member_sha(archive, 'RailwayWarlords.exe') == sha(P / 'build/windows/RailwayWarlords.exe'))
        check('windows_geographic_notices_and_complete_source_license',all(
            member_sha(archive,'licenses/'+path.name)==sha(path) for path in (P/'assets/legal').glob('*.txt')))
    check('apk_equals_verified_export', sha(apk) == sha(P / 'build/android/RailwayWarlords.apk'))
    check('current_runtime_identity', manifest['runtime_source_sha256'] == source_digest()[0])

    with zipfile.ZipFile(source) as archive:
        members = archive.namelist()
        names = set(members)
        check('no_duplicate_or_escaping_entries', len(members) == len(names)
              and all(not n.startswith(('/', '\\')) and '..' not in Path(n).parts for n in names))
        forbidden = ['.toolchain/', '.godot/', '__pycache__/', 'keystore', 'credential',
                     'password', 'sub2_image_gen.py']
        check('no_private_tools_credentials_or_caches',
              not any(token in name.lower() for name in names for token in forbidden))

        def same(path):
            name = path.relative_to(ROOT).as_posix()
            return name in names and member_sha(archive, name) == sha(path)

        runtime = [P / 'project.godot', P / 'export_presets.cfg']
        for folder in ['app', 'content', 'domain', 'ai', 'presentation', 'persistence', 'audio']:
            runtime.extend(path for path in (P / folder).rglob('*')
                           if path.is_file() and path.suffix in ['.gd', '.tscn', '.json'])
        runtime.extend((P / 'schemas').glob('*.json'))
        runtime.extend(path for path in (P / 'assets').rglob('*') if path.is_file()
                       and path.suffix in ['.png', '.wav', '.otf', '.ttf', '.json', '.txt',
                                           '.tres', '.gdshader', '.import'])
        restored = hashlib.sha256()
        for path in sorted(runtime):
            name = path.relative_to(ROOT).as_posix()
            check('runtime_bytes:' + path.relative_to(P).as_posix(), same(path))
            if name in names:
                restored.update(path.relative_to(P).as_posix().encode())
                restored.update(archive.read(name))
        check('runtime_identity_reconstructed_from_source_zip',
              restored.hexdigest() == manifest['runtime_source_sha256'])

        assets = read(P / 'assets/manifest.json')['assets']
        for item in assets:
            check('raster_source:' + item['id'], same(ROOT / item['source_file'])
                  and same(ROOT / item['prompt_file']) and same(P / item['engine_path'].removeprefix('res://'))
                  and sha(ROOT / item['source_file']) == item['source_sha256'])
            for index, previous in enumerate(item.get('revision_history', [])):
                paths = [ROOT / previous[key] for key in ['source_file', 'prompt_file'] if previous.get(key)]
                check('raster_revision:' + item['id'] + ':' + str(index), bool(paths) and all(same(path) for path in paths))
        for row in manifest['current_reports'] + manifest['native_captures']:
            path = P / row['file']
            check('evidence:' + row['file'], same(path) and sha(path) == row['sha256'])

        dem = list((ROOT / 'design/geodata/terrain_tiles').glob('*.tif'))
        continental=read(ROOT/'design/geodata/asia_relief_dem/samples_v1.json')
        check('all_original_numeric_dem_tiles_preserved', len(dem) >= 409 and all(same(path) for path in dem), count=len(dem))
        check('continental_dem_sources_and_samples_preserved',len(continental['tiles'])==54 and same(ROOT/'design/geodata/asia_relief_dem/samples_v1.json') and all(same(ROOT/row['file']) for row in continental['tiles']))
        geography=read(ROOT/'design/geodata/surface_detail_sources/sources.json')
        check('original_material_and_river_data_and_licenses_preserved',
              all(same(ROOT/row['file']) and sha(ROOT/row['file'])==row['sha256'] for row in geography['records'])
              and same(ROOT/'design/geodata/surface_detail_sources/sources.json')
              and same(ROOT/'design/geodata/asia_relief_dem/asia_strategic_before_dem.json'))
        physical_audit=read(P/'reports/surface_geography_audit.json')
        check('independent_physical_geography_audit_is_included',physical_audit['passed']
              and physical_audit['includes_fine_hydrography'] and same(P/'reports/surface_geography_audit.json'))
        check('independent_map_expansion_is_present',manifest['additional_independent_map_sources']==796 and manifest['total_map_sources']==870 and manifest['current_native_capacity_rerun'])
        for relative in ['output/imagegen/15_warlord_railways_full_gameplay.png',
                         'output/imagegen/prompts/15_warlord_railways_full_gameplay.txt',
                         'output/research/european_war_6/sources.json',
                         'output/imagegen/warlord/ew6_v025/full_gameplay/r002/source.png',
                         'output/imagegen/warlord/ew6_v025/full_gameplay/r002/prompt.txt']:
            check('design_reference:' + relative, same(ROOT / relative))

        missing = []
        link_count = 0
        for name in sorted(n for n in names if n.startswith('game/railway_warlords/docs/') and n.endswith('.md')):
            for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', archive.read(name).decode('utf-8')):
                target = target.strip('<>').split('#', 1)[0]
                if not target or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target):
                    continue
                resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), target))
                link_count += 1
                if resolved not in names and not any(n.startswith(resolved.rstrip('/') + '/') for n in names):
                    missing.append(dict(document=name, target=target))
        check('program_document_links_resolve_inside_source_zip', not missing, links=link_count, missing=missing)

    report = dict(version=current_version(), passed=all(row['passed'] for row in checks), checks=checks,
                  content_hash=manifest['content_hash'], runtime_source_sha256=manifest['runtime_source_sha256'],
                  formal_release_ready=False, physical_android_device_tested=False,
                  complete_art_release_approved=False, ew6_visual_parity_claimed=False)
    (out / '交付复核.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(version=report['version'], passed=report['passed'], checks=len(checks),
                          failures=[row['name'] for row in checks if not row['passed']])))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
