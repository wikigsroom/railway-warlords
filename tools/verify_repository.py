"""Validate portable README links, native media and immutable asset provenance."""
import argparse
import hashlib
import base64
import json
from pathlib import Path
import re
import subprocess
from PIL import Image
from build_release import source_digest, current_version

P = Path(__file__).resolve().parents[1]
PUBLIC_DOCS = ['README.md', 'README.en.md', 'LICENSE-NOTICE.md',
               'docs/DEVELOPMENT.md', 'docs/MEDIA.md',
               'docs/SCENARIO_INDEX.md', 'docs/UNIT_REFERENCE.md',
               'docs/30_二十类地域地表与纹理整改.md',
               'docs/31_连续地表与水系层次.md',
               'docs/32_真实河段连续水面.md',
               'docs/33_真实海岸与控制区裁切.md',
               'docs/34_连续地表混合与控制色去重.md',
               'docs/35_地图缩放层次与精确点选.md',
               'docs/36_连续高程光影与细河岸带.md',
               'docs/37_二十类地表材质形态重制.md',
               'docs/38_源陆地补纹与林底选材约束.md',
               'docs/39_本地YuE2纯器乐配乐与场景衔接.md',
               'docs/40_每日历法与四阶段人物肖像.md',
               'docs/41_军事界面与将领档案精修.md',
               'docs/42_战区沙盘与外交事务精修.md',
               'docs/43_安静地表与山脚融合.md',
               'docs/44_细海岸与沿岸图层统一.md',
               'docs/45_连续水纹与真实蜂窝显示.md',
               'docs/46_师旅级将领池与战役名册.md',
               'docs/47_地图模型比例与统一标注布局.md',
               'docs/48_战场浮动界面与直接触摸滚动.md',
               'docs/49_低地底纹与河岸材质调整.md',
               'docs/50_山地底材衔接与地形绘制批处理.md',
               'docs/51_地图拖动预取与源线段缓存.md',
               'docs/52_局部战区五倍比例与独立江岸.md',
               'docs/53_地表绘制层次修订.md',
               'docs/54_控制区共边与海岸描边修复.md',
               'docs/55_城市建筑群层级与地图整合.md',
               'docs/56_细水系圆角与水床显示.md',
               'docs/57_源岸线方向与柔和海岸过渡.md',
               'docs/SOUND_DESIGN.md', 'SOUND_DESIGN.md',
               'docs/25_欧陆战争6地图资源差距评估.md',
               'docs/00_程序文档索引.md', 'docs/04_美术来源与审核.md',
               'docs/05_测试与验收.md', 'docs/06_双端构建与发布.md',
               'docs/23_当前完成度评估.md', 'docs/26_欧陆战争6_UI结构与视觉对标.md']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(relative):
    return json.loads((P / relative).read_text(encoding='utf-8-sig'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--documentation-only', action='store_true',
                        help='Validate docs/media/source integrity without claiming the full native release gates.')
    parser.add_argument('--report-output', type=Path,
                        help='Write to a new report path, preserving previous release evidence.')
    args = parser.parse_args()
    if args.report_output and args.report_output.exists():
        raise FileExistsError(args.report_output)
    raw = subprocess.check_output(['git', 'ls-files', '--cached', '--others',
                                   '--exclude-standard', '-z'], cwd=P)
    files = {P / name.decode('utf-8') for name in raw.split(b'\0') if name}
    paths = {f.resolve() for f in files}
    errors = []
    links = 0
    for relative in PUBLIC_DOCS:
        path = P / relative
        for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if link.startswith(('https:', 'http:', 'mailto:')):
                continue
            link = link.strip('<>')
            name, _, anchor = link.partition('#')
            target = (path.parent / name).resolve() if name else path
            links += 1
            if not target.exists():
                errors.append({'type': 'missing_link', 'file': relative, 'link': link})
            elif target.is_file() and target not in paths:
                errors.append({'type': 'excluded_link', 'file': relative, 'link': link})
            if anchor and target.suffix == '.md' and target.exists():
                if f'id="{anchor}"' not in target.read_text(encoding='utf-8'):
                    errors.append({'type': 'missing_anchor', 'file': relative, 'link': link})

    provenance = read('docs/asset-provenance/index.json')
    checked_assets = 0
    for row in provenance['assets']:
        for field, checksum in [('image', 'image_sha256'), ('prompt', 'prompt_sha256')]:
            path = P / row[field]
            if path.resolve() not in paths or not path.is_file() or digest(path) != row[checksum]:
                errors.append({'type': 'asset_provenance', 'asset': row['id'], 'field': field})
        checked_assets += 1
    manifest_assets = read('assets/manifest.json')['assets']
    if checked_assets != len(manifest_assets) or {r['id'] for r in provenance['assets']} != {r['id'] for r in manifest_assets}:
        errors.append({'type': 'asset_count', 'actual': checked_assets})
    for row in manifest_assets:
        if digest(P / row['engine_path'].removeprefix('res://')) != row['source_sha256']:
            errors.append({'type': 'registered_original_changed', 'asset': row['id']})
    aliases=read('docs/asset-provenance/legacy-portrait-prompts.json')['prompts']
    for aid,row in aliases.items():
        raw=base64.b64decode(row['utf8_bytes_base64'])
        expected=next(a for a in manifest_assets if a['id']==aid)['prompt_sha256']
        if hashlib.sha256(raw).hexdigest()!=row['original_sha256'] or row['original_sha256']!=expected:
            errors.append({'type':'encoded_original_prompt_changed','asset':aid})

    media = read('docs/media/manifest.json')
    gif_facts = []
    for row in media['screenshots']:
        if digest(P / row['file']) != row['sha256']:
            errors.append({'type': 'native_png_digest', 'file': row['file']})
        original = P / row['native_source']
        if not original.is_file() or digest(original) != row['sha256']:
            errors.append({'type': 'native_source_digest', 'file': row['file']})
        if row.get('metadata'):
            meta = read(row['metadata'])
            if meta['build_version'] != row.get('version', media['version']) or not meta['raw_godot_capture']:
                errors.append({'type': 'native_media_version', 'file': row['file']})
    for row in media['animations']:
        target = P / row['file']
        if digest(target) != row['sha256'] or digest(P / row['source']) != row['source_sha256']:
            errors.append({'type': 'native_video_or_gif_digest', 'file': row['file']})
        with Image.open(target) as im:
            frames = im.n_frames
            width, height = im.size
            duration = 0
            frame_hashes = set()
            for i in range(frames):
                im.seek(i)
                duration += im.info.get('duration', 0)
                frame_hashes.add(hashlib.sha256(im.convert('RGB').tobytes()).hexdigest())
        if (width, height) != (960, 540) or abs(duration / 1000 - row['duration_seconds']) > .1 or len(frame_hashes) < 2:
            errors.append({'type': 'gif_playback', 'file': row['file']})
        gif_facts.append({'file': row['file'], 'frames': frames, 'unique_frames': len(frame_hashes),
                          'duration_ms': duration, 'size': [width, height]})

    secret_patterns = [
        ('private_key', re.compile(r'-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----')),
        ('provider_token', re.compile(r'\b(?:sk-proj-|sk-ant-|gh[pousr]_|github_pat_)[A-Za-z0-9_-]{18,}')),
        ('assigned_secret', re.compile(r'''(?i)(?:api_key|apiKey|token|password|secret)\s*[:=]\s*["'][^"'\n]{16,}["']''')),
    ]
    scanned = 0
    for path in files:
        relative = path.relative_to(P).as_posix()
        if path.stat().st_size >= 100 * 1024 * 1024:
            errors.append({'type': 'oversized_git_blob', 'file': relative})
        if any(part in ('.godot', 'build', '__pycache__', '.toolchain', 'signing') for part in path.relative_to(P).parts):
            errors.append({'type': 'private_or_generated_path', 'file': relative})
        if path.suffix.lower() not in {'.py', '.gd', '.json', '.txt', '.cfg', '.md', '.toml', '.yml', '.yaml', '.tscn', '.import', '.csv'}:
            continue
        text = path.read_text(encoding='utf-8', errors='replace')
        scanned += 1
        for label, pattern in secret_patterns:
            for match in pattern.finditer(text):
                errors.append({'type': label, 'file': relative,
                               'line': text[:match.start()].count('\n') + 1})

    runtime = source_digest()[0]
    expected_runtime = None
    if not args.documentation_only:
        proof = read('reports/terrain_surface_native_evidence.json')
        expected_runtime = proof['runtime_source_sha256']
        if not proof['passed'] or proof['version'] != current_version() or len(proof['groups']) != 6:
            errors.append({'type': 'current_native_proof_incomplete'})
        for group in proof['groups']:
            for row in group['captures']:
                if digest(P / row['file']) != row['sha256'] or digest(P / row['metadata']) != row['metadata_sha256']:
                    errors.append({'type': 'current_native_capture_changed', 'file': row['file']})
        if runtime != expected_runtime:
            errors.append({'type': 'runtime_changed_during_documentation'})
        coast = read('reports/control_land_native_evidence.json')
        if not coast['passed'] or coast['version'] != current_version() or coast['runtime_source_sha256'] != runtime or len(coast['groups']) != 2:
            errors.append({'type': 'current_control_land_proof_incomplete'})
        for group in coast['groups']:
            if digest(P / group['report']) != group['report_sha256']:
                errors.append({'type': 'control_land_report_changed', 'file': group['report']})
            for row in group['captures']:
                if digest(P / row['file']) != row['sha256'] or digest(P / row['metadata']) != row['metadata_sha256']:
                    errors.append({'type': 'control_land_capture_changed', 'file': row['file']})
    counts = {}
    for scenario in read('content/scenarios/catalog.json')['scenarios']:
        mode = read('content/scenarios/' + scenario + '.json')['mode']
        counts[mode] = counts.get(mode, 0) + 1
    if counts != {'campaign': 39, 'conquest': 10, 'legion': 12}:
        errors.append({'type': 'scenario_counts', 'actual': counts})
    result = {'passed': not errors, 'version': current_version(), 'public_documents': len(PUBLIC_DOCS),
              'local_links_checked': links, 'verified_images_and_prompts': checked_assets,
              'native_screenshots': len(media['screenshots']), 'gifs': gif_facts,
              'candidate_files': len(files), 'candidate_bytes': sum(f.stat().st_size for f in files),
              'text_files_scanned_for_credentials': scanned, 'scenario_counts': counts,
              'runtime_source_sha256': runtime, 'runtime_unchanged': None if args.documentation_only else runtime == expected_runtime,
              'scope': 'documentation_media_and_source_integrity' if args.documentation_only else 'full_repository_and_native_proofs',
              'full_native_release_gates_checked': not args.documentation_only,
              'physical_android_device_tested': False, 'errors': errors}
    output = args.report_output or P / ('reports/repository_documentation_validation.json' if args.documentation_only else 'reports/repository_validation.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
