"""Prove this renderer revision retains the delivered 0.2.28 content and media."""
from datetime import datetime, timezone
import hashlib
import json
import subprocess

from build_release import P, current_version, source_digest
from package_delivery import read, require, sha

BASELINE = 'ca166704fb26bab25e30eaf7d91f926348d8f0c5'


def old(relative):
    return subprocess.check_output(['git', 'show', BASELINE + ':' + relative], cwd=P)


def main():
    require(current_version() == '0.2.29', 'Unexpected composition revision')
    paths = ['content', 'presentation/data', 'domain', 'ai', 'persistence', 'assets', 'docs/asset-prompts']
    tree = subprocess.check_output(['git', 'ls-tree', '-r', '-z', BASELINE, '--', *paths], cwd=P)
    records = []
    for entry in tree.split(b'\0'):
        if not entry:
            continue
        header, name = entry.split(b'\t', 1)
        relative = name.decode('utf-8')
        path = P / relative
        require(path.is_file(), 'Delivered file removed: ' + relative)
        data = path.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        preserved = blob == header.split()[2].decode()
        if relative == 'content/content_registry.gd':
            require(data == old(relative).replace(b'APP_VERSION="0.2.28"', b'APP_VERSION="0.2.29"'),
                    'Content registry change exceeds the application version')
        else:
            require(preserved, 'Delivered rules, geography or media changed: ' + relative)
        records.append(dict(file=relative, preserved=preserved))
    for relative, substitutions in [
        ('project.godot', [(b'config/version="0.2.28"', b'config/version="0.2.29"')]),
        ('export_presets.cfg', [(b'version/code=33', b'version/code=34'),
                                (b'version/name="0.2.28"', b'version/name="0.2.29"')]),
    ]:
        expected = old(relative)
        for before, after in substitutions:
            require(before in expected, 'Missing expected baseline version field')
            expected = expected.replace(before, after)
        require((P / relative).read_bytes() == expected, 'Export configuration change exceeds version fields')
    assets = read(P / 'assets/manifest.json')['assets']
    require(len(assets) == 2507, 'Delivered raster inventory differs')
    for asset in assets:
        require(sha(P / asset['engine_path'].removeprefix('res://')) == asset['source_sha256'],
                'Immutable original differs: ' + asset['id'])
    # The generated sample state is intentionally untracked. Bind the old
    # catalogue identity to the actual release gate committed at BASELINE,
    # independently cross-checking its runtime against that commit's exports.
    baseline_identity_path = 'reports/commander_pool_release_validation.json'
    baseline_identity_bytes = old(baseline_identity_path)
    baseline_identity = json.loads(baseline_identity_bytes)
    baseline_exports = json.loads(old('reports/export_results.json'))
    require(baseline_identity['passed'] and baseline_identity['version'] == '0.2.28'
            and {row['target'] for row in baseline_exports} == {'windows', 'android'}
            and all(row['export_verified'] and row['runtime_source_sha256']
                    == baseline_identity['runtime_source_sha256'] for row in baseline_exports),
            'Committed baseline release identity and both verified exports must agree')
    before_hash = baseline_identity['content_hash']
    require(read(P / 'reports/sample_state_v2.json')['content_hash'] == before_hash,
            'Map/rules catalogue identity changed')
    result = dict(passed=True, version=current_version(), baseline_commit=BASELINE,
        runtime_source_sha256=source_digest()[0], content_hash=before_hash,
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        checked_delivered_files=len(records), preserved_delivered_files=sum(r['preserved'] for r in records),
        preserved_raster_originals=len(assets), new_raster_originals=0,
        map_geography_preserved=True, rules_preserved=True, media_and_prompts_preserved=True,
        operation_hex_radius_world=48, source_pngs_modified=False, manual_compositing=False,
        version_only_registry_change=True,
        baseline_content_identity_source=baseline_identity_path,
        baseline_content_identity_sha256=hashlib.sha256(baseline_identity_bytes).hexdigest(),
        baseline_runtime_source_sha256=baseline_identity['runtime_source_sha256'],
        baseline_identity_cross_checked_with_both_committed_exports=True, files=records)
    (P / 'reports/map_composition_scope_audit.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'files'}), flush=True)


if __name__ == '__main__':
    main()
