"""Audit current public UTF-8 display text without rewriting immutable history."""
import json
import subprocess
from build_release import P, ROOT, current_version, source_digest


def main():
    former_name = ''.join(map(chr, [27611, 27901, 19996]))
    raw = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=P)
    public = {P / name.decode('utf-8') for name in raw.split(b'\0') if name}
    extensions = {'.md', '.gd', '.py', '.json', '.txt', '.cfg', '.tscn', '.csv', '.toml', '.html', '.xml'}
    public = sorted(p for p in public if p.is_file() and p.suffix.lower() in extensions)
    design = sorted(p for p in (ROOT / 'design').rglob('*') if p.is_file() and p.suffix.lower() in extensions)
    hits = []
    for path in public + design:
        if former_name in path.read_text(encoding='utf-8-sig', errors='replace'):
            hits.append(path.relative_to(ROOT).as_posix())
    value = dict(passed=not hits, version=current_version(), runtime_source_sha256=source_digest()[0],
                 legacy_display_name_plaintext_files=hits, public_text_files_scanned=len(public),
                 selected_design_text_files_scanned=len(design),
                 scope='Current public UTF-8 source, documentation and selected design. Immutable old source bytes remain reversibly encoded; old Git history and archived releases are retained.')
    (P / 'reports/daily_age_text_audit.json').write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(value, ensure_ascii=True))
    raise SystemExit(0 if value['passed'] else 1)


if __name__ == '__main__':
    main()
