"""Independently verify immutable source/prompt/import identity of twenty grounds."""
import json
from pathlib import Path
from PIL import Image, ImageStat, ImageFilter
from build_release import P, ROOT, current_version
from package_delivery import read, require, sha


def main():
    catalog=read(P/'presentation/data/ground_macro_catalog.json')
    plan_path=P/catalog.get('source_plan_file','presentation/data/ground_macro_plan.json')
    require(plan_path.resolve().is_relative_to(P.resolve()),'Plan must remain inside the project')
    plan=read(plan_path)
    manifest={row['id']:row for row in read(P/'assets/manifest.json')['assets']}
    require(catalog['source_plan_sha256']==sha(plan_path),'Immutable plan differs')
    require(len(plan['assets'])==len(catalog['records'])==20,'Twenty types required')
    hashes=set();rows=[]
    for item in plan['assets']:
        row=manifest[item['id']];source=ROOT/row['source_file'];image=P/row['engine_path'].removeprefix('res://')
        prompt=ROOT/row['prompt_file'];portable=P/'docs/asset-prompts'/ (item['id']+'.txt')
        require(sha(source)==sha(image)==row['source_sha256']==catalog['records'][item['family']]['source_sha256'],'Source differs: '+item['id'])
        require(prompt.read_text(encoding='utf-8')==item['prompt'] and sha(prompt)==sha(portable)==row['prompt_sha256'],'Prompt differs')
        require(row['source_kind']=='sub2_image_gen' and row['model']=='gpt-image-2.5' and row['quality']=='high','Generation route differs')
        require(not row['image_modified'] and not row['manual_compositing'],'Transformed source')
        with Image.open(source) as im:
            require(min(im.size)>=1024,'Small source')
            require(im.mode!='RGBA' or im.getchannel('A').getextrema()==(255,255),'Nonopaque material')
            luma=im.convert('L').resize((128,128));smooth=luma.filter(ImageFilter.GaussianBlur(2))
            from PIL import ImageChops
            high_frequency=ImageStat.Stat(ImageChops.difference(luma,smooth)).mean[0]
        imported=image.with_suffix('.png.import').read_text(encoding='utf-8')
        require('process/size_limit=384' in imported and 'mipmaps/generate=true' in imported,'Wrong import budget')
        hashes.add(row['source_sha256']);rows.append(dict(id=item['id'],family=item['family'],source_sha256=sha(source),prompt_sha256=sha(prompt),import_sha256=sha(image.with_suffix('.png.import')),high_frequency_luma_mean_128=round(high_frequency,4)))
    require(len(hashes)==20,'Duplicate original bytes')
    superseded=catalog.get('superseded_asset_ids',[])
    require(len(superseded)==catalog.get('superseded_originals',0),'Superseded inventory differs')
    require(not set(superseded)&{row['id'] for row in rows},'Active and superseded IDs overlap')
    for asset_id in superseded:
        old=manifest[asset_id]
        require(sha(P/old['engine_path'].removeprefix('res://'))==sha(ROOT/old['source_file'])==old['source_sha256'],
                'Previous immutable original differs: '+asset_id)

    report=dict(passed=True,version=current_version(),sources=20,source_route=plan['source_route'],source_images_modified=False,
        art_score=False,geography_assignments_changed=False,formal_art_approval=False,
        source_plan_file=plan_path.relative_to(P).as_posix(),stored_superseded_originals_verified=len(superseded),
        measurement_scope='Analysis-only 128px luminance; no derived image written. Frequency is not an artistic-quality score.',assets=rows)
    (P/'reports/ground_macro_asset_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=True,sources=20,unique_hashes=len(hashes))),flush=True)


if __name__=='__main__':main()
