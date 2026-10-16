"""Verify preserved source bytes against the actual immutable delivered ZIP."""
import json
import zipfile
from datetime import datetime, timezone
from build_release import P, ROOT
from package_delivery import sha


def main():
    manifest = json.loads((P/'tests/fixtures/reference_v023.json').read_text(encoding='utf-8'))
    archive_path = ROOT / manifest['source_archive']
    archive_sha = sha(archive_path)
    if archive_sha != manifest['source_archive_sha256']:
        raise SystemExit('Preserved 0.2.3 source archive changed.')
    checks = []
    with zipfile.ZipFile(archive_path) as archive:
        for row in manifest['references']:
            original = archive.read(row['original'])
            import hashlib
            original_sha = hashlib.sha256(original).hexdigest()
            expected = original.decode('utf-8')
            if row['original'].endswith('state_access.gd'):
                expected = expected.replace('class_name StateAccess', 'class_name SnapshotReferenceAccess023')
                expected = expected.replace('extends RefCounted\n', 'extends RefCounted\nconst ReferenceContext=preload("res://tests/fixtures/reference_cache_v023.gd")\n', 1)
                expected = expected.replace('RulesQueryCache.current()', 'ReferenceContext.current()')
            else:
                expected = expected.replace('class_name CommandKernel', 'class_name SnapshotReferenceKernel023')
                expected = expected.replace('StateAccess.', 'SnapshotReferenceAccess023.')
            reference = P / row['fixture']
            valid = original_sha == row['original_sha256'] and sha(reference) == row['reference_sha256']
            valid = valid and reference.read_bytes() == expected.encode('utf-8')
            checks.append({'fixture':row['fixture'],'passed':valid,'original_sha256':original_sha,
                           'reference_sha256':sha(reference)})
    cache = P / manifest['cache_namespace']['fixture']
    checks.append({'fixture':manifest['cache_namespace']['fixture'],
                   'passed':sha(cache)==manifest['cache_namespace']['sha256'],
                   'scope':'Independent private derived-index namespace; single main-thread reference driver.'})
    report = {'passed':all(row['passed'] for row in checks), 'source_archive':manifest['source_archive'],
              'source_archive_sha256':archive_sha,'checked_at_utc':datetime.now(timezone.utc).isoformat(),
              'checks':checks,'scope':'Actual archived bytes verified; only class-name, access-class references and an isolated private query-cache namespace substituted. All original rule and snapshot operations are unchanged.'}
    (P/'reports/snapshot_reference_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'passed':report['passed'],'references':len(checks)}))
    raise SystemExit(0 if report['passed'] else 1)


if __name__=='__main__':main()
