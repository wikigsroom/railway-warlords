"""Bind the visual preview to unchanged published history, rules and originals."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess

P = Path(__file__).resolve().parents[1]
BASELINE = '5fdd2de0348650307aec304d3175d334f62da610'
OUT = P / 'reports/urban_hierarchy_v0235/scope.json'


def old(name):
    return subprocess.check_output(['git', 'show', BASELINE + ':' + name], cwd=P)


def main():
    assert not OUT.exists(), 'Preserve the original scope receipt.'
    checks = []
    def check(name, passed): checks.append(dict(name=name, passed=bool(passed)))
    before = json.loads(old('assets/manifest.json'))['assets']
    after = json.loads((P / 'assets/manifest.json').read_bytes())['assets']
    check('all_2509_published_original_records_and_order_preserved', len(before) == 2509 and after[:len(before)] == before)
    check('exactly_twelve_new_independent_originals', len(after) == 2521 and len({row['source_sha256'] for row in after}) == 2521)
    bank_before = json.loads(old('presentation/data/map_bank_visuals.json'))
    bank_after = json.loads((P / 'presentation/data/map_bank_visuals.json').read_bytes())
    check('all_796_published_bank_records_preserved', len(bank_before['records']) == 796 and all(bank_after['records'].get(key) == value for key, value in bank_before['records'].items()))
    protected = []
    for folder in ['content', 'domain', 'ai', 'persistence', 'audio', 'schemas']:
        names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASELINE, '--', folder], cwd=P).decode('utf-8').splitlines()
        for name in names:
            if Path(name).suffix not in ['.json', '.gd', '.gdshader']: continue
            previous = old(name)
            if name == 'content/content_registry.gd':
                previous = previous.replace(b'const APP_VERSION="0.2.34"', b'const APP_VERSION="0.2.35"')
            path = P / name
            passed = path.exists() and path.read_bytes() == previous
            check('published_rules_and_history_preserved:' + name, passed)
            protected.append(dict(file=name, sha256=hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None, only_app_version_allowed=name == 'content/content_registry.gd'))
    current = {row['id']: row for row in after}
    for row in before:
        path = P / current[row['id']]['engine_path'].removeprefix('res://')
        with path.open('rb') as stream: actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        check('published_original_bytes_preserved:' + row['id'], actual == row['source_sha256'])
    result = dict(passed=all(row['passed'] for row in checks), baseline_published_commit=BASELINE,
                  created_at_utc=datetime.now(timezone.utc).isoformat(), driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  prior_rasters=2509, current_rasters=2521, new_originals=12,
                  historical_or_rule_changes=False, existing_originals_modified=False, new_music_generated=False,
                  future_music_route='music-gen-remote-YuE2_RTX3080_instrumental',
                  checks=checks, failures=[row['name'] for row in checks if not row['passed']], protected_sources=protected)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(passed=result['passed'], checks=len(checks), failures=result['failures']), ensure_ascii=False), flush=True)
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
