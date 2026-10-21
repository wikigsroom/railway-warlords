"""Archive previously registered dated native frames before shared QA paths update."""
import re
import shutil

from build_release import P, current_version
from package_delivery import read, require, sha
from package_ui_refinement import write


def main():
    manifest = read(P / 'docs/media/manifest.json')
    archived = 0
    for row in manifest['screenshots']:
        version = row.get('version', manifest['version'])
        if row.get('historical_capture') or version == current_version() or not re.search(r'-v\d+', row['file']):
            continue
        source = P / row['native_source']
        metadata = source.with_suffix('.json')
        require(sha(source) == row['sha256'] == sha(P / row['file']), 'Dated frame already differs')
        facts = read(metadata)
        require(facts['build_version'] == version and facts['raw_godot_capture'], 'Dated raw source required')
        # Preserve the complete native file hierarchy underneath its actual version.
        relative = source.relative_to(P / 'reports/screenshots')
        target = P / 'reports/screenshots/ui_refinement_native' / ('v' + version.replace('.', '')) / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            require(sha(target) == row['sha256'] and sha(target.with_suffix('.json')) == sha(metadata), 'Archived frame changed')
        else:
            shutil.copyfile(source, target)
            shutil.copyfile(metadata, target.with_suffix('.json'))
        row.update(native_source=target.relative_to(P).as_posix(), historical_capture=True,
            preserved_previous_native_source=source.relative_to(P).as_posix())
        archived += 1
    write(P / 'docs/media/manifest.json', manifest)
    print('Preserved dated whole native frames: ' + str(archived), flush=True)


if __name__ == '__main__':
    main()
