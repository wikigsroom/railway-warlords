"""Generate four independent Sub2 settlement sprites; preserve every PNG byte."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
from PIL import Image

P = Path(__file__).resolve().parents[1]
ROOT = P.parents[1]
RAW = ROOT / 'output/imagegen/warlord/settlements_v023'
CLI = Path('C:/Users/carzy/.codex/skills/sub2-image-gen/scripts/sub2_image_gen.py')
STYLE = """A premium 1920s Chinese military atlas game sprite. Warm sandy paper highlights,
coal-black woodcut ink contours, muted olive and gray-blue tiled roofs, restrained aged watercolor.
Near-overhead elevated 60-degree camera, slight isometric perspective, soft upper-left light.
The same elegant fine engraved illustration language as a period Chinese military map.
One compact coherent independent settlement object; NOT an asset sheet, collage or full scene.
Transparent alpha exterior, no background, checkerboard, circular ground disc, hexes, labels,
text, flag, emblems, border or watermark. No fantasy, palace exaggeration, glossy 3D, cartoon,
modern tower, asphalt, satellite dish, cars or electric transmission tower.
Generous 12 percent transparent margins on all sides, all buildings fully inside canvas.
Centered low wide 1.45:1 silhouette. Legible at small tactical-map size.
"""
SUBJECTS = {
    'scenery_historic_village': 'A modest northern Chinese village around 1920: five small gray-brick courtyard farmhouses, low earthen boundary walls, one haystack, a handcart and sparse weathered earth paths. The houses are the focus, no hills, rivers or invented geographic surroundings. Human figures unnecessary. Rustic small scale, asymmetrical arrangement.',
    'scenery_historic_market': 'A northern Chinese market town around 1920: a short compact street of eight low tiled-roof shop houses, two plain cloth market awnings, a timber cart and restrained telegraph pole. No writing on shop fronts. Dense but quiet and orderly, clearly larger than a village, with no city wall or provincial palace.',
    'scenery_historic_county': 'An early Republican Chinese county seat around 1920: one restrained gray-brick gate, low surviving rectangular city walls, six courtyard blocks, a modest county-government compound, tiled roofs and two small street shop rows. Worn practical northern architecture, no imperial dragon ornament. A compact legible county fortress rather than a gigantic metropolis.',
    'scenery_historic_capital': 'An early Republican Chinese provincial capital around 1920: an elegant compact surviving walled old-city block with ten low courtyard and shop compounds, a dignified but modest provincial administrative courtyard, one restrained clockless Western-influenced public building, and clearly readable principal gate. Mixed late-Qing and early-Republican architecture, no imperial palace, skyscrapers or invented landmark. Larger organized silhouette than a county town.'
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def generate(item):
    name, subject = item
    folder = RAW / name / 'r001'
    folder.mkdir(parents=True, exist_ok=True)
    prompt = folder / 'prompt.txt'
    source = folder / 'source.png'
    prompt.write_text(STYLE + '\nSubject: ' + subject + '\n', encoding='utf-8')
    if not source.exists():
        with (folder / 'generation.log').open('w', encoding='utf-8') as out:
            job = subprocess.run([sys.executable, str(CLI), 'generate', '--model', 'gpt-image-2.5', '--quality', 'high', '--size', '1024x1024', '--background', 'transparent', '--prompt-file', str(prompt), '--out', str(source)], stdout=out, stderr=subprocess.STDOUT, timeout=900)
        if job.returncode or not source.is_file():
            raise RuntimeError('Sub2 generation failed: ' + name + '; inspect its gateway diagnostic log.')
    with Image.open(source) as im:
        size=list(im.size)
        alpha=im.getchannel('A').getextrema()[0] if im.mode=='RGBA' else 255
    if alpha!=0:
        raise RuntimeError('Sub2 did not provide transparent alpha: ' + name + '. Source remains unchanged.')
    destination=P/'assets/scenery'/(name+'.png')
    shutil.copyfile(source,destination)
    if sha(source)!=sha(destination):
        raise RuntimeError('Original PNG copy mismatch.')
    return {'id':name,'category':'scenery','subject':subject,'view':'atlas','state':'generated_pending_visual_review','game_ready':False,'source_kind':'sub2_image_gen','model':'gpt-image-2.5','quality':'high','style_version':'warlord_atlas_v2_settlements','era':'1920-1924','source_file':source.relative_to(ROOT).as_posix(),'source_sha256':sha(source),'prompt_file':prompt.relative_to(ROOT).as_posix(),'prompt_sha256':sha(prompt),'actual_dimensions':size,'planned_source_request':[1024,1024],'engine_path':'res://'+destination.relative_to(P).as_posix(),'planned_engine_path':'res://'+destination.relative_to(P).as_posix(),'runtime_import_max_dimension':512,'background':'transparent','alpha_min':alpha,'revision':'settlements_v023_r001','image_modified':False}

def main():
    path=P/'assets/manifest.json';manifest=json.loads(path.read_text(encoding='utf-8'))
    records={record['id']:record for record in manifest['assets']};completed=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(generate,item) for item in SUBJECTS.items()]
        for future in as_completed(futures):
            record=future.result();records[record['id']]=record;completed.append(record['id'])
            manifest['assets']=sorted(records.values(),key=lambda record:record['id'])
            path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print(record['id']+': original PNG installed',flush=True)
    (P/'reports/settlement_asset_generation.json').write_text(json.dumps({'passed':len(completed)==4,'assets':completed,'route':'sub2-image-gen / gpt-image-2.5 high','manual_compositing':False,'image_modified':False},indent=2),encoding='utf-8')

if __name__=='__main__':main()
