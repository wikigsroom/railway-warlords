"""Preserve reviewed native frames before the next current-build capture pass."""
import argparse
import json
import shutil
from build_release import P
from package_delivery import read, sha, require


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--review', default='ui_refinement_native_review.json')
    args = parser.parse_args()
    path = P / 'reports' / args.review
    review = read(path)
    version = review['version']
    count = 0
    remap = {}
    for row in review['viewed_complete_captures']:
        source = P / row['file']
        require(sha(source) == row['sha256'], 'Reviewed source changed: ' + row['file'])
        if row.get('original_capture_path'):
            continue
        relative = source.relative_to(P / 'reports/screenshots')
        target = P / 'reports/screenshots/ui_refinement_native' / ('v' + version.replace('.', '')) / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        meta = source.with_suffix('.json')
        if meta.exists():
            shutil.copyfile(meta, target.with_suffix('.json'))
            require(sha(meta) == sha(target.with_suffix('.json')), 'Capture metadata changed')
        require(sha(target) == row['sha256'], 'Capture bytes changed')
        old = row['file']
        row['original_capture_path'] = old
        row['file'] = target.relative_to(P).as_posix()
        remap[old] = row['file']
        count += 1
    if count:
        path.write_text(json.dumps(review, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    manifest_path = P / 'docs/media/manifest.json'
    manifest = read(manifest_path)
    rows = manifest if isinstance(manifest, list) else manifest.get('captures', manifest.get('files', []))
    # Manifests may keep their media list under images; walk exact source-path
    # values so the schema and every unchanged media PNG remain intact.
    def remap_values(value):
        if isinstance(value, dict):
            return {k: remap_values(v) for k, v in value.items()}
        if isinstance(value, list):
            return [remap_values(v) for v in value]
        return remap.get(value, value) if isinstance(value, str) else value
    if remap:
        manifest_path.write_text(json.dumps(remap_values(manifest), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        for meta in (P / 'docs/media').glob('*.json'):
            if meta == manifest_path:
                continue
            data = read(meta)
            mapped = remap_values(data)
            if data != mapped:
                meta.write_text(json.dumps(mapped, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(passed=True, reviewed_version=version, exact_frames_archived=count)))


if __name__ == '__main__':
    main()
