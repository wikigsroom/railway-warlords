"""Refresh current whole native stills while retaining dated earlier media."""
import re
import shutil

from build_release import P, current_version, source_digest
from package_delivery import read, require, sha
from package_ui_refinement import write


def main():
    version = current_version()
    runtime = source_digest()[0]
    proof = read(P / 'reports/map_composition_native_evidence.json')
    require(proof['passed'] and proof['version'] == version and proof['runtime_source_sha256'] == runtime,
        'Current exported composition proof required')
    manifest = read(P / 'docs/media/manifest.json')
    for row in manifest['screenshots']:
        if row.get('historical_capture') or re.search(r'-v\d+', row['file']):
            continue
        source = P / row['native_source']
        metadata = source.with_suffix('.json')
        require(source.is_file() and metadata.is_file(), 'Retained native source missing')
        if read(metadata)['build_version'] != version:
            continue
        shutil.copyfile(source, P / row['file'])
        shutil.copyfile(metadata, P / row['metadata'])
        row.update(version=version, sha256=sha(source), byte_identical_to_native_capture=True)
    captures = {r['case']: r for r in proof['groups'][0]['captures']}
    for name in ['wuhan', 'beijing', 'village']:
        row = captures[name]
        source = P / row['file']
        metadata = P / row['metadata']
        require(sha(source) == row['sha256'] and sha(metadata) == row['metadata_sha256'], 'Native frame changed')
        target = P / 'docs/media' / ('map-composition-' + name + '-v' + version.replace('.', '') + '.png')
        shutil.copyfile(source, target)
        shutil.copyfile(metadata, target.with_suffix('.json'))
        relative = target.relative_to(P).as_posix()
        manifest['screenshots'] = [r for r in manifest['screenshots'] if r['file'] != relative]
        manifest['screenshots'].append(dict(file=relative, version=version, native_source=row['file'],
            metadata=target.with_suffix('.json').relative_to(P).as_posix(), sha256=row['sha256'],
            byte_identical_to_native_capture=True, historical_capture=False, physical_android_device_tested=False))
    manifest.update(version=version, current_map_composition_evidence='reports/map_composition_native_evidence.json',
        notice='Complete current shipping Windows viewports copied byte for byte. Explicitly dated older stills and GIFs retain their actual versions. Desktop X30 proportions are not physical phone evidence.')
    write(P / 'docs/media/manifest.json', manifest)
    print('Refreshed current native stills and added three unchanged composition viewports.', flush=True)


if __name__ == '__main__':
    main()
