"""Generate immutable atlas scenery directly with the requested Sub2 route."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import hashlib, json, shutil, subprocess, sys, argparse
from PIL import Image

P=Path(__file__).resolve().parents[1]; ROOT=P.parents[1]
CLI=Path('C:/Users/carzy/.codex/skills/sub2-image-gen/scripts/sub2_image_gen.py')
STYLE=('ONE complete independent transparent game scenery asset. 1920s Chinese military atlas, '
       'beautiful hand-painted woodcut illustration, weathered ochre parchment highlights, '
       'muted olive-green vegetation, graphite rock shadows. Near overhead light-isometric view, '
       'north up, light from upper left, short soft shadow lower right. Organic finely inked '
       'contours and convincing volume, elegant restrained historical strategy-map art. '
       'No photo, glossy 3D, pixel art, anime, fantasy, UI, labels, letters, hex grid, border, '
       'watermark or collage. Transparent alpha exterior, no square terrain patch or pedestal. '
       'Entire subject and translucent ground shadow fit inside the central 80% with clear margins. ')
SUBJECTS={
 'scenery_jiumenkou_wall':'A single compact cartographic landmark for the actual Jiumenkou water Great Wall in northern China, as weathered in the early 1920s. A straight old Chinese grey-stone fortified wall spanning a shallow river channel, with EXACTLY NINE separate side-by-side rectangular low water-gate openings below the wall, formed by EIGHT short wedge-shaped stone piers. All nine openings must be visible and countable from a near-frontal light-isometric angle. Modest crenellations above and two low Chinese brick bridgehead enclosures at opposite ends. One small weathered tiled gate tower. Rough pale stone riverbed, tiny visible water confined within the compact landmark; no long invented river course. Authentic Ming Chinese masonry, muted graphite stone with ochre light. No Roman aqueduct, western castle, rail track, train station, ornamental tourist landscaping, modern dam, intact modern reconstruction, tall exaggerated towers or vegetation slab. Transparent outside the complete landmark footprint. This is a stylized map symbol of the real structure, not a photoreal site reconstruction.',
 'scenery_yanshan_ridge':'One compact connected northern-Chinese hard-rock mountain ridge, inspired by the actual Yanshan landscape: broad weathered angular granite and gneiss slopes, two moderately high rounded rocky summits, shallow branching gullies, sparse muted scrub at the base. Cartographic terrain symbol rather than a literal named peak. Substantial landscape silhouette with readable rock relief. No needle peaks, limestone karst towers, exotic alpine glaciers or imaginary dense forest.',
 'scenery_hill_grove':'One low rounded dry ochre northern-Chinese hillside with sparse mature olive-green trees, small rocks and pale grassy slopes. Broad shallow silhouette, no tall peak.',
 'scenery_forest_pine':'One naturally irregular dense cluster of nine northern-Chinese dark olive pine trees of varying heights. Individual pointed crowns, visible inked trunks, airy irregular edge, no ground slab.',
 'scenery_forest_mixed':'One naturally irregular small copse of six northern-Chinese olive deciduous trees of different heights, finely painted foliage and visible trunks. No garden layout or terrain slab.',
 'scenery_farm_fields':'One modest early-1920s north-Chinese field parcel: thin irregular earthen field boundaries, alternating pale harvested and muted green crops, two small trees beside an unpaved path. Very flat sparse scenery with transparent spaces between small field strips, no city or road network.',
 'scenery_village':'One compact early-Republican northern-Chinese rural hamlet: three small grey-brick courtyard houses with weathered charcoal tiled roofs and a modest tree. Near overhead light-isometric view, no roads extending beyond the asset, no modern structures, entire footprint compact.',
 'scenery_walled_city':'One compact beautiful early-1920s northern-Chinese county town: an old grey-brick gate tower, a short section of modest city wall, several weathered tiled roofs and a small courtyard. Calm authentic light-isometric architecture, no fantasy castle or western keep. Readable substantial city silhouette.',
 'scenery_station_town':'One compact beautiful early-1920s Chinese railway station precinct: a grey-brick two-storey station house with charcoal tiled roofs, one low warehouse, a platform and two telegraph poles. No train, rails, labels, national flags or modern architecture. Light-isometric substantial map landmark.'
}

def generate(item,revision='r001'):
 aid,subject=item;folder=ROOT/'output/imagegen/warlord/raw'/aid/revision;folder.mkdir(parents=True,exist_ok=True)
 prompt=folder/'prompt.txt';out=folder/'source.png'
 if not prompt.exists():prompt.write_text(STYLE+subject,encoding='utf-8')
 if not out.exists():
  result=subprocess.run([sys.executable,str(CLI),'generate','--model','gpt-image-2.5','--quality','high','--size','1024x1024','--background','transparent','--prompt-file',str(prompt),'--out',str(out)],capture_output=True,timeout=360)
  if result.returncode or not out.exists():return {'id':aid,'state':'generation_failed','exit_code':result.returncode}
 with Image.open(out) as im:
  dimensions=list(im.size);alpha_min=im.getchannel('A').getextrema()[0] if im.mode=='RGBA' else 255
 if alpha_min==255:return {'id':aid,'state':'review_rejected','reason':'transparent_exterior_missing'}
 dest=P/'assets/scenery'/f'{aid}.png';dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(out,dest)
 return {'id':aid,'category':'scenery','subject':subject,'view':'light_isometric','state':'generated_pending_visual_review','source_kind':'sub2_image_gen','model':'gpt-image-2.5','quality':'high','style_version':'warlord_atlas_v2_scenery','era':'1920-1924','source_file':out.relative_to(ROOT).as_posix(),'source_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'prompt_file':prompt.relative_to(ROOT).as_posix(),'actual_dimensions':dimensions,'planned_engine_path':f'res://assets/scenery/{aid}.png','engine_path':f'res://assets/scenery/{aid}.png','background':'transparent','game_ready':False,'manual_compositing':False,'revision':revision}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--only',choices=list(SUBJECTS));ap.add_argument('--revision',default='r001');args=ap.parse_args()
 if not args.revision.startswith('r') or not args.revision[1:].isdigit():raise SystemExit('Revision must be r plus digits.')
 records=[]
 with ThreadPoolExecutor(max_workers=2) as executor:
  for future in as_completed([executor.submit(generate,item,args.revision) for item in SUBJECTS.items() if args.only is None or item[0]==args.only]):
   record=future.result();records.append(record);print(record['id'],record['state'],flush=True)
 manifest=P/'assets/manifest.json';data=json.loads(manifest.read_text(encoding='utf-8'));ids={r['id'] for r in records}
 for record in records:
  previous=next((a for a in data['assets'] if a['id']==record['id']),None)
  if previous and previous.get('revision')!=record.get('revision'):
   record['revision_history']=previous.get('revision_history',[])+[{k:previous.get(k) for k in ['revision','source_file','source_sha256','prompt_file']}]
 data['assets']=[a for a in data['assets'] if a['id'] not in ids]+records
 manifest.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 (P/'reports/scenery_generation.json').write_text(json.dumps({'route':'sub2-image-gen/gpt-image-2.5','manual_compositing':False,'results':records},ensure_ascii=False,indent=2),encoding='utf-8')
 if any(r['state']!='generated_pending_visual_review' for r in records):raise SystemExit(1)
if __name__=='__main__':main()
