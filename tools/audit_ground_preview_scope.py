"""Bind the ground preview to retained rules, originals and export sources."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess

P = Path(__file__).resolve().parents[1]
R = P / 'reports/geographic_ground_v0237'
PARENT = '1ce5f399ae7f8d5f6176c8b6f2ce6138bef4b93b'
NEW_DATA = 'presentation/data/asia_ground_regions.json'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=P)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    out = R / 'final_scope01.json'
    if out.exists():
        raise FileExistsError(out)
    prefixes = ('content/', 'domain/', 'ai/', 'persistence/', 'assets/', 'presentation/data/')
    baseline = git('ls-tree', '-r', '--name-only', PARENT).decode('utf-8').splitlines()
    protected = {name for name in baseline if name.startswith(prefixes)}
    changed = git('diff', '--name-only', PARENT, '--', *[p.rstrip('/') for p in prefixes]).decode('utf-8').splitlines()
    changed_existing = sorted(set(changed) & protected)
    assert changed_existing == ['content/content_registry.gd'], changed_existing
    old = git('show', PARENT + ':content/content_registry.gd')
    assert (P / 'content/content_registry.gd').read_bytes() == old.replace(
        b'const APP_VERSION="0.2.36"', b'const APP_VERSION="0.2.37"', 1)
    assert NEW_DATA not in baseline
    assert sha(P / NEW_DATA) == '50a866840af44c12cd80f5f9cff8099c816f7295a1ac907e0d95757355bd53cd'
    seal = json.loads((R / 'preview_stage01.json').read_bytes())
    export = json.loads((R / 'preview_export01.json').read_bytes())
    assert seal['passed'] and export['passed']
    assert export['stage_copy_receipt_sha256'] == sha(R / 'preview_stage01.json')
    seal_time = datetime.fromisoformat(seal['created_at_utc']).timestamp()
    originals = json.loads((P / 'assets/manifest.json').read_bytes())['assets']
    assert len(originals) == 2521
    for entry in originals:
        relative = entry['engine_path'].removeprefix('res://')
        assert seal['file_sha256'][relative] == entry['source_sha256']
        assert export['runtime_file_sha256'][relative] == entry['source_sha256']
        assert (P / relative).stat().st_mtime <= seal_time
    assert not git('ls-files', '--others', '--exclude-standard', '--', 'assets').strip()
    files = [P / 'project.godot', P / 'export_presets.cfg']
    for folder in ['app', 'content', 'domain', 'ai', 'presentation', 'persistence', 'audio', 'schemas']:
        files.extend(f for f in (P / folder).rglob('*') if f.is_file() and f.suffix in ['.gd', '.tscn', '.json', '.gdshader'])
    code = {f.relative_to(P).as_posix(): sha(f) for f in sorted(files)}
    assert all(export['runtime_file_sha256'][name] == checksum for name, checksum in code.items())
    result = dict(passed=True, version='0.2.37', created_at_utc=datetime.now(timezone.utc).isoformat(),
                  controller_sha256=sha(__file__), parent_commit=PARENT,
                  protected_existing_files=len(protected), protected_existing_changes=changed_existing,
                  protected_change='APP_VERSION only; pre-existing rules, maps, originals and presentation JSON retained',
                  additional_numeric_data=NEW_DATA, additional_numeric_data_sha256=sha(P / NEW_DATA),
                  raster_originals_verified_against_complete_copy_and_export_seals=len(originals),
                  art_verification_method='Complete authority/copy SHA256 seal, source manifest SHA256, no tracked asset diff, no new asset files, and unchanged original mtimes after seal',
                  fresh_runtime_code_and_data_sha256=code,
                  export_receipt_sha256=sha(R / 'preview_export01.json'),
                  runtime_source_merkle_sha256=export['runtime_source_merkle_sha256'],
                  new_raster_originals=0, new_music=0, terrain_rule_hex_changed=False,
                  historical_content_changed=False, historical_content_correctness_certified=False,
                  formal_art_approval=False, physical_android_device_tested=False)
    with out.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'fresh_runtime_code_and_data_sha256'}), flush=True)


if __name__ == '__main__':
    main()
