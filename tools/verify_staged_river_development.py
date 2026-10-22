"""Check final staged bytes and links without rehashing unchanged 5GB originals."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
from verify_repository import PUBLIC_DOCS

P = Path(__file__).resolve().parents[1]
R = P / 'reports/river_cartography_v0236'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    base = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=P).decode().strip()
    assert base == 'bb157c31d2b897c92b99d952253e867f77db7081'
    staged = {}
    for raw in subprocess.check_output(['git', 'ls-files', '--stage', '-z'], cwd=P).split(b'\0'):
        if raw:
            header, name = raw.split(b'\t', 1)
            mode, oid, stage = header.decode().split()
            staged[name.decode('utf-8')] = dict(mode=mode, oid=oid, stage=stage)
    changed = [name.decode('utf-8') for name in subprocess.check_output(
        ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z'], cwd=P).split(b'\0') if name]
    patterns = [
        ('private_key', re.compile(r'-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----')),
        ('provider_token', re.compile(r'\b(?:sk-proj-|sk-ant-|gh[pousr]_|github_pat_)[A-Za-z0-9_-]{18,}')),
        ('assigned_secret', re.compile(r'''(?i)(?:api_key|apiKey|token|password|secret)\s*[:=]\s*["'][^"'\n]{16,}["']''')),
    ]
    failures, records = [], []
    for name in changed:
        path = P / name
        raw = path.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if blob != staged[name]['oid'] or staged[name]['stage'] != '0':
            failures.append(dict(file=name, reason='staged_bytes_differ'))
        if len(raw) >= 100 * 1024 * 1024:
            failures.append(dict(file=name, reason='oversized_blob'))
        if any(part in {'.godot', 'build', '__pycache__', 'signing', '.toolchain'} for part in path.relative_to(P).parts):
            failures.append(dict(file=name, reason='private_or_generated_path'))
        if path.suffix in {'.py', '.gd', '.json', '.md', '.cfg', '.txt'}:
            text = raw.decode('utf-8')
            for kind, pattern in patterns:
                for match in pattern.finditer(text):
                    failures.append(dict(file=name, reason=kind, line=text[:match.start()].count('\n') + 1))
        records.append(dict(file=name, bytes=len(raw), blob=blob, sha256=hashlib.sha256(raw).hexdigest()))
    links = 0
    paths = {(P / name).resolve() for name in staged}
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
    command = json.loads((R / 'revised/geometry03/command.json').read_bytes())
    production_matches = True
    for name in ['presentation/map_hydrography.gd', 'presentation/map_river_surface.gd', 'presentation/map_view.gd']:
        if hashlib.sha256((P / name).read_bytes()).hexdigest() != command['code_and_data_sha256'][name]:
            production_matches = False
            failures.append(dict(file=name, reason='production_differs_from_native_tested_source'))
    report = dict(passed=not failures, created_at_utc=datetime.now(timezone.utc).isoformat(),
                  controller_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), baseline_commit=base,
                  scope='Every changed staged file compared with raw working bytes; all public links checked. Unchanged originals already audited separately.',
                  changed_staged_files_checked=len(records), public_documents=len(PUBLIC_DOCS), local_links_checked=links,
                  source_geometry_proof_matches_current_renderers=production_matches, development_only=True,
                  shipping_binary_rebuilt=False, physical_android_device_tested=False,
                  failures=failures, files=records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ['passed', 'changed_staged_files_checked', 'public_documents', 'local_links_checked', 'failures']}), flush=True)
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
