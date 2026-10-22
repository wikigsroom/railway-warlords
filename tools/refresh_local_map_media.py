"""Publish verbatim, individually viewed shipping viewport selections."""
from pathlib import Path
import hashlib
import json
import shutil

from build_release import P, current_version


def read(path):
    return Path(path).read_text(encoding='utf-8')


def data(path):
    return json.loads(read(path))


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    assert current_version() == '0.2.34'
    root = P / 'reports/local_map_refinement'
    maps_root = P / 'reports/screenshots/local_map_refinement/v0234/verified_export_01'
    maps, shipping = data(maps_root / 'validation.json'), data(root / 'shipping_01/validation.json')
    review = data(root / 'visual_review.json')
    assert maps['passed'] and maps['mode'] == 'verified_export' and len(maps['checks']) == 106
    assert shipping['passed'] and shipping['gpu_checks'] == 48 and shipping['ui_smoke_passed']
    assert maps['runtime_source_sha256'] == shipping['runtime_source_sha256'] == review['runtime_source_sha256']
    viewed = {row['path']: row['sha256'] for row in review['actually_viewed_complete_images']}
    assert len(viewed) == 16 and not review['formal_art_approval']
    captures = {row['name']: row for row in maps['captures']}
    captures['home'] = next(row for row in shipping['captures'] if row['path'].endswith('/home.png'))
    manifest_path = P / 'docs/media/manifest.json'
    manifest = data(manifest_path)
    for row in manifest['screenshots']:
        if 'version' not in row:
            assert row.get('metadata'), 'Retained screenshots need their actual version.'
            row['version'] = data(P / row['metadata'])['build_version']
    selections = dict(home='menu', wuhan='local-wuhan', wuhan_three_towns='local-wuhan-three-towns',
                      ningpu_city='local-nanjing', ningpu_river='local-ningpu-river',
                      ningpu_regional='local-ningpu-regional', coast='local-coast',
                      wuhan_x30_layout='local-wuhan-x30-layout')
    for name, stem in selections.items():
        row = captures[name]
        source = Path(row.get('image', row.get('path')))
        metadata = Path(row['metadata'])
        if not source.is_absolute():
            source = P / source
        if not metadata.is_absolute():
            metadata = P / metadata
        relative = source.relative_to(P).as_posix()
        assert sha(source) == row['sha256'] == viewed[relative]
        assert sha(metadata) == row['metadata_sha256']
        meta = data(metadata)
        assert meta['build_version'] == '0.2.34' and meta['raw_godot_capture'] and meta['qa_save_isolated']
        target = P / 'docs/media' / (stem + '-v0234.png')
        assert not target.exists() and not target.with_suffix('.json').exists()
        shutil.copyfile(source, target)
        shutil.copyfile(metadata, target.with_suffix('.json'))
        assert sha(target) == sha(source)
        assert not any(row['file'] == target.relative_to(P).as_posix() for row in manifest['screenshots'])
        manifest['screenshots'].append(dict(file=target.relative_to(P).as_posix(),
            version='0.2.34', native_source=relative, sha256=sha(source),
            metadata=target.with_suffix('.json').relative_to(P).as_posix(),
            byte_identical_to_native_capture=True, physical_android_device_tested=False))
    manifest.update(version='0.2.34', current_local_map_evidence=maps_root.relative_to(P).as_posix()+'/validation.json',
                    notice='Whole native shipping viewports copied verbatim; older stills and GIFs retain their real versions. Desktop X30 dimensions are not physical phone acceptance.')
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Copied eight individually viewed whole shipping viewports without modifying image bytes.', flush=True)


if __name__ == '__main__':
    main()
