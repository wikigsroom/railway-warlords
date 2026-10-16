"""Whole immutable Sub2 sources for the continuous relief revision; no image editing."""
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
RAW = ROOT / 'output/imagegen/warlord/ew6_v025/relief_v0212'
CLI = Path('C:/Users/carzy/.codex/skills/sub2-image-gen/scripts/sub2_image_gen.py')


def plan():
    materials = [
        ('tile_plain_01', '''ONE flat opaque seamless ground material. Very quiet, restrained
muted sage-olive gray-green #9BA67D. Painted historical strategy-map ground seen straight
down. Mostly uniform smooth color with broad subtle tonal drift and a few tiny fine dry
grass flecks. LOW CONTRAST: ninety percent quiet flat areas. No chunky sponge brush,
camouflage, rocks, hills, trees, fields, objects, rivers, roads, paper, stains or shadows.
No objects or actual geographic features. Not aerial photography. Soft matte hand-painted
material, no 3D bumps or illumination gradients. Fill the entire canvas edge to edge.
No frame, grid, words, logo, watermark, collage or panels. All edges should join seamlessly.'''),
        ('tile_plain_02', '''ONE flat opaque seamless ground material, companion variant for
a historical strategy map. Quiet muted warm olive-sage #9BA17A, just slightly drier than
fresh meadow. Ninety percent calm smooth matte color, with faint broad natural variation
and occasional tiny subdued grass flecks. Straight top-down. LOW CONTRAST. No rocks,
hills, trees, farms, field boundaries, roads, rivers, objects, 3D bumps, cast shadows,
parchment, stains or camouflage pattern. No noisy hatching or photographic texture.
Whole canvas continuous material, seamless edges. No borders, grids, lettering or panels.'''),
    ]
    jobs = [('tile', aid, prompt, False) for aid, prompt in materials]
    style = '''ONE isolated terrain miniature for an original premium historical strategy
game. Readable broad hand-painted 2.5D volumes. Fixed elevated orthographic view at 55
degrees, north at image top. Upper-left sunlight, gentle cool lower-right shadows.
Muted olive-sage slopes #8C9766, gray-green rock #7B8273, deep slate-olive shadow #52634F.
Large simple coherent lit planes, no black hatch noise or photorealistic rock texture.
Match a quiet muted sage meadow. This is symbolic relief, not a real named mountain.
No trees, snow, buildings, roads, rivers, labels, flags, grid, UI, horizon, backdrop or sky.
Transparent alpha ZERO exterior and generous empty margins. NO ground rectangle, round
pedestal, detached rocks, separate objects, colored halo or scenery sheet. One connected
mass only, complete silhouette centered inside 80 percent of the entire image.
'''
    subjects = {
        'scenery_ridge_spine_ew': '''A compact connected rocky mountain spine, running LEFT
to RIGHT. Three strongly dimensional asymmetric angular peaks connected by visible
saddles and overlapping grassy foothill shoulders. Highest peak offset from center.
Broad, relatively high 1.7:1 visible silhouette, not a flat strip. Soft irregular grassy
foot merges quietly into transparent exterior. Clearly readable at 160 display pixels.''',
        'scenery_ridge_spine_ns': '''A compact connected rocky mountain spine running from
image TOP toward BOTTOM: three peaks recede in depth, overlapping front-to-back along
the north-south axis. High lit crest, darker right slopes and broad rounded foothills.
Strongly dimensional, relatively compact 1:1 visible silhouette. Not a left-right chain.
Soft irregular grassy foot blends quietly to alpha. Clearly readable at 130 pixels.''',
        'scenery_foothill_ew': '''One low connected rolling foothill spine running LEFT to
RIGHT, with three overlapping smooth shoulders and a shallow saddle. Broad readable
light-facing slopes and darker right slopes, a little quiet gray rock along crest.
Not a pile of separate stones or pointy mountains. Soft olive grassy irregular foot.
Visible shape about 1.7:1, readable at 130 display pixels. No flat grass floor.''',
        'scenery_foothill_ns': '''One low connected rolling foothill spine running TOP to
BOTTOM in depth. Three overlapping broad shoulders receding northward, shallow grassy
saddles, clearly shaded convex slopes and a little quiet gray rock at the crest.
Compact 1:1 visible silhouette; not a left-right strip or pointed mountains.
Soft irregular olive grassy foot, no flat ground floor. Readable at 110 pixels.''',
    }
    jobs.extend(('scenery', aid, style + subject, True) for aid, subject in subjects.items())
    return jobs


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(job):
    category, aid, prompt, transparent = job
    folder = RAW / aid / 'r001'
    folder.mkdir(parents=True, exist_ok=True)
    prompt_file, source = folder / 'prompt.txt', folder / 'source.png'
    if prompt_file.exists() and prompt_file.read_text(encoding='utf-8') != prompt:
        raise RuntimeError('Immutable prompt mismatch: ' + aid)
    if not prompt_file.exists():
        prompt_file.write_text(prompt, encoding='utf-8')
    if not source.exists():
        log = folder / 'generation.log'
        attempt = 2
        while log.exists():
            log = folder / f'generation_attempt_{attempt:02}.log'
            attempt += 1
        with log.open('w', encoding='utf-8') as stream:
            result = subprocess.run([sys.executable, str(CLI), 'generate', '--model', 'gpt-image-2.5',
                '--quality', 'high', '--size', '1024x1024', '--background',
                'transparent' if transparent else 'opaque', '--prompt-file', str(prompt_file),
                '--out', str(source)], stdout=stream, stderr=subprocess.STDOUT, timeout=900)
        if result.returncode or not source.exists():
            raise RuntimeError('Sub2 generation failed: ' + aid + '; inspect local generation log')
    with Image.open(source) as im:
        dimensions = list(im.size)
        alpha = im.getchannel('A').getextrema() if im.mode == 'RGBA' else (255, 255)
        bounds = list(im.getchannel('A').point(lambda a: 255 if a > 16 else 0).getbbox()) if transparent else [0, 0, *im.size]
    if transparent and alpha[0] != 0:
        raise RuntimeError('Full alpha exterior missing: ' + aid)
    return dict(id=aid, category=category, subject=aid, view='ns' if aid.endswith('_ns') else 'ew',
        state='generated_pending_visual_review', game_ready=False, source_kind='sub2_image_gen',
        model='gpt-image-2.5', quality='high', style_version='warlord_ew6_v025_relief_v0212',
        era='terrain_symbol_not_historical_landcover', source_file=source.relative_to(ROOT).as_posix(),
        source_sha256=sha(source), prompt_file=prompt_file.relative_to(ROOT).as_posix(),
        prompt_sha256=sha(prompt_file), actual_dimensions=dimensions, planned_source_request=[1024, 1024],
        engine_path=f'res://assets/{category}/{aid}.png', planned_engine_path=f'res://assets/{category}/{aid}.png',
        runtime_import_max_dimension=512, background='transparent' if transparent else 'opaque_seamless',
        alpha_min=alpha[0], alpha_bounds=bounds, revision='relief_v0212_r001',
        image_modified=False, manual_compositing=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', default='')
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--install-reviewed', action='store_true')
    args = parser.parse_args()
    jobs = [job for job in plan() if not args.only or job[1] in args.only.split(',')]
    if args.install_reviewed:
        for job in jobs:
            if not (RAW / job[1] / 'r001/source.png').exists():
                raise SystemExit('Generate and inspect first: ' + job[1])
    rows, failures = [], []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        pending = {pool.submit(generate, job): job[1] for job in jobs}
        for future in as_completed(pending):
            try:
                rows.append(future.result())
                print(pending[future] + ': immutable source ready', flush=True)
            except Exception as error:
                failures.append(dict(id=pending[future], reason=str(error)))
                print(str(error), flush=True)
    if args.install_reviewed and not failures:
        path = P / 'assets/manifest.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        current = {row['id']: row for row in data['assets']}
        for row in rows:
            previous = current.get(row['id'])
            history = previous.get('revision_history', []) if previous else []
            if previous and previous['source_sha256'] != row['source_sha256']:
                history += [{key: previous.get(key) for key in ['revision', 'source_file', 'source_sha256', 'prompt_file', 'prompt_sha256']}]
            row['revision_history'] = history
            row['visual_review'] = 'complete source inspected; silhouette/material consistency provisional; formal release approval pending'
            dest = P / row['engine_path'].removeprefix('res://')
            shutil.copyfile(ROOT / row['source_file'], dest)
            current[row['id']] = row
        data['assets'] = sorted(current.values(), key=lambda row: row['id'])
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        visuals = dict(format=1, alpha_threshold_for_measurement=16, source_pngs_modified=False,
                       full_texture_draw=True, records={row['id']: dict(
                           dimensions=row['actual_dimensions'], alpha_bounds=row['alpha_bounds'],
                           source_sha256=row['source_sha256']) for row in rows if row['category'] == 'scenery'})
        (P / 'presentation/data/relief_visuals.json').write_text(
            json.dumps(visuals, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    report = dict(passed=not failures, requested=len(jobs), installed=args.install_reviewed,
                  assets=sorted(rows, key=lambda row: row['id']), failures=failures,
                  route='sub2-image-gen/gpt-image-2.5', source_images_modified=False, manual_compositing=False)
    (P / 'reports/relief_material_generation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    raise SystemExit(bool(failures))


if __name__ == '__main__':
    main()
