"""Copy individually viewed shipping viewports verbatim into README media."""
from pathlib import Path
import hashlib
import json
import shutil
from build_release import P, current_version


def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    assert current_version() == '0.2.35'
    root = P / 'reports/urban_hierarchy_v0235'
    maps, shipping, review = [read(root / name) for name in ['composition_shipping01/validation.json', 'shipping01/validation.json', 'visual_review.json']]
    assert maps['passed'] and maps['mode'] == 'verified_export' and shipping['passed']
    assert maps['runtime_source_sha256'] == shipping['runtime_source_sha256'] == review['runtime_source_sha256']
    viewed = {row['path']: row['sha256'] for row in review['actually_viewed_complete_images']}
    assert len(viewed) == 16 and not review['formal_art_approval']
    captures = {row['name']: row for row in maps['captures']}
    captures['home'] = next(row for row in shipping['captures'] if row['path'].endswith('/home.png'))
    manifest_path = P / 'docs/media/manifest.json'; manifest = read(manifest_path)
    for name, stem in dict(home='menu', wuhan='urban-wuhan', wuhan_three_towns='urban-three-towns', ningpu_city='urban-nanjing',
                           ningpu_river='urban-ningpu-river', ningpu_regional='urban-ningpu-regional', coast='urban-coast',
                           wuhan_x30_layout='urban-x30-layout').items():
        row = captures[name]; source, metadata = Path(row.get('image', row.get('path'))), Path(row['metadata'])
        if not source.is_absolute(): source = P / source
        if not metadata.is_absolute(): metadata = P / metadata
        relative = source.relative_to(P).as_posix()
        assert sha(source) == row['sha256'] == viewed[relative] and sha(metadata) == row['metadata_sha256']
        meta = read(metadata)
        assert meta['build_version'] == '0.2.35' and meta['raw_godot_capture'] and meta['qa_save_isolated']
        target = P / 'docs/media' / (stem + '-v0235.png')
        assert not target.exists() and not target.with_suffix('.json').exists()
        shutil.copyfile(source, target); shutil.copyfile(metadata, target.with_suffix('.json'))
        assert sha(target) == sha(source)
        assert not any(row['file'] == target.relative_to(P).as_posix() for row in manifest['screenshots'])
        manifest['screenshots'].append(dict(file=target.relative_to(P).as_posix(), version='0.2.35', native_source=relative,
            sha256=sha(source), metadata=target.with_suffix('.json').relative_to(P).as_posix(),
            byte_identical_to_native_capture=True, physical_android_device_tested=False))
    manifest.update(version='0.2.35', current_map_visual_evidence='reports/urban_hierarchy_v0235/composition_shipping01/validation.json',
                    notice='Whole shipping viewports copied verbatim after individual viewing. Earlier stills and GIFs retain their actual versions. Desktop X30 layout is not physical-phone acceptance.')
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Copied eight whole shipping viewports with identical bytes.', flush=True)


if __name__ == '__main__': main()
