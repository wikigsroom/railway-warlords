"""Check batch hash equivalence, including same-metadata content changes."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time

from build_release import ROOT, current_version
import regression_dependencies as deps
from run_validation import CHECKS


def main():
    checks = []

    def check(ok, label):
        checks.append(dict(name=label, passed=bool(ok)))
        if not ok:
            raise AssertionError(label)

    saved_root, saved_dependencies = deps.P, deps.dependencies
    fixture_root = ROOT / 'output/regression_hash_batch'
    fixture_root.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix='equivalence-', dir=fixture_root) as temp:
            deps.P = Path(temp)
            values = {
                'ai/a.gd': b'branch A\x00',
                'app/main.gd': b'branch B\r\n',
                'assets/shared.png': bytes(range(256)) * 8193,
                'content/史料.json': '{"name":"史料"}\n'.encode(),
                'tests/one.gd': b'one',
                'tests/two.gd': b'two',
            }
            for name, value in values.items():
                path = deps.P / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(value)
            paths = {
                'first': sorted(deps.P / name for name in values if name != 'tests/two.gd'),
                'second': sorted(deps.P / name for name in values if name not in {'ai/a.gd', 'tests/one.gd'}),
                'third': sorted(deps.P / name for name in values if name.startswith(('assets/', 'content/'))),
            }
            deps.dependencies = lambda name: paths[name]
            before = deps.identities(paths)
            check(all(before[name] == deps.identity(name) for name in paths),
                  'branched_sorted_subsets_match_legacy_paths_bytes_and_mtime')
            shared = deps.P / 'assets/shared.png'
            metadata = shared.stat()
            payload = shared.read_bytes()
            shared.write_bytes(bytes([payload[0] ^ 1]) + payload[1:])
            os.utime(shared, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
            after = deps.identities(paths)
            check(all(after[name][0] != before[name][0] for name in paths)
                  and all(after[name] == deps.identity(name) for name in paths),
                  'same_size_same_mtime_byte_change_is_detected_without_cached_digests')
            check(deps.identities([]) == {}, 'empty_batch')
            missing = deps.P / 'assets/missing.png'
            paths['missing'] = [missing]
            rejected = False
            try:
                deps.identities(['missing'])
            except FileNotFoundError:
                rejected = True
            check(rejected, 'missing_dependency_rejected')
    finally:
        deps.P, deps.dependencies = saved_root, saved_dependencies
    started = time.monotonic()
    actual = deps.identities(CHECKS)
    check(set(actual) == set(CHECKS), 'all_native_regression_groups_are_hashed')
    # This is the unchanged, independent pre-batch implementation on actual
    # media/content/script bytes, rather than a comparison with stored receipts.
    check(actual['commander_roster_test'] == deps.identity('commander_roster_test'),
          'actual_commander_closure_matches_unchanged_legacy_identity')
    report = dict(passed=True, game_version=current_version(),
        created_at_utc=datetime.now(timezone.utc).isoformat(), checks=checks,
        algorithm='Identical sorted relative-path UTF-8 bytes plus raw file bytes; independent SHA-256 states per check.',
        persistent_hash_cache=False, metadata_used_instead_of_bytes=False,
        runtime_changes=False, elapsed_actual_seconds=round(time.monotonic() - started, 3),
        module_sha256=hashlib.sha256(Path(deps.__file__).read_bytes()).hexdigest(),
        actual_dependency_identities={name: value[0] for name, value in actual.items()})
    out = saved_root / 'reports/regression_hash_batch_equivalence.json'
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(passed=True, checks=len(checks), groups=len(actual), report=str(out)), ensure_ascii=True))


if __name__ == '__main__':
    main()
