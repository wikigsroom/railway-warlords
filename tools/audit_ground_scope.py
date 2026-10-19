"""Compare retained rule/geographical JSON with the delivered 0.2.24 commit."""
import hashlib
import json
import subprocess
from build_release import P, current_version, source_digest

BASELINE = 'ceba74adb7d97fe04ab5d3dc72d5a5004da69921'


def main():
    tree = subprocess.check_output(['git', 'ls-tree', '-r', '-z', BASELINE, '--',
                                    'content', 'presentation/data'], cwd=P)
    rows = []
    for entry in tree.split(b'\0'):
        if not entry:
            continue
        header, name = entry.split(b'\t', 1)
        relative = name.decode('utf-8')
        if not relative.endswith('.json') or relative == 'presentation/data/ground_macro_catalog.json':
            continue
        path = P / relative
        original = header.split()[2].decode('ascii')
        data = path.read_bytes()
        actual = hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()
        rows.append(dict(file=relative, baseline_git_blob=original, current_git_blob=actual,
                         preserved=original == actual, sha256=hashlib.sha256(data).hexdigest()))
    changed = [row['file'] for row in rows if not row['preserved']]
    value = dict(passed=bool(rows) and not changed, version=current_version(), baseline_commit=BASELINE,
                 runtime_source_sha256=source_digest()[0], verified_preserved_json_files=len(rows),
                 changed_files=changed, files=rows,
                 scope='All pre-existing rule, scenario and presentation JSON except the intentionally replaced ground-source catalog; complete bytes compared with delivered 0.2.24 Git blobs. New image plan is additional, not a rewritten geography source.')
    (P / 'reports/ground_atlas_scope_audit.json').write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(passed=value['passed'], verified=len(rows), changed=changed)), flush=True)
    raise SystemExit(0 if value['passed'] else 1)


if __name__ == '__main__':
    main()
