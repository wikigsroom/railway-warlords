"""Validate portable README links, native media and immutable asset provenance."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
from PIL import Image
from build_release import source_digest

P = Path(__file__).resolve().parents[1]
PUBLIC_DOCS = ['README.md', 'README.en.md', 'LICENSE-NOTICE.md',
               'docs/DEVELOPMENT.md', 'docs/MEDIA.md',
               'docs/SCENARIO_INDEX.md', 'docs/UNIT_REFERENCE.md']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(relative):
    return json.loads((P / relative).read_text(encoding='utf-8-sig'))


def main():
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
    if checked_assets != 1056:
        errors.append({'type': 'asset_count', 'actual': checked_assets})

    media = read('docs/media/manifest.json')
    gif_facts = []
    for row in media['screenshots']:
        if digest(P / row['file']) != row['sha256']:
            errors.append({'type': 'native_png_digest', 'file': row['file']})
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
    expected_runtime = read('reports/native_visual_evidence.json')['runtime_source_sha256']
    if runtime != expected_runtime:
        errors.append({'type': 'runtime_changed_during_documentation'})
    counts = {}
    for scenario in read('content/scenarios/catalog.json')['scenarios']:
        mode = read('content/scenarios/' + scenario + '.json')['mode']
        counts[mode] = counts.get(mode, 0) + 1
    if counts != {'campaign': 39, 'conquest': 10, 'legion': 12}:
        errors.append({'type': 'scenario_counts', 'actual': counts})
    result = {'passed': not errors, 'version': '0.2.12', 'public_documents': len(PUBLIC_DOCS),
              'local_links_checked': links, 'verified_images_and_prompts': checked_assets,
              'native_screenshots': len(media['screenshots']), 'gifs': gif_facts,
              'candidate_files': len(files), 'candidate_bytes': sum(f.stat().st_size for f in files),
              'text_files_scanned_for_credentials': scanned, 'scenario_counts': counts,
              'runtime_source_sha256': runtime, 'runtime_unchanged': runtime == expected_runtime,
              'physical_android_device_tested': False, 'errors': errors}
    (P / 'reports/repository_validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
