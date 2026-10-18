"""Copy complete current dossier viewports verbatim; never process image pixels."""
import json
import shutil
from build_release import P, current_version, source_digest
from package_delivery import read, sha, require


def main():
    version = current_version()
    proof = read(P / 'reports/ui_refinement_native_evidence.json')
    require(proof['passed'] and proof['version'] == version
            and proof['runtime_source_sha256'] == source_digest()[0], 'Current dossier proof required')
    registered = {row['file']: row for group in proof['groups'] for row in group['captures']}
    folder = P / 'reports/screenshots/dossier_native'
    targets = [('dossier-hong-v0223.png', 'windows/dossier_hong_middle.png'),
               ('dossier-medals-v0223.png', 'windows/medal_slots_full.png'),
               ('dossier-x30-v0223.png', 'x30_layout/medal_slots_full.png'),
               ('dossier-large-text-v0223.png', 'large_text/dossier_hong_middle.png')]
    manifest = read(P / 'docs/media/manifest.json')
    replacements = set('docs/media/' + name for name, _ in targets)
    rows = [row for row in manifest['screenshots'] if row['file'] not in replacements]
    for name, relative in targets:
        source = folder / relative
        registered_row = registered[source.relative_to(P).as_posix()]
        require(sha(source) == registered_row['sha256'], 'Verified source changed')
        metadata = source.with_suffix('.json')
        require(sha(metadata) == registered_row['metadata_sha256'], 'Verified metadata changed')
        target = P / 'docs/media' / name
        shutil.copyfile(source, target)
        shutil.copyfile(metadata, target.with_suffix('.json'))
        require(sha(target) == sha(source), 'Screenshot copy differs')
        rows.append(dict(file=target.relative_to(P).as_posix(), version=version,
                         native_source=source.relative_to(P).as_posix(), sha256=sha(source),
                         metadata=target.with_suffix('.json').relative_to(P).as_posix(),
                         byte_identical_to_native_capture=True, historical_capture=False,
                         physical_android_device_tested=False))
    manifest.update(screenshots=rows, current_dossier_native_evidence='reports/ui_refinement_native_evidence.json',
                    notice='Current map/UI/dossier pictures are complete Windows viewports. Four 0.2.22 character captures and two 0.2.12 action stills keep their historical identity. Battle GIFs remain 0.2.12. No physical Android acceptance.')
    (P / 'docs/media/manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(screenshots=len(rows), new_complete_dossier_captures=len(targets))))


if __name__ == '__main__':
    main()
