"""Generate original independent UI assets only through the authorized Sub2 CLI.

No pixel changes, montage, cropping or atlas packing. Install byte-identical
copies with immutable prompt/source provenance; visual review stays explicit.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from PIL import Image

P = Path(__file__).resolve().parents[1]
ROOT = P.parents[1]
RAW = ROOT / 'output/imagegen/warlord/ew6_ui_v030'
CLI = Path('C:/Users/carzy/.codex/skills/sub2-image-gen/scripts/sub2_image_gen.py')
BASE = '''Original interface asset for a premium historical turn-based strategy game
set in Asia 1840-1940. Restrained European War 6:1914 inspired UI readability,
entirely original geometry and materials, no copied EasyTech logo or artwork.
Frontal orthographic view, clean low-frequency surfaces, elegant fine edges.
Absolutely no text, letters, digits, watermark, label, montage or sprite sheet.
One complete isolated asset in a square canvas. No crop, no perspective.
'''

JOBS = [
    ('ui', 'ui_dialog_frame', False, BASE + '''ONE square opaque light cool-gray
information panel. Flat interior #CACCD0 covering 96% of canvas, extremely quiet
subtle brushed metal grain. A thin crisp dark slate outer rim, fine silver bevel,
one subtle warm bronze inner hairline. Outer rim only 1.5% of image width per side.
No thick ornamental frame, rust, screws, corners, paper, icons, scenery or inset
objects. Straight edge-to-edge square. The center must be almost uniform gray.'''),
    ('ui', 'ui_hud_plate', False, BASE + '''ONE square opaque dark graphite HUD
plate, #1C2428 center, faint quiet brushed steel grain, slim #6F787C rim occupying
only 1% at the edge and an even thinner muted silver inner highlight. No gold
frame, decorations, paper, screws, rounded corners or inset objects. Edge to
edge square, simple sober military dashboard material, very legible at small scale.'''),
    ('ui', 'ui_action_hex', True, BASE + '''ONE compact regular vertical hexagonal
command badge. Entire six-sided shape centered in 78% of canvas. Dark charcoal
opaque quiet interior, a thin silver outer bevel and muted champagne inner rim.
Completely empty interior without symbol or lettering. Transparent alpha outside
the hexagon, no circular disc, no ground shadow, no white background. This is a
single coherent flat UI button shape, not 3D scenery. All six corners fully visible.'''),
    ('icon', 'icon_resource_fuel', True, BASE + '''ONE small hand-painted kerosene
fuel tin used in early 20th century Asia, dark bronze rectangular metal oil can
with a short spout and cap. Warm neutral highlights, clear silhouette readable
at 32 px. Entire object centered in 75% of canvas, transparent exterior. No labels,
printed markings, red star, modern plastic, background, badge or extra objects.'''),
    ('icon', 'icon_resource_silver', True, BASE + '''ONE compact hand-painted group
of three silver coins and one tiny traditional Chinese silver sycee, cool silver
metal with clear highlights. Simplified readable at 32 px. One coherent centered
group in 75% of canvas, transparent exterior. No lettering, exact inscription,
banknote, background, badge or extra objects. Silver only, no gold.'''),
    ('icon', 'icon_command_endphase', True, BASE + '''ONE simple champagne-colored
hourglass icon, flat silhouette with thin silver casing, pale sand, symmetric and
clear at 40 px. Entire single hourglass in 70% of canvas. Transparent exterior,
no background, badge, lettering, hands, border or detached parts.'''),
    ('icon', 'icon_command_diplomacy', True, BASE + '''ONE simple ivory and muted
champagne handshake icon, two complete hands clasped, clean flat carved silhouette
with minimal slate shadow. Readable at 40 px. Single centered coherent symbol in
75% of canvas. Transparent exterior, no badge, background, flag, text or frame.'''),
    ('icon', 'icon_command_pause', True, BASE + '''ONE simple ivory pause symbol,
two solid parallel rectangular metal bars with a very slim silver edge, clean
front-on flat silhouette. Centered within 70% of square canvas, transparent
exterior, no badge, frame, shadow cloud, background, text or extra symbol.'''),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(job):
    category, name, transparent, prompt = job
    folder = RAW / name / 'r001'
    folder.mkdir(parents=True, exist_ok=True)
    prompt_file, source = folder / 'prompt.txt', folder / 'source.png'
    if prompt_file.exists() and prompt_file.read_text(encoding='utf-8') != prompt:
        raise RuntimeError('Immutable prompt differs: ' + name)
    if not prompt_file.exists():
        prompt_file.write_text(prompt, encoding='utf-8')
    if not source.exists():
        attempt = 1
        log = folder / 'generation.log'
        while log.exists():
            attempt += 1
            log = folder / ('generation_attempt_%02d.log' % attempt)
        with log.open('w', encoding='utf-8') as stream:
            result = subprocess.run([sys.executable, str(CLI), 'generate',
                '--model', 'gpt-image-2.5', '--quality', 'high', '--size', '1024x1024',
                '--background', 'transparent' if transparent else 'opaque',
                '--prompt-file', str(prompt_file), '--out', str(source)],
                stdout=stream, stderr=subprocess.STDOUT, timeout=900)
        if result.returncode or not source.exists():
            raise RuntimeError('Sub2 generation failed: ' + name + '; see ' + str(log))
    with Image.open(source) as im:
        dimensions = list(im.size)
        alpha = im.getchannel('A').getextrema()[0] if im.mode == 'RGBA' else 255
    if transparent and alpha != 0:
        raise RuntimeError('Transparent alpha missing: ' + name)
    record = dict(id=name, category=category, subject=name, view='front',
        state='generated_pending_visual_review', game_ready=False,
        source_kind='sub2_image_gen', model='gpt-image-2.5', quality='high',
        style_version='warlord_ew6_ui_v030', era='1840-1940',
        source_file=source.relative_to(ROOT).as_posix(), source_sha256=sha(source),
        prompt_file=prompt_file.relative_to(ROOT).as_posix(), prompt_sha256=sha(prompt_file),
        actual_dimensions=dimensions, planned_source_request=[1024,1024],
        engine_path='res://assets/' + category + '/' + name + '.png',
        planned_engine_path='res://assets/' + category + '/' + name + '.png',
        runtime_import_max_dimension=128 if category == 'icon' else 768,
        background='transparent' if transparent else 'opaque', alpha_min=alpha,
        revision='ew6_ui_v030_r001', image_modified=False)
    (folder / 'provenance.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    records, failures = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        jobs = {pool.submit(generate, job): job[1] for job in JOBS}
        for future in as_completed(jobs):
            try:
                record = future.result()
                records.append(record)
                print(record['id'] + ': original Sub2 PNG ready',flush=True)
            except Exception as error:
                failures.append(dict(id=jobs[future],reason=str(error)))
                print(json.dumps(failures[-1]),flush=True)
    if args.install:
        path = P / 'assets/manifest.json'
        manifest = json.loads(path.read_text(encoding='utf-8'))
        by_id = {row['id']:row for row in manifest['assets']}
        for record in records:
            shutil.copyfile(ROOT / record['source_file'], P / record['engine_path'].removeprefix('res://'))
            by_id[record['id']] = record
        manifest['assets'] = sorted(by_id.values(), key=lambda row:row['id'])
        path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report = dict(passed=not failures,requested=len(JOBS),completed=[r['id'] for r in records],
        failures=failures,installed=args.install,provider='sub2-image-gen/gpt-image-2.5',
        manual_compositing=False,source_images_modified=False)
    (P / 'reports/ew6_ui_asset_generation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    raise SystemExit(bool(failures))


if __name__ == '__main__':
    main()
