"""Compare protected production bytes with the published 0.2.35 Git tree."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

P = Path(__file__).resolve().parents[1]
ROOTS = {'app', 'audio', 'assets', 'content', 'domain', 'ai', 'presentation', 'persistence'}
ALLOWED = {'presentation/map_hydrography.gd', 'presentation/map_river_surface.gd', 'presentation/map_view.gd'}


def protected(name):
    return name.split('/')[0] in ROOTS or name in {'project.godot', 'export_presets.cfg'} or name.startswith(('docs/asset-provenance/', 'docs/asset-prompts/'))


def digests(path):
    git = hashlib.sha1(b'blob ' + str(path.stat().st_size).encode('ascii') + b'\0')
    strong = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            git.update(chunk); strong.update(chunk)
    return git.hexdigest(), strong.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', default='bb157c31d2b897c92b99d952253e867f77db7081')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    base = subprocess.check_output(['git', 'rev-parse', args.baseline + '^{commit}'], cwd=P).decode().strip()
    tree = subprocess.check_output(['git', 'rev-parse', base + '^{tree}'], cwd=P).decode().strip()
    raw = subprocess.check_output(['git', 'ls-tree', '-r', '-z', base], cwd=P)
    records, changes, failures = [], [], []
    total_bytes = 0
    for entry in raw.split(b'\0'):
        if not entry:
            continue
        prefix, encoded = entry.split(b'\t', 1)
        mode, kind, oid = prefix.decode('ascii').split()
        name = encoded.decode('utf-8')
        if not protected(name):
            continue
        path = P / name
        if not path.is_file():
            failures.append(dict(file=name, reason='missing_protected_source')); continue
        git, strong = digests(path)
        same = git == oid
        row = dict(file=name, bytes=path.stat().st_size, baseline_blob=oid, current_blob=git,
                   sha256=strong, unchanged=same)
        if not same:
            changes.append(row)
            if name not in ALLOWED:
                failures.append(dict(file=name, reason='unexpected_production_change'))
        else:
            records.append(row)
        total_bytes += path.stat().st_size
    new = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z'], cwd=P)
    new_production = [name.decode('utf-8') for name in new.split(b'\0') if name and protected(name.decode('utf-8'))]
    if new_production:
        failures.append(dict(reason='unexpected_untracked_production_files', files=new_production))
    if {row['file'] for row in changes} != ALLOWED:
        failures.append(dict(reason='different_changed_production_file_set'))
    report = dict(passed=not failures, created_at_utc=datetime.now(timezone.utc).isoformat(),
                  controller_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  baseline_commit=base, baseline_tree=tree, development_only=True,
                  scope='Raw working-file Git blob and SHA256, without clean filters; all registered production roots and original provenance compared with published Git tree.',
                  protected_unchanged_files=len(records), inspected_bytes=total_bytes,
                  unchanged_png_files=sum(row['file'].startswith('assets/') and row['file'].endswith('.png') for row in records),
                  new_production_files=new_production, changed_production_files=changes,
                  historical_accuracy_claimed=False, new_raster_assets=False, new_music=False,
                  shipping_binary_rebuilt=False, physical_android_device_tested=False,
                  failures=failures, unchanged_files=records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ['passed', 'protected_unchanged_files', 'inspected_bytes', 'unchanged_png_files', 'failures']}), flush=True)
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
