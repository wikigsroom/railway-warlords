"""Prepare byte-identical screenshots, full-frame GIFs and public provenance.

Native screenshots are never edited. GIFs preserve chronological native video
frames without overlays, crops, frame synthesis or speed changes.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

P = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, default=P.parents[1])
    parser.add_argument('--skip-gifs', action='store_true')
    args = parser.parse_args()
    media = P / 'docs/media'
    media.mkdir(parents=True, exist_ok=True)
    selected = {
        'battlefield.png': 'reports/screenshots/map_final_windows.png',
        'mountains.png': 'reports/screenshots/map_bank_native/mountain.png',
        'coast.png': 'reports/screenshots/map_bank_native/coast.png',
        'tributaries.png': 'reports/screenshots/map_bank_native/tributaries.png',
        'sand.png': 'reports/screenshots/map_bank_native/sand.png',
        'gravel.png': 'reports/screenshots/map_bank_native/gravel.png',
        'wet-soil.png': 'reports/screenshots/map_bank_native/wet_soil.png',
        'yangtze.png': 'reports/screenshots/map_bank_native/yangtze.png',
        'asia-overview.png': 'reports/screenshots/asia_1840_overview.png',
        'legion-deployment.png': 'reports/screenshots/legion_deployment_windows.png',
        'mobile-layout.png': 'reports/screenshots/map_bank_native/forest_x30.png',
        'battle-impact.png': 'reports/screenshots/visual_playtest/04_impact.png',
        'air-recon.png': 'reports/screenshots/visual_playtest/06_air_recon.png',
    }
    captures = []
    for name, relative in selected.items():
        source = P / relative
        target = media / name
        shutil.copyfile(source, target)
        assert sha(source) == sha(target)
        metadata = source.with_suffix('.json')
        row = {'file': f'docs/media/{name}', 'native_source': relative,
               'sha256': sha(source), 'byte_identical_to_native_capture': True,
               'physical_android_device_tested': False}
        if metadata.exists():
            target_metadata = target.with_suffix('.json')
            shutil.copyfile(metadata, target_metadata)
            row['metadata'] = target_metadata.relative_to(P).as_posix()
        captures.append(row)
    menu = media / 'menu.png'
    if menu.exists():
        captures.insert(0, {'file': 'docs/media/menu.png', 'sha256': sha(menu),
                          'native_source': 'current Windows export --qa-session --capture',
                          'metadata': 'docs/media/menu.json', 'raw_godot_viewport': True,
                          'physical_android_device_tested': False})
    video = P / 'reports/atlas_v2_native_final.mp4'
    clips = [('movement.gif', 0.5, 7.0), ('combat.gif', 15.0, 8.0)]
    animations = []
    for name, start, duration in clips:
        target = media / name
        vf = ('fps=12,scale=960:-1:flags=lanczos,split[a][b];'
              '[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=sierra2_4a')
        command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                   '-ss', str(start), '-t', str(duration), '-i', str(video),
                   '-filter_complex', vf, '-loop', '0', str(target)]
        if not args.skip_gifs:
            subprocess.run(command, check=True)
        if target.exists():
            animations.append({'file': target.relative_to(P).as_posix(),
                               'sha256': sha(target), 'source': video.relative_to(P).as_posix(),
                               'source_sha256': sha(video), 'start_seconds': start,
                               'duration_seconds': duration, 'fps': 12, 'width': 960,
                               'full_frame': True, 'playback_speed': 1.0, 'filter': vf,
                               'overlays': False, 'synthetic_frames': False, 'audio': False})
    write_json(media / 'manifest.json', {
        'version': '0.2.12', 'screenshots': captures, 'animations': animations,
        'source_video': {'file': video.relative_to(P).as_posix(), 'sha256': sha(video),
                         'resolution': [1440, 810], 'fps': 30, 'duration_seconds': 26.2},
        'notice': 'Desktop native captures. Mobile layout is not a physical Android test.'})

    manifest = json.loads((P / 'assets/manifest.json').read_text(encoding='utf-8'))
    provenance = []
    for row in manifest['assets']:
        engine = P / row['engine_path'].removeprefix('res://')
        digest = sha(engine)
        assert digest == row['source_sha256'], row['id']
        prompt_source = args.workspace / row['prompt_file']
        prompt_target = P / 'docs/asset-prompts' / (row['id'] + '.txt')
        if prompt_source.exists():
            prompt_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(prompt_source, prompt_target)
        if not prompt_target.exists():
            raise RuntimeError('Missing prompt: ' + row['id'])
        prompt_digest = sha(prompt_target)
        assert prompt_digest == row.get('prompt_sha256', prompt_digest), row['id'] + ' prompt'
        provenance.append({'id': row['id'], 'category': row['category'],
                           'image': engine.relative_to(P).as_posix(), 'image_sha256': digest,
                           'prompt': prompt_target.relative_to(P).as_posix(),
                           'prompt_sha256': prompt_digest, 'source_kind': row['source_kind'],
                           'model': row.get('model'), 'quality': row.get('quality'),
                           'original_workspace_source': row['source_file'],
                           'image_modified': False, 'formal_art_approval': False})
    write_json(P / 'docs/asset-provenance/index.json', {
        'version': '0.2.12', 'count': len(provenance),
        'image_bytes': 'Engine PNG files are byte-identical originals; no duplicate raw tree needed.',
        'assets': provenance})

    catalog = json.loads((P / 'content/scenarios/catalog.json').read_text(encoding='utf-8'))
    rows = [json.loads((P / f'content/scenarios/{key}.json').read_text(encoding='utf-8'))
            for key in catalog['scenarios']]
    maps = {f.stem: json.loads(f.read_text(encoding='utf-8'))
            for f in (P / 'content/maps').glob('*.json') if f.name != 'catalog.json'}
    lines = ['# 全部剧本 / Scenario index', '',
             'Generated from runtime JSON for version 0.2.12. These are authored game settings, not a historical certification.', '',
             '数据来自当前运行 JSON。日期为剧本登记日期；部分标题、事件标签和部署仍待逐条历史复核。', '',
             'Counts: ' + ', '.join(f'{k}={v}' for k, v in Counter(r['mode'] for r in rows).items()), '',
             '| ID | 游戏内名称 / In-game name | Mode | Scenario date | Map | Round limit |',
             '| --- | --- | --- | --- | --- | ---: |']
    for r in rows:
        link = '../content/scenarios/' + r['id'] + '.json'
        lines.append(f"| [{r['id']}]({link}) | {r['name']} | {r['mode']} | {r['anchor_date']} | {maps[r['map_id']]['name']} | {r['round_limit']} |")
    (P / 'docs/SCENARIO_INDEX.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    units = json.loads((P / 'content/definitions/units.json').read_text(encoding='utf-8'))
    names = ['Local garrison', 'Rifle regiment', 'Assault battalion', 'Machine-gun battalion',
             'Cavalry regiment', 'Engineer battalion', 'Field artillery', 'Heavy artillery',
             'Armored cars', 'Armored train', 'River gunboat', 'Transport ship', 'Coastal gunship']
    lines = ['# 兵种数值表 / Unit reference', '',
             'Version 0.2.12. Base values from runtime JSON; terrain, skills, morale and stacks modify actual results.', '',
             '基础数值来自运行数据，实际结果还受地形、技能、士气、编队等影响。最早年代还必须通过具体剧本白名单。', '',
             '| ID | 名称 / Unit | HP | Attack | Defense | AP | Range | Cash / Food / Arms | Earliest era | Occupy |',
             '| --- | --- | ---: | ---: | ---: | ---: | --- | --- | ---: | --- |']
    for r, name in zip(units, names):
        cost = r['cost']
        lines.append(f"| `{r['id']}` | {r['name']} / {name} | {r['hp']} | {r['attack']} | {r['defense']} | {r['ap']} | {r['range_min']}–{r['range_max']} | {cost.get('cash',0)} / {cost.get('food',0)} / {cost.get('arms',0)} | {r['historical_era_min']} | {'Yes' if r['can_occupy'] else 'No'} |")
    lines.extend(['', 'Source: [units.json](../content/definitions/units.json).', '',
                  'These values are balance parameters, not historical force statistics. A stack is not an archival battalion/regiment/brigade.'])
    (P / 'docs/UNIT_REFERENCE.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({'native_screenshots': len(captures), 'gifs': len(animations),
                      'verified_asset_sources_and_prompts': len(provenance), 'scenarios': len(rows)}))


if __name__ == '__main__':
    main()
