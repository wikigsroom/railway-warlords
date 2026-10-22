"""Install the four reviewed Sub2 originals; never write or modify image pixels."""
from datetime import datetime, timezone
from pathlib import Path
import copy
import hashlib
import json
import re
import shutil

from PIL import Image

HERE=Path(__file__).resolve().parent
if HERE.name=='tools' and (HERE.parent/'project.godot').exists():
    P=HERE.parent
    ROOT=P.parents[1]
    HERE=ROOT/'output/imagegen/warlord/ground_hierarchy_v0235'
else:
    ROOT=HERE.parents[3]
    P=ROOT/'game/railway_warlords'
FAMILIES=['temperate_meadow','alluvial_loam','flood_meadow','subtropical_humus']


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def immutable_copy(source, target, checksum):
    assert sha(source)==checksum
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        assert sha(target)==checksum,'Never overwrite an original: '+str(target)
    else:
        shutil.copyfile(source,target)
    assert sha(target)==checksum


def main():
    publication=read(ROOT/'output/local-map-refinement-v0234/publication_receipt_v0234.json')
    assert publication['passed'] and publication['commit']=='5fdd2de0348650307aec304d3175d334f62da610'
    review=read(HERE/'source_review.json')
    native=read(HERE/'native_visual_review.json')
    assert review['source_route']=='sub2-image-gen/gpt-image-2.5/high'
    assert native['passed_native_rendering_samples']==3 and native['source_originals_actually_viewed']==4
    sources={row['family']:row for row in review['assets']}
    assert set(sources)==set(FAMILIES)
    catalog_path=P/'presentation/data/ground_macro_catalog.json'
    catalog=read(catalog_path)
    assert catalog['material_identity_revision']=='painted_lowland_v0231_r001','Inspect an existing later integration rather than reapply it.'
    parent_plan_path=P/catalog['source_plan_file']
    assert sha(parent_plan_path)==catalog['source_plan_sha256']
    parent_plan=read(parent_plan_path)
    manifest_path=P/'assets/manifest.json'
    manifest=read(manifest_path)
    assets={row['id']:row for row in manifest['assets']}
    assert len(assets)==2509 and len(catalog['records'])==20
    previous_asset_ids=set(assets)
    provenance_path=P/'docs/asset-provenance/index.json'
    provenance=read(provenance_path)
    portable={row['id']:row for row in provenance['assets']}
    assert set(portable)==previous_asset_ids
    geography=P/'presentation/data/terrain_surface_regions.json'
    geography_sha=sha(geography)
    records=copy.deepcopy(catalog['records'])
    superseded=set(catalog['superseded_asset_ids'])
    incoming={}
    installed=[]
    for family in FAMILIES:
        source=sources[family]
        assert source['whole_original_actually_viewed'] and source['alpha_range']==[255,255]
        original=HERE/source['original_file']
        prompt=HERE/source['prompt_file']
        assert sha(original)==source['source_sha256'] and sha(prompt)==source['prompt_sha256']
        old_id=records[family]['asset_id']
        row=copy.deepcopy(assets[old_id])
        identifier='tile_ground_hierarchy_v0235_'+family
        engine_path='res://assets/tile/'+identifier+'.png'
        with Image.open(original) as im:
            rgba=im.convert('RGBA')
            assert list(im.size)==[1254,1254] and rgba.getextrema()[3]==(255,255)
            # Analysis only. No analysis image or modified PNG is ever saved.
            fingerprint=hashlib.sha256(rgba.resize((24,24)).tobytes()).hexdigest()
        row.update(id=identifier,source_file=original.relative_to(ROOT).as_posix(),
                   prompt_file=prompt.relative_to(ROOT).as_posix(),
                   source_sha256=source['source_sha256'],prompt_sha256=source['prompt_sha256'],
                   engine_path=engine_path,planned_engine_path=engine_path,
                   style_version='warlord_ground_hierarchy_v0235',revision='ground_hierarchy_v0235_r001',
                   source_revision='r001',actual_dimensions=[1254,1254],planned_source_request=[1024,1024],
                   alpha_min=255,alpha_coverage_mean=1.0,alpha_bounds=[0,0,1254,1254],
                   analysis_fingerprint_rgba_24=fingerprint,runtime_import_max_dimension=384,
                   state='generated_source_reviewed_runtime_trial',game_ready=False,
                   visual_review='Four whole originals and three uninstalled native viewports inspected. Normal imports, integration and formal art approval are separate.',
                   image_modified=False,manual_compositing=False)
        target=P/engine_path.removeprefix('res://')
        immutable_copy(original,target,row['source_sha256'])
        immutable_copy(prompt,P/'docs/asset-prompts'/(identifier+'.txt'),row['prompt_sha256'])
        # Configure only the four new imports. Let Godot create their fresh
        # resource UIDs and imported textures; keep all existing metadata intact.
        template=(P/'assets/tile'/(old_id+'.png.import')).read_text(encoding='utf-8')
        old_res='res://assets/tile/'+old_id+'.png'
        old_hash=hashlib.md5(old_res.encode()).hexdigest()
        new_hash=hashlib.md5(engine_path.encode()).hexdigest()
        assert old_hash in template
        template=re.sub(r'^uid=.*\n','',template,flags=re.MULTILINE)
        template=template.replace(old_id,identifier).replace(old_hash,new_hash)
        assert 'process/size_limit=384' in template and 'mipmaps/generate=true' in template
        (target.with_suffix('.png.import')).write_text(template,encoding='utf-8')
        assets[identifier]=row
        portable[identifier]=dict(id=identifier,category='tile',image=engine_path.removeprefix('res://'),
            image_sha256=row['source_sha256'],prompt='docs/asset-prompts/'+identifier+'.txt',
            prompt_sha256=row['prompt_sha256'],source_kind='sub2_image_gen',model='gpt-image-2.5',quality='high',
            original_workspace_source=row['source_file'],image_modified=False,formal_art_approval=False)
        records[family]=dict(asset_id=identifier,source_sha256=row['source_sha256'],actual_dimensions=[1254,1254],
                             **({'world_repeat_period':records[family]['world_repeat_period']} if 'world_repeat_period' in records[family] else {}))
        superseded.add(old_id)
        definition=copy.deepcopy(next(v for v in parent_plan['assets'] if v['family']==family))
        definition.update(id=identifier,prompt=prompt.read_text(encoding='utf-8'),source_revision='r001')
        incoming[family]=definition
        installed.append(dict(id=identifier,family=family,source_sha256=row['source_sha256'],
                              prompt_sha256=row['prompt_sha256'],superseded_id=old_id))
    assert len(assets)==2513 and len(superseded)==46 and len(records)==20
    new_plan=P/'presentation/data/ground_material_plan_v0235.json'
    write(new_plan,dict(format=1,version='0.2.35-development',terrain_type_count=20,
          source_route='sub2-image-gen/gpt-image-2.5/high',parent_plan_file=parent_plan_path.relative_to(P).as_posix(),
          parent_plan_sha256=sha(parent_plan_path),assets=[incoming.get(row['family'],row) for row in parent_plan['assets']],
          scope='Four quieter replacement ground originals; geographic assignments and world-space sampling remain unchanged.',
          source_images_modified=False,manual_compositing=False))
    catalog.update(version='0.2.35-development',records=records,source_plan_file=new_plan.relative_to(P).as_posix(),
                   source_plan_sha256=sha(new_plan),superseded_originals=46,superseded_asset_ids=sorted(superseded),
                   material_identity_revision='quiet_ground_hierarchy_v0235_r001')
    # Preserve existing inventory order and records; append only the four new
    # originals. Reordering thousands of unrelated rows obscures review.
    manifest['assets']=list(assets.values())
    provenance.update(version='0.2.35-development',count=2513,
                      image_bytes=sum((P/row['engine_path'].removeprefix('res://')).stat().st_size for row in assets.values()),
                      assets=list(portable.values()))
    write(manifest_path,manifest)
    write(catalog_path,catalog)
    write(provenance_path,provenance)
    assert sha(geography)==geography_sha
    write(P/'reports/ground_hierarchy_v0235/installation.json',dict(passed=True,
          stage='development_source_installed_import_and_shipping_validation_pending',
          target_revision='0.2.35-development',current_published_version='0.2.34',
          created_at_utc=datetime.now(timezone.utc).isoformat(),installed_new_originals=4,
          active_macro_originals=20,stored_superseded_originals=46,total_registered_rasters=2513,
          source_images_modified=False,manual_compositing=False,geography_assignments_changed=False,
          geography_sha256=geography_sha,formal_art_approval=False,ew6_parity_claimed=False,
          new_shipping_artifact_created=False,assets=installed))
    print('Installed four immutable ground originals. Import and native source validation remain pending.',flush=True)


if __name__=='__main__':
    main()
