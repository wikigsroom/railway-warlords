"""Bind the commander expansion to the delivered 0.2.27 geography and artwork."""
from datetime import datetime, timezone
import hashlib
import json
import subprocess
from build_release import P, current_version, source_digest
from package_delivery import read, sha, require

BASELINE = 'ec3701d'
ALLOWED = {
    'content/content_registry.gd', 'content/definitions/catalog.json',
    'content/definitions/generals.json', 'content/history/asia_timeline.json',
    'content/scenarios/campaign_1860_01.json', 'content/scenarios/campaign_1860_02.json',
    'presentation/data/general_lifespans.json', 'presentation/data/general_portraits.json',
    'domain/legion_rules.gd', 'domain/state_builder.gd', 'domain/victory_rules.gd',
}

def main():
    require(current_version() in {'0.2.28', '0.2.29'}, 'Commander audit version differs')
    tree = subprocess.check_output(['git', 'ls-tree', '-r', '-z', BASELINE, '--',
        'content', 'presentation/data', 'domain', 'ai', 'persistence'], cwd=P)
    records = []
    for entry in tree.split(b'\0'):
        if not entry:continue
        header, name = entry.split(b'\t', 1); relative = name.decode('utf-8')
        if not relative.endswith(('.json', '.gd', '.tscn')):continue
        path = P / relative
        require(path.is_file(), 'Delivered file removed: ' + relative)
        data = path.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        records.append(dict(file=relative, preserved=blob == header.split()[2].decode(),
            declared_commander_change=relative in ALLOWED, sha256=sha(path)))
    changed = {r['file'] for r in records if not r['preserved']}
    unexpected = sorted(changed - ALLOWED)
    require(not unexpected, 'Undeclared rules/geography change: ' + ', '.join(unexpected))
    map_files = [r for r in records if r['file'].startswith('content/maps/')]
    require(map_files and all(r['preserved'] for r in map_files), 'Map geography changed')
    old = json.loads(subprocess.check_output(['git', 'show', BASELINE + ':assets/manifest.json'], cwd=P))['assets']
    assets = read(P / 'assets/manifest.json')['assets']; by_id = {r['id']: r for r in assets}
    require(len(old) == 1327, 'Baseline original roster differs')
    for row in old:
        require(by_id.get(row['id']) == row, 'Delivered asset registration changed: ' + row['id'])
        require(sha(P / row['engine_path'].removeprefix('res://')) == row['source_sha256'],
            'Delivered original changed: ' + row['id'])
    additions = [r for r in assets if r['id'] not in {a['id'] for a in old}]
    require(len(additions) == 1180 and all(r['category'] == 'portrait'
        and r['style_version'] == 'warlord_commanders_v0228' for r in additions),
        'Only the 1,180 planned commander portraits may be added')
    geography = read(P / 'reports/coast_detail_geography_audit.json')
    bound = geography['passed'] and not geography['production_compiler_imported'] and all(
        r['map_sha256'] == sha(P / ('content/maps/' + r['map_id'] + '.json')) for r in geography['maps'])
    require(bound, 'Independent original-GIS audit no longer binds to the maps')
    result = dict(passed=True, version=current_version(), runtime_source_sha256=source_digest()[0],
        baseline_commit=BASELINE, created_at_utc=datetime.now(timezone.utc).isoformat(),
        checked_existing_files=len(records), preserved_json_files=sum(r['preserved'] and r['file'].endswith('.json') for r in records),
        declared_changed_files=sorted(changed), unexpected_changed_files=unexpected,
        preserved_map_files=len(map_files), preserved_existing_originals=len(old),
        added_portrait_originals=len(additions), independent_raw_geography_audit_bound=bound,
        old_originals_modified=False, source_images_modified=False, manual_compositing=False,
        complete_historical_orders_of_battle=False, all_qualifying_asian_commanders_covered=False,
        scope='Commander identities, dated deployments, independent side counts, allied capture objectives and two 1860 recipes may change. All delivered maps, GIS meshes, map originals, AI and persistence retain their 0.2.27 bytes. The retained independent GIS audit is a source-binding check, not new historical survey approval.', files=records)
    (P / 'reports/commander_pool_scope_audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k != 'files'}), flush=True)

if __name__ == '__main__':main()
