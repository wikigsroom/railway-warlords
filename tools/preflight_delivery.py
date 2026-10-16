"""Check public document links and existing immutable release archives."""
from pathlib import Path
import hashlib
import json
import re
from urllib.parse import unquote
from build_release import current_version

P = Path(__file__).resolve().parents[1]
ROOT = P.parents[1]


def digest(path):
    sha = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            sha.update(block)
    return sha.hexdigest()


def main():
    documents = [ROOT/'README.md', P/'README.md', P/'README.en.md', P/'LICENSE-NOTICE.md', *sorted((P/'docs').glob('*.md'))]
    missing = []
    checked = 0
    for document in documents:
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', document.read_text(encoding='utf-8')):
            target = target.strip('<>').split('#', 1)[0]
            if not target or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target):
                continue
            checked += 1
            if not (document.parent/unquote(target)).exists():
                missing.append({'document': str(document.relative_to(ROOT)), 'target': target})
    public = []
    for folder in ('app','content','domain','ai','persistence','presentation','audio','schemas','tests','tools','docs'):
        public.extend(path for path in (P/folder).rglob('*') if path.is_file() and path.suffix in {'.gd','.py','.json','.md','.cfg','.tscn'})
    public.extend([P/'project.godot',P/'export_presets.cfg',P/'README.md',ROOT/'README.md'])
    patterns = re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b|\bAIza[A-Za-z0-9_-]{30,}\b')
    credentials = [str(path.relative_to(ROOT)) for path in public if patterns.search(path.read_text(encoding='utf-8'))]
    preserved = []
    for folder in sorted((ROOT/'output/releases').glob('railway-warlords-*')):
        version=folder.name.removeprefix('railway-warlords-')
        if version==current_version() or not (folder/'release_manifest.json').is_file():continue
        manifest = json.loads((folder/'release_manifest.json').read_text(encoding='utf-8'))
        for item in manifest['files']:
            path = folder/item['name'];actual=digest(path) if path.is_file() else None
            preserved.append({'version':version,'name':item['name'],'sha256':actual,'matches':actual==item['sha256']})
    report = {'local_doc_links_checked':checked,'missing_local_doc_links':missing,'public_text_files_scanned':len(public),'credential_patterns_detected_files':credentials,'preserved_releases':preserved,'previous_releases_preserved':all(item['matches'] for item in preserved)}
    report['passed'] = not missing and not credentials and report['previous_releases_preserved']
    (P/'reports/delivery_preflight.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({key:value for key,value in report.items() if key!='preserved_releases'},ensure_ascii=True))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
