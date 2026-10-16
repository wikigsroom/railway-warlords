"""Install byte-identical Sub2 relief revisions; keep all older raw files immutable."""
import hashlib
import json
import shutil
from pathlib import Path
from PIL import Image

P=Path(__file__).resolve().parents[1]
ROOT=P.parents[1]
REVISIONS={
    'scenery_yanshan_ridge':('r004','f47baf3e4d0471c52d73b716ffeda030a2c99d686b7968911ac46061e46ec557','Connected uneven bare mountain ridge, generic elevation legend; no geological or vegetation claim.'),
    'scenery_hill_grove':('r003','abd39b4fe5b3107090d41ed1c833d296735e1550ad3b29c2c473e74c002ec852','Low connected treeless foothills. Stable asset ID retained; no historical grove distribution implied.'),
}

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    path=P/'assets/manifest.json';manifest=json.loads(path.read_text(encoding='utf-8'));records=[]
    for aid,(revision,expected,subject) in REVISIONS.items():
        source=ROOT/'output/imagegen/warlord/raw'/aid/revision/'source.png'
        prompt=source.with_name('prompt.txt')
        if not prompt.is_file() or digest(source)!=expected:raise SystemExit('Unverified raw revision: '+aid)
        with Image.open(source) as image:
            if image.mode!='RGBA' or image.getchannel('A').getextrema()[0]!=0:raise SystemExit('Missing transparent exterior: '+aid)
            dimensions=list(image.size)
        item=next(a for a in manifest['assets'] if a['id']==aid)
        history=list(item.get('revision_history',[]))
        if item.get('revision')!=revision:
            history.append({key:item.get(key) for key in ('revision','source_file','source_sha256','prompt_file')})
        item.update({'revision':revision,'revision_history':history,'subject':subject,'source_file':source.relative_to(ROOT).as_posix(),'source_sha256':expected,'prompt_file':prompt.relative_to(ROOT).as_posix(),'actual_dimensions':dimensions,'style_version':'warlord_atlas_v3_relief','state':'generated_pending_visual_review','game_ready':False,'manual_compositing':False,'source_kind':'sub2_image_gen','model':'gpt-image-2.5','quality':'high'})
        destination=P/'assets/scenery'/(aid+'.png');shutil.copyfile(source,destination)
        records.append({'id':aid,'revision':revision,'source_sha256':expected,'engine_sha256':digest(destination),'actual_dimensions':dimensions,'native_alpha_review_pending':True,'all_original_bytes_preserved':True})
    path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    report={'route':'sub2-image-gen/gpt-image-2.5','installed_revisions':records,'other_candidates_retained':['scenery_yanshan_ridge/r003','scenery_hill_grove/r002'],'manual_compositing':False,'full_release_art_review_complete':False}
    (P/'reports/relief_generation_v6.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'installed':len(records),'source_bytes_unchanged':all(r['source_sha256']==r['engine_sha256'] for r in records)},ensure_ascii=True))

if __name__=='__main__':main()
