"""Check this renderer change against the preceding committed preview."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

P = Path(__file__).resolve().parents[2]
BASE = '23995666a6aefaa9fff6b84aa653a0147e5f5e8c'


def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def main():
    tree = subprocess.check_output(['git', 'ls-tree', '-r', '-z', BASE], cwd=P)
    protected = []
    for record in tree.split(b'\0'):
        if not record:
            continue
        meta, raw_path = record.split(b'\t', 1)
        path = raw_path.decode('utf-8')
        roots = ('domain/', 'ai/', 'content/', 'persistence/', 'presentation/data/')
        if path.startswith(roots) and Path(path).suffix in ('.gd', '.json') and path != 'content/content_registry.gd':
            data = (P / path).read_bytes()
            expected = meta.split()[2].decode()
            assert blob(data) == expected, 'Protected source changed: ' + path
            protected.append(dict(file=path, git_blob_sha1=expected))
    registry = subprocess.check_output(['git', 'show', BASE + ':content/content_registry.gd'], cwd=P)
    assert registry.replace(b'APP_VERSION="0.2.31"', b'APP_VERSION="0.2.32"') == (P / 'content/content_registry.gd').read_bytes()
    immutable_files = ['assets/manifest.json', 'docs/asset-provenance/index.json']
    for name in immutable_files:
        assert subprocess.check_output(['git', 'show', BASE + ':' + name], cwd=P) == (P / name).read_bytes()
    assets = json.loads((P / 'assets/manifest.json').read_text(encoding='utf-8'))['assets']
    assert len(assets) == 2509
    report = dict(passed=True, version='0.2.32', base_commit=BASE,
        recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        unchanged_rule_and_geography_files=len(protected), protected_files=protected,
        content_registry_only_change='APP_VERSION 0.2.31 -> 0.2.32',
        asset_manifest_and_provenance_byte_identical=True, registered_rasters=len(assets),
        new_independent_originals=0, active_ground_material_types=20,
        historical_landuse_claimed=False, physical_android_device_tested=False,
        formal_art_approval=False, ew6_parity_claimed=False)
    (P / 'reports/relief_grounding_v0232/scope.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('SCOPE_PASS protected_files=' + str(len(protected)))


if __name__ == '__main__':
    main()
