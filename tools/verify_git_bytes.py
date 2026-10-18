"""Check that staged Git blobs preserve the tested working files byte for byte."""
import argparse
import hashlib
import json
import subprocess
from build_release import P, current_version, source_digest


def inspect(include_receipt):
    rows = subprocess.check_output(['git', 'ls-files', '--stage', '-z'], cwd=P).split(b'\0')
    errors = []
    checked = 0
    for raw in rows:
        if not raw:
            continue
        header, name = raw.split(b'\t', 1)
        mode, oid, stage = header.split()
        relative = name.decode('utf-8')
        if not include_receipt and relative == 'reports/git_byte_preservation.json':
            continue
        path = P / relative
        if stage != b'0' or mode not in (b'100644', b'100755') or not path.is_file():
            errors.append(dict(file=relative, reason='Unmerged, nonregular or missing staged file'))
            continue
        digest = hashlib.sha1()
        digest.update(b'blob ' + str(path.stat().st_size).encode() + b'\0')
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        checked += 1
        if digest.hexdigest() != oid.decode():
            errors.append(dict(file=relative, reason='Staged blob differs from working bytes'))
    return checked, errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    checked, errors = inspect(include_receipt=args.check_only)
    if not checked:
        errors.append(dict(reason='No staged files'))
    value = dict(passed=not errors, version=current_version(), runtime_source_sha256=source_digest()[0],
                 files_checked=checked, mismatches=errors,
                 scope='Git SHA1 blob identity compared to every staged regular working file. Receipt excluded when writing itself; check-only includes it.',
                 runtime_files_modified=False)
    if not args.check_only:
        (P / 'reports/git_byte_preservation.json').write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(passed=value['passed'], version=value['version'], files_checked=checked,
                          mismatch_count=len(errors), first_mismatches=errors[:12],
                          runtime_source_sha256=value['runtime_source_sha256']), ensure_ascii=True))
    raise SystemExit(0 if value['passed'] else 1)


if __name__ == '__main__':
    main()
