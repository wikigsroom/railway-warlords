"""Compare current historical JSON bytes with the immutable 0.1.2 source archive."""
import hashlib
import json
import zipfile
from pathlib import Path

P=Path(__file__).resolve().parents[1]
ROOT=P.parents[1]

def main():
    baseline=ROOT/'output/releases/railway-warlords-0.1.2'
    manifest=json.loads((baseline/'release_manifest.json').read_text(encoding='utf-8'))
    artifact=next(item for item in manifest['files'] if item['kind']=='godot_source_and_provenance')
    paths=[path for folder in ('definitions','maps','scenarios') for path in sorted((P/'content'/folder).glob('*.json'))]
    paths.append(P/'content/geography_sources.json');checks=[]
    with zipfile.ZipFile(baseline/artifact['name']) as archive:
        for path in paths:
            name=path.relative_to(ROOT).as_posix();old=archive.read(name);current=path.read_bytes()
            checks.append({'file':path.relative_to(P).as_posix(),'matches':old==current,'baseline_sha256':hashlib.sha256(old).hexdigest(),'current_sha256':hashlib.sha256(current).hexdigest()})
    report={'passed':all(item['matches'] for item in checks),'baseline_version':'0.1.2','baseline_archive':artifact['name'],'baseline_archive_expected_sha256':artifact['sha256'],'archive_integrity_evidence':'reports/delivery_preflight.json','requires_preserved_baseline_preflight':True,'checks':checks,'scope':'All 63 content JSON files, including geography, scenarios and original definitions. Does not certify all military-history facts.'}
    (P/'reports/geography_preservation_v6.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'passed':report['passed'],'json_files_compared':len(checks)},ensure_ascii=True))
    raise SystemExit(0 if report['passed'] else 1)

if __name__=='__main__':main()
