"""Refresh portable provenance and copy untouched current native screenshots.

Older recordings keep their own version identity. No image pixels are edited.
"""
import argparse
import json
from pathlib import Path
import shutil
import base64
import hashlib
from build_release import P, ROOT, current_version, source_digest
from package_delivery import read, require, sha


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def provenance():
    records = []
    archive_path=P/'docs/asset-provenance/legacy-portrait-prompts.json'
    legacy=read(archive_path)['prompts'] if archive_path.exists() else {}
    previous = {row['id']:row for row in read(P / 'docs/asset-provenance/index.json')['assets']}
    for row in read(P / 'assets/manifest.json')['assets']:
        image = P / row['engine_path'].removeprefix('res://')
        prompt = P / 'docs/asset-prompts' / (row['id'] + '.txt')
        original_prompt = ROOT / row['prompt_file']
        require(sha(image) == row['source_sha256'], 'Original image mismatch: ' + row['id'])
        alias_record=legacy.get(row['id'])
        if alias_record:
            original=base64.b64decode(alias_record['utf8_bytes_base64'])
            require(hashlib.sha256(original).hexdigest()==row['prompt_sha256']==alias_record['original_sha256'], 'Encoded original prompt differs')
            if original_prompt.exists():require(original_prompt.read_bytes()==original, 'Original prompt bytes changed')
        elif prompt.exists() and original_prompt.exists():
            require(sha(prompt) == sha(original_prompt), 'Immutable portable prompt differs: ' + row['id'])
        elif not prompt.exists() and original_prompt.exists():
            shutil.copyfile(original_prompt, prompt)
        require(prompt.is_file(), 'Missing portable prompt: ' + row['id'])
        prompt_sha = sha(prompt)
        expected = row.get('prompt_sha256') or previous.get(row['id'],{}).get('prompt_sha256')
        require(expected is not None and (prompt_sha == expected or alias_record is not None), 'Registered prompt differs: ' + row['id'])
        records.append(dict(id=row['id'], category=row['category'], image=image.relative_to(P).as_posix(),
                            image_sha256=sha(image), prompt=prompt.relative_to(P).as_posix(),
                            prompt_sha256=prompt_sha, source_kind=row['source_kind'], model=row.get('model'),
                            quality=row.get('quality'), original_workspace_source=row['source_file'],
                            image_modified=False, formal_art_approval=False))
        if alias_record:records[-1].update(readable_alias_transcription=True,original_prompt_archive=archive_path.relative_to(P).as_posix(),original_prompt_sha256=alias_record['original_sha256'])
    write(P / 'docs/asset-provenance/index.json', dict(version=current_version(), count=len(records),
          image_bytes='Engine PNG files are byte-identical originals; no duplicate raw tree needed.', assets=records))
    print(json.dumps(dict(provenance_images_and_prompts=len(records))), flush=True)


def media():
    version = current_version()
    proof = read(P / 'reports/terrain_surface_native_evidence.json')
    require(proof['passed'] and proof['version'] == version and proof['runtime_source_sha256'] == source_digest()[0]
            and len(proof['groups']) == 6, 'Complete current native capture proof required')
    old = read(P / 'docs/media/manifest.json')
    folder = P / 'reports/screenshots'
    war = folder / 'war_room_native/windows'
    terrain = folder / 'terrain_surfaces_native/windows'
    details = folder / 'terrain_surfaces_native/details'
    coast_proof = read(P / 'reports/control_land_native_evidence.json')
    require(coast_proof['passed'] and coast_proof['version'] == version and coast_proof['runtime_source_sha256'] == proof['runtime_source_sha256'],
            'Current native coastal-control proof required')
    coast = folder / 'control_land_native/windows'
    symbols_proof = read(P / 'reports/map_symbol_native_evidence.json')
    require(symbols_proof['passed'] and symbols_proof['version'] == version
            and symbols_proof['runtime_source_sha256'] == proof['runtime_source_sha256'], 'Current symbol viewport proof required')
    symbols = folder / 'map_symbols_native/windows'
    selected = {'menu.png': war / 'home.png', 'battlefield.png': folder / 'map_final_windows.png',
                'mountains.png': details / 'mountain.png', 'coast.png': details / 'coast.png',
                'tributaries.png': details / 'tributaries.png', 'sand.png': terrain / 'map_dune_sand.png',
                'gravel.png': terrain / 'map_gravel_gobi.png', 'wet-soil.png': terrain / 'map_saline_meadow.png',
                'yangtze.png': details / 'yangtze.png', 'asia-overview.png': folder / 'asia_1840_overview.png',
                'nanjing.png': details / 'nanjing.png', 'yangtze-x30.png': details / 'yangtze_x30.png',
                'legion-deployment.png': war / 'legion_deployment.png',
                'mobile-layout.png': folder / 'war_room_native/x30_layout/opening_army.png',
                'map-regional-symbols.png': symbols / 'asia_1840_400.png',
                'map-selected-formation.png': symbols / 'asia_1840_selected.png'}
    for name, case in [('bohai', 'tianjin'), ('japan', 'osaka'), ('caspian', 'baku'), ('singapore', 'singapore'), ('asia', 'overview')]:
        selected['control-' + name + '.png'] = coast / (case + '_control.png')
    selected['control-bohai-natural.png'] = coast / 'tianjin_natural.png'
    selected['control-caspian-natural.png'] = coast / 'baku_natural.png'
    selected['control-bohai-x30.png'] = folder / 'control_land_native/x30_layout/tianjin_control.png'
    for name, surface in [('campaign-browser', 'campaign'), ('conquest-browser', 'conquest'), ('legion-browser', 'legion'),
                          ('recruitment', 'recruit'), ('city-buildings', 'buildings'), ('diplomacy', 'diplomacy'),
                          ('assign-general', 'assign_general'), ('headquarters', 'headquarters'),
                          ('technology', 'technology'), ('staff-research', 'staff_research')]:
        selected[name + '.png'] = war / (surface + '.png')
    for index, name in enumerate(['terrain-atlas-grass', 'terrain-atlas-forest', 'terrain-atlas-relief']):
        selected[name + '.png'] = terrain / ('atlas_' + str(index) + '.png')
    for family in ['temperate_meadow', 'temperate_litter', 'conifer_litter', 'flood_meadow', 'weathered_rock', 'alpine_scree']:
        selected['terrain-' + family.replace('_', '-') + '.png'] = terrain / ('map_' + family + '.png')
    rows = []
    for name, source in selected.items():
        meta = read(source.with_suffix('.json'))
        require(meta['build_version'] == version and meta['raw_godot_capture'], 'Current native source required: ' + name)
        target = P / 'docs/media' / name
        shutil.copyfile(source, target)
        shutil.copyfile(source.with_suffix('.json'), target.with_suffix('.json'))
        require(sha(target) == sha(source), 'Screenshot bytes changed: ' + name)
        rows.append(dict(file=target.relative_to(P).as_posix(), version=version,
                         native_source=source.relative_to(P).as_posix(), sha256=sha(source),
                         metadata=target.with_suffix('.json').relative_to(P).as_posix(),
                         byte_identical_to_native_capture=True, physical_android_device_tested=False))
    for row in old['screenshots']:
        if Path(row['file']).name not in selected:
            row.setdefault('version', '0.2.12')
            row['historical_capture'] = row['version'] != version
            rows.append(row)
    animations = old['animations']
    for row in animations:
        row.setdefault('version', '0.2.12')
        row['historical_recording'] = True
    video = old['source_video']
    video.setdefault('version', '0.2.12')
    write(P / 'docs/media/manifest.json', dict(version=version, screenshots=rows, animations=animations,
          source_video=video, current_native_evidence='reports/terrain_surface_native_evidence.json',
          current_control_native_evidence='reports/control_land_native_evidence.json',
          current_map_symbol_native_evidence='reports/map_symbol_native_evidence.json',
          current_general_native_evidence='reports/general_portrait_native_evidence.json',
          notice='Current terrain/UI screenshots are native Windows captures. Battle GIFs and action stills preserve version 0.2.12. No physical Android acceptance.'))
    current_count=sum(row.get('version') == version for row in rows)
    print(json.dumps(dict(screenshots=len(rows), current=current_count, historical=len(rows)-current_count,
                          historical_gifs=len(animations))), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--provenance-only', action='store_true')
    args = parser.parse_args()
    provenance()
    if not args.provenance_only:
        media()


if __name__ == '__main__':
    main()
