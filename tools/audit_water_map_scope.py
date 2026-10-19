"""Bind the water/grid revision to unchanged delivered geography and originals."""
from datetime import datetime, timezone
import hashlib
import json
import subprocess
from build_release import P, current_version, source_digest
from package_delivery import read, sha, require

BASELINE = '4d619a9'


def git_bytes(relative):
    return subprocess.check_output(['git', 'show', BASELINE + ':' + relative], cwd=P)


def main():
    tree = subprocess.check_output(['git', 'ls-tree', '-r', '-z', BASELINE, '--',
        'content', 'presentation/data', 'domain', 'ai', 'persistence'], cwd=P)
    records = []
    for entry in tree.split(b'\0'):
        if not entry:
            continue
        header, name = entry.split(b'\t', 1)
        relative = name.decode('utf-8')
        if not relative.endswith(('.json', '.gd', '.tscn')):
            continue
        data = (P / relative).read_bytes()
        expected = header.split()[2].decode('ascii')
        if relative == 'content/content_registry.gd':
            old = git_bytes(relative)
            require(data == old.replace(b'const APP_VERSION="0.2.26"', b'const APP_VERSION="0.2.27"'),
                    'Only the application version may change in the content registry')
            continue
        actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        records.append(dict(file=relative, preserved=actual == expected, sha256=sha(P / relative)))
    old = json.loads(git_bytes('assets/manifest.json'))['assets']
    current = {row['id']: row for row in read(P / 'assets/manifest.json')['assets']}
    require(len(old) == 1324 and len(current) == 1327, 'Unexpected original source roster')
    preserved = []
    for row in old:
        registered = current[row['id']]
        require(row == registered, 'Existing original registration changed: ' + row['id'])
        require(sha(P / row['engine_path'].removeprefix('res://')) == row['source_sha256'],
                'Existing original PNG changed: ' + row['id'])
        preserved.append(row['id'])
    new_ids = sorted(set(current) - {row['id'] for row in old})
    source_review = {row['id']: row for row in read(P / 'reports/water_material_source_review.json')['images']}
    require(new_ids == sorted('tile_water_' + kind + '_v0227' for kind in ['sea', 'river', 'inland']),
            'Only the reviewed independent water sources may be added')
    water = []
    for asset_id in new_ids:
        row = current[asset_id]
        image = P / row['engine_path'].removeprefix('res://')
        prompt = P / 'docs/asset-prompts' / (asset_id + '.txt')
        imported = image.with_suffix('.png.import').read_text(encoding='utf-8')
        require(row['source_kind'] == 'sub2_image_gen' and row['model'] == 'gpt-image-2.5'
                and row['quality'] == 'high' and not row['image_modified']
                and sha(image) == row['source_sha256'] == source_review[asset_id]['sha256']
                and source_review[asset_id]['viewed_complete_original']
                and sha(prompt) == row['prompt_sha256'] and row['alpha_min'] == 255,
                'Unreviewed, modified or untraceable water original: ' + asset_id)
        require('mipmaps/generate=true' in imported and 'process/size_limit=512' in imported,
                'Runtime water import lacks the specified mip chain: ' + asset_id)
        water.append(dict(id=asset_id, sha256=sha(image), prompt_sha256=sha(prompt),
                          import_sha256=sha(image.with_suffix('.png.import'))))
    require(len({row['sha256'] for row in water}) == 3, 'Water sources must be independently generated')
    require(records and all(row['preserved'] for row in records), 'Source geography, rules or history changed')
    report = dict(passed=True, version=current_version(), runtime_source_sha256=source_digest()[0],
        baseline_commit=BASELINE, created_at_utc=datetime.now(timezone.utc).isoformat(),
        preserved_existing_geography_and_rules=len(records), preserved_existing_originals=len(preserved),
        changed_existing_geography_and_rules=[], old_originals_modified=False,
        new_water_originals=water, source_images_modified=False, manual_compositing=False,
        formal_art_approval=False, historical_water_color_claimed=False,
        files=records, scope='Byte equality to delivered 0.2.26 for existing content JSON, presentation data, domain, AI and persistence. Only APP_VERSION changes in the registry. All 1,324 previous source registrations/PNGs are retained; three immutable Sub2 originals are added.')
    (P / 'reports/water_map_scope_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'files'}), flush=True)


if __name__ == '__main__':
    main()
