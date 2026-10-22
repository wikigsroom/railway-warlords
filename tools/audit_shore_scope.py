"""Check shore development against the preceding committed river revision."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

from audit_river_scope import protected, digests

P = Path(__file__).resolve().parents[1]
ALLOWED = {'presentation/map_coast_band.gd', 'presentation/map_view.gd'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', default='6cf1f09ca75e9508ec5ad44274dab6de2187d802')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    base = subprocess.check_output(['git', 'rev-parse', args.baseline + '^{commit}'], cwd=P).decode().strip()
    tree = subprocess.check_output(['git', 'rev-parse', base + '^{tree}'], cwd=P).decode().strip()
    raw = subprocess.check_output(['git', 'ls-tree', '-r', '-z', base], cwd=P)
    records, changes, failures, baseline_names = [], [], [], set()
    total_bytes = 0
    for entry in raw.split(b'\0'):
        if not entry:
            continue
        prefix, encoded = entry.split(b'\t', 1)
        _, _, oid = prefix.decode('ascii').split()
        name = encoded.decode('utf-8')
        baseline_names.add(name)
        if not protected(name):
            continue
        path = P / name
        if not path.is_file():
            failures.append(dict(file=name, reason='missing_protected_source'))
            continue
        blob, strong = digests(path)
        same = blob == oid
        row = dict(file=name, bytes=path.stat().st_size, baseline_blob=oid, current_blob=blob,
                   sha256=strong, unchanged=same)
        if same:
            records.append(row)
        else:
            changes.append(row)
            if name not in ALLOWED:
                failures.append(dict(file=name, reason='unexpected_production_change'))
        total_bytes += path.stat().st_size
    current = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=P)
    new_production = sorted({name.decode('utf-8') for name in current.split(b'\0')
                             if name and name.decode('utf-8') not in baseline_names and protected(name.decode('utf-8'))})
    if new_production:
        failures.append(dict(reason='unexpected_new_production_files', files=new_production))
    if {row['file'] for row in changes} != ALLOWED:
        failures.append(dict(reason='different_changed_production_file_set'))
    report = dict(passed=not failures, created_at_utc=datetime.now(timezone.utc).isoformat(),
                  controller_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  helper_sha256=hashlib.sha256((P / 'tools/audit_river_scope.py').read_bytes()).hexdigest(),
                  baseline_commit=base, baseline_tree=tree, development_only=True,
                  scope='Raw Git blob and SHA256 checks of registered production roots and original provenance against the preceding river development commit.',
                  protected_unchanged_files=len(records), inspected_bytes=total_bytes,
                  unchanged_png_files=sum(row['file'].startswith('assets/') and row['file'].endswith('.png') for row in records),
                  new_production_files=new_production, changed_production_files=changes,
                  original_geography_modified=False, historical_accuracy_claimed=False,
                  new_raster_assets=False, new_music=False, shipping_binary_rebuilt=False,
                  physical_android_device_tested=False, failures=failures, unchanged_files=records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ['passed', 'protected_unchanged_files', 'inspected_bytes', 'unchanged_png_files', 'failures']}), flush=True)
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
