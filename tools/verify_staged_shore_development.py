"""Check staged shore work against native proofs and the full original-byte audit."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess

from verify_repository import PUBLIC_DOCS

P = Path(__file__).resolve().parents[1]
R = P / 'reports/shore_presentation_v0236'
BASE = '6cf1f09ca75e9508ec5ad44274dab6de2187d802'
PRODUCTION = ['presentation/map_coast_band.gd', 'presentation/map_view.gd']


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=P).decode().strip() == BASE
    staged = {}
    for raw in subprocess.check_output(['git', 'ls-files', '--stage', '-z'], cwd=P).split(b'\0'):
        if raw:
            header, name = raw.split(b'\t', 1)
            mode, oid, stage = header.decode().split()
            staged[name.decode('utf-8')] = dict(mode=mode, oid=oid, stage=stage)
    changed = [name.decode('utf-8') for name in subprocess.check_output(
        ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z'], cwd=P).split(b'\0') if name]
    deletions = subprocess.check_output(['git', 'diff', '--cached', '--name-only', '--diff-filter=D', '-z'], cwd=P)
    failures, records = [], []
    if deletions:
        failures.append(dict(reason='unexpected_staged_deletion'))
    patterns = [
        ('private_key', re.compile(r'-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----')),
        ('provider_token', re.compile(r'\b(?:sk-proj-|sk-ant-|gh[pousr]_|github_pat_)[A-Za-z0-9_-]{18,}')),
        ('assigned_secret', re.compile(r'''(?i)(?:api_key|apiKey|token|password|secret)\s*[:=]\s*["'][^"'\n]{16,}["']''')),
    ]
    for name in changed:
        path = P / name; raw = path.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if blob != staged[name]['oid'] or staged[name]['stage'] != '0':
            failures.append(dict(file=name, reason='staged_bytes_differ'))
        if len(raw) >= 100 * 1024 * 1024:
            failures.append(dict(file=name, reason='oversized_blob'))
        if name.startswith('reports/screenshots/') or any(part in {'.godot', 'build', '__pycache__', 'signing', '.toolchain'} for part in path.relative_to(P).parts):
            failures.append(dict(file=name, reason='unrelated_private_or_generated_path'))
        if path.suffix in {'.py', '.gd', '.json', '.md', '.cfg', '.txt'}:
            text = raw.decode('utf-8')
            for kind, pattern in patterns:
                for match in pattern.finditer(text):
                    failures.append(dict(file=name, reason=kind, line=text[:match.start()].count('\n') + 1))
        records.append(dict(file=name, bytes=len(raw), blob=blob, sha256=hashlib.sha256(raw).hexdigest()))
    links = 0; paths = {(P / name).resolve() for name in staged}
    for name in PUBLIC_DOCS:
        path = P / name
        for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if link.startswith(('https:', 'http:', 'mailto:')):
                continue
            relative, _, anchor = link.strip('<>').partition('#')
            target = (path.parent / relative).resolve() if relative else path.resolve()
            links += 1
            if not target.exists() or (target.is_file() and target not in paths):
                failures.append(dict(file=name, reason='missing_or_unstaged_link', link=link))
            elif anchor and target.suffix == '.md' and f'id="{anchor}"' not in target.read_text(encoding='utf-8'):
                failures.append(dict(file=name, reason='missing_anchor', link=link))
    proof_paths = [R / 'revised' / (case + '06') / 'command.json'
                   for case in ['shore_rules', 'osaka', 'shanhaiguan', 'tianjin', 'qingdao']]
    proof_hashes = []; current_sha = {}
    for path in proof_paths:
        command = read(path)
        result = read(path.with_name('result.json'))
        if not result['passed'] or not result['dependencies_unchanged']:
            failures.append(dict(file=path.relative_to(P).as_posix(), reason='native_proof_not_passed'))
        for name, checksum in command['code_and_data_sha256'].items():
            if name not in current_sha:
                current_sha[name] = sha(P / name)
            if current_sha[name] != checksum:
                failures.append(dict(file=name, reason='production_differs_from_native_proof'))
        proof_hashes.append(dict(file=path.relative_to(P).as_posix(), sha256=sha(path)))
    scope_path = R / 'protected_scope06.json'; scope = read(scope_path)
    if not scope['passed'] or scope['baseline_commit'] != BASE:
        failures.append(dict(reason='protected_byte_audit_not_passed'))
    if {row['file'] for row in scope['changed_production_files']} != set(PRODUCTION):
        failures.append(dict(reason='unexpected_production_file_set'))
    for row in scope['changed_production_files']:
        if sha(P / row['file']) != row['sha256']:
            failures.append(dict(file=row['file'], reason='renderer_differs_from_full_scope_audit'))
    report = dict(passed=not failures, created_at_utc=datetime.now(timezone.utc).isoformat(),
                  controller_sha256=sha(Path(__file__)), baseline_commit=BASE,
                  scope='Changed staged bytes, public links, five complete native proof dependency lists and the full original-byte audit.',
                  changed_staged_files_checked=len(records), public_documents=len(PUBLIC_DOCS), local_links_checked=links,
                  native_source_proofs=proof_hashes, protected_scope_sha256=sha(scope_path),
                  development_only=True, shipping_binary_rebuilt=False, formal_art_approval=False,
                  physical_android_device_tested=False, failures=failures, files=records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ['passed', 'changed_staged_files_checked', 'public_documents', 'local_links_checked', 'failures']}), flush=True)
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
