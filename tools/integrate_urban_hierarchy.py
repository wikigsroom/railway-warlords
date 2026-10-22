"""Install eight reviewed whole originals, preserving all prior inventory rows."""
from datetime import datetime, timezone
from pathlib import Path
import copy
import hashlib
import json
import re
import shutil

from PIL import Image

P = Path(__file__).resolve().parents[1]
ROOT = P.parents[1]
WORK = ROOT / 'output/imagegen/warlord/urban_hierarchy_v0235'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def keep_copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        assert sha(source) == sha(destination), 'Refuse to replace original: ' + str(destination)
    else:
        shutil.copyfile(source, destination)
    assert sha(source) == sha(destination)


def main():
    plan = read(WORK / 'production_plan.json')
    review = read(WORK / 'source_review.json')
    approved = {row['id']: row for row in review['assets']}
    assert len(approved) == len(plan['assets']) == 8
    assert all(row['whole_original_opened'] and not row['rejected'] for row in approved.values())
    manifest_path = P / 'assets/manifest.json'
    provenance_path = P / 'docs/asset-provenance/index.json'
    bank_path = P / 'presentation/data/map_bank_visuals.json'
    manifest, provenance, bank = read(manifest_path), read(provenance_path), read(bank_path)
    assert len(manifest['assets']) == provenance['count'] == 2513, 'Inspect the current revision rather than reinstall.'
    assert len(bank['records']) == bank['additional_count'] == 796 and bank['total_map_assets'] == 870
    assert not (P / 'presentation/data/map_urban_extension_plan.json').exists()
    previous = copy.deepcopy(manifest['assets'])
    previous_sources = copy.deepcopy(provenance['assets'])
    existing = {row['id'] for row in previous}
    installed = []
    active = {}
    for definition in plan['assets']:
        identifier = definition['id']; family = definition['family']
        assert identifier not in existing
        source, prompt = ROOT / definition['source_file'], ROOT / definition['prompt_file']
        assert sha(source) == approved[identifier]['source_sha256']
        assert prompt.read_text(encoding='utf-8') == definition['prompt']
        with Image.open(source) as original:
            rgba = original.convert('RGBA'); alpha = rgba.getchannel('A')
            bounds = list(alpha.point(lambda value: 255 if value > 16 else 0).getbbox())
            dimensions = list(original.size)
            corners = [alpha.getpixel(point) for point in [(0, 0), (original.width - 1, 0), (0, original.height - 1), (original.width - 1, original.height - 1)]]
            assert max(corners) <= 1 and alpha.getextrema()[0] == 0 and alpha.getextrema()[1] >= 240
            fingerprint = hashlib.sha256(rgba.resize((24, 24)).tobytes()).hexdigest()
        engine_path = 'res://assets/building/' + identifier + '.png'
        row = dict(definition, state='generated_source_reviewed_runtime_trial', game_ready=False,
                   source_kind='sub2_image_gen', model='gpt-image-2.5', quality='high',
                   style_version='warlord_urban_hierarchy_v0235', revision='urban_hierarchy_v0235_r001',
                   engine_path=engine_path, planned_engine_path=engine_path, source_sha256=sha(source),
                   prompt_sha256=sha(prompt), actual_dimensions=dimensions, planned_source_request=[1024, 1024],
                   alpha_min=alpha.getextrema()[0], alpha_bounds=bounds, alpha_bounds_threshold_8bit=16,
                   analysis_fingerprint_rgba_24=fingerprint, image_modified=False, manual_compositing=False,
                   background='transparent', formal_art_approval=False,
                   visual_review='Whole independent source inspected; native integration and commercial approval are separate.')
        keep_copy(source, P / engine_path.removeprefix('res://'))
        keep_copy(prompt, P / 'docs/asset-prompts' / (identifier + '.txt'))
        template_id = 'building_bank_county_north_china_001'
        template_res = 'res://assets/building/' + template_id + '.png'
        template = (P / (template_res.removeprefix('res://') + '.import')).read_text(encoding='utf-8')
        template = re.sub(r'^uid=.*\n', '', template, flags=re.MULTILINE)
        template = template.replace(template_id, identifier).replace(hashlib.md5(template_res.encode()).hexdigest(), hashlib.md5(engine_path.encode()).hexdigest())
        assert 'mipmaps/generate=true' in template and 'process/size_limit=384' in template
        (P / (engine_path.removeprefix('res://') + '.import')).write_text(template, encoding='utf-8')
        manifest['assets'].append(row)
        provenance['assets'].append(dict(id=identifier, category='building', image=engine_path.removeprefix('res://'),
            image_sha256=row['source_sha256'], prompt='docs/asset-prompts/' + identifier + '.txt',
            prompt_sha256=row['prompt_sha256'], source_kind='sub2_image_gen', model='gpt-image-2.5', quality='high',
            original_workspace_source=definition['source_file'], image_modified=False, formal_art_approval=False))
        record = {key: row[key] for key in ['category', 'family', 'variant', 'axis', 'region', 'role', 'gate', 'visible_bounds', 'alpha_bounds', 'source_sha256']}
        record['dimensions'] = dimensions
        bank['records'][identifier] = record
        bank['families'].setdefault(family, []).append(identifier)
        active.setdefault(family, []).append(identifier)
        installed.append(row)
    assert manifest['assets'][:2513] == previous and provenance['assets'][:2513] == previous_sources
    bank.update(urban_extension_count=8, additional_count=804, total_map_assets=878, urban_active_families=active)
    provenance.update(version='0.2.35-development', count=2521,
        image_bytes=sum((P / row['image']).stat().st_size for row in provenance['assets']))
    write(manifest_path, manifest); write(provenance_path, provenance); write(bank_path, bank)
    write(P / 'presentation/data/map_urban_extension_plan.json', plan)
    write(P / 'reports/map_urban_extension_generation.json', dict(passed=True, running=False, completed=8,
        source_route='sub2-image-gen/gpt-image-2.5/high', failures=[], assets=installed,
        source_pngs_modified=False, formal_art_approval=False, whole_originals_opened=8))
    report = dict(passed=True, created_at_utc=datetime.now(timezone.utc).isoformat(), source_originals_added=8,
        prior_registered_originals_preserved=2513, registered_originals=2521, bank_sources=804,
        active_families=active, source_images_modified=False, history_or_rule_geography_changed=False,
        stage='development_source_installed_normal_import_and_native_review_pending',
        shipping_exe=False, physical_android_device_tested=False, formal_art_approval=False)
    write(P / 'reports/urban_hierarchy_v0235/installation.json', report)
    print(json.dumps(dict(passed=True, installed=8, originals=2521, normal_import_pending=True)), flush=True)


if __name__ == '__main__':
    main()
