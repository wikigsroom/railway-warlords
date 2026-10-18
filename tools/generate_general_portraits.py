"""Generate whole dated portrait originals through the required Sub2 route.

No source raster is edited, cropped, packed, mirrored or painted over. Installation
is a separate action after inspecting every complete original. Reference years are
illustration briefs, never claims that a source photograph was taken that year.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from PIL import Image

P = Path(__file__).resolve().parents[1]
ROOT = P.parents[1]
RAW = ROOT / 'output/imagegen/warlord/portraits_v0222'
SKILL = Path('C:/Users/carzy/.codex/skills/sub2-image-gen/scripts/sub2_image_gen.py')
STYLE = '''ONE complete original historical strategy-game portrait, chest-up, near frontal
three-quarter view, level shoulders, eyes toward the viewer. Premium painted military
atlas art: confident fine charcoal contours, rich but restrained warm skin planes,
muted olive, charcoal and slate fabric, small dusty brass accents, upper-left light,
dimensional face and woven clothing. Harmonize with a steel-gray/brass/parchment HUD.
NOT photorealistic, anime, caricature, glossy 3D, propaganda poster or fantasy.
The named real historical person must be recognizable from documented portraits,
not a generic officer. Individual face structure, eyes, hairline and facial hair matter.
This is an interpretive game illustration, not an archival photograph or a claim of
exact documentary reconstruction. Do not fabricate medals, ranks or invented insignia.
Plain unmarked clothing; no modern camouflage, post-1949 uniforms, invented armor,
flags, background scene, lettering, nameplate, frame, seal, watermark or other people.
Entire head, hair/cap and both shoulders within generous clear margins. Subject occupies
the middle 78 percent of a square canvas. Fully transparent exterior and gaps, alpha
zero, no paper rectangle, vignette, fog, shadow disc or pedestal. ONE single portrait,
never a collage, sheet, board, strip or multiple panels.
'''

# The source register distinguishes observed reference collections from the requested
# illustration date. Identity/age briefs do not claim exact year-specific photographs.
SPECS = [
 ('lin_zexu','林则徐',1785,[1840], 'Qing civil official in a dark navy high-collar robe and a restrained Qing official winter hat. Long narrow dark moustache and beard, resolute scholarly face. NOT an emperor or Republican general.', ['https://digitalarchive.npm.gov.tw/Collection/Detail/28680?dep=P']),
 ('zeng_guofan','曾国藩',1811,[1860], 'Qing scholar-official and Xiang Army organizer, dark indigo official robe, sober Qing official hat, long thin beard, serious broad forehead. No modern peaked cap.', ['https://afe.easia.columbia.edu/special/china_1750_taiping.htm']),
 ('li_hongzhang','李鸿章',1823,[1860,1890,1900], 'Qing statesman, long narrow face, moustache and long pointed beard, dark blue official robe, small restrained Qing official hat. Facial hair and hairline age naturally for the requested year; NOT the same elderly man in every year.', ['https://www.npg.org.uk/collections/search/portrait/mw225127/Li-Hongzhang-Li-Hung-Chang']),
 ('yamagata_aritomo','山县有朋',1838,[1890,1900,1917], 'Meiji Japanese military statesman, distinctive long face, high forehead, receding hairline and moustache, dark high-collar Meiji officer tunic, bareheaded. Older variant has gray-white facial hair and a thinner hairline. No invented medal rows.', ['https://www.ndl.go.jp/portrait/e/datas/208/']),
 ('waldersee','瓦德西',1832,[1900], 'Alfred von Waldersee, elderly Prussian field marshal, bareheaded with receding gray hair, distinctive pale moustache and side whiskers, dark Prussian blue high-collar tunic, understated gold shoulder cords. No spiked helmet, no Nazi-era symbols.', ['https://www.nam.ac.uk/explore/boxer-rebellion']),
 ('kuropatkin','库罗帕特金',1848,[1890,1900], 'Aleksei Nikolaevich Kuropatkin, Imperial Russian officer, distinctive broad forehead, short neat hair and full thick moustache. Dark Imperial Russian high-collar officer tunic, bareheaded, simple shoulder boards with no invented symbols. No Soviet uniform.', ['https://gallica.bnf.fr/ark:/12148/btv1b530368130']),
 ('sun_yat_sen','孙中山',1866,[1917], 'Sun Yat-sen, recognizably distinctive high forehead, swept-back short dark hair, thin neat moustache, dark plain Western formal suit, white shirt and dark tie, bareheaded. Civilian political leader, not a khaki field general.', ['https://www.sunyat-sen.org/portal/list/index.html?id=216']),
 ('duan_qirui','段祺瑞',1865,[1917,1927], 'Duan Qirui, recognizably distinctive Beiyang statesman face and receding hairline, neatly groomed short moustache, plain dark high-collar tunic, bareheaded. Age-appropriate gray in the later version. No fantasy decorations.', ['https://manifold.uhpress.hawaii.edu/projects/the-northern-expedition']),
 ('chiang_kai_shek','蒋介石',1887,[1927,1940], 'Chiang Kai-shek, distinctive narrow face, high receding forehead, closely shaven head, very thin neat moustache. Plain khaki high-collar National Revolutionary Army officer tunic, bareheaded, no invented medals or insignia. Do not portray him as a white-haired postwar old man.', ['https://film.iwmcollections.org.uk/record/17738']),
 ('li_zongren','李宗仁',1891,[1927,1940], 'Li Zongren, distinctive long oval face, short dark hair, restrained thin moustache, plain olive-khaki National Revolutionary Army high-collar tunic and plain peaked cap. Compact sober proportions, not a generic Zhang Zuolin face.', ['https://manifold.uhpress.hawaii.edu/projects/the-northern-expedition']),
 ('bai_chongxi','白崇禧',1893,[1927,1940], 'Bai Chongxi, distinctive lean narrow face, sharp cheekbones, short tidy hair and thin moustache, plain olive-khaki National Revolutionary Army high-collar tunic, bareheaded. Intelligent alert expression, no invented medals.', ['https://manifold.uhpress.hawaii.edu/projects/the-northern-expedition']),
 ('mao_zedong','李德胜',1893,[1927,1940], 'Mao Zedong, distinctive broad forehead, long dark hair parted near the center and brushed back, clean-shaven, recognizable broad face and chin. For 1927 use a dark plain Chinese long gown with upright collar and a youthful slender face. For 1940 use a simple washed slate-gray cotton stand-collar jacket, bareheaded and middle-aged. No post-1949 suit, medals or red-star cap.', ['https://www.12371.cn/2021/12/26/ARTI1640485049308845.shtml']),
 ('peng_dehuai','彭德怀',1898,[1940], 'Peng Dehuai, distinctive strong square face, heavy eyebrows and close-cropped hair, clean-shaven, plain worn gray Eighth Route Army cotton tunic and soft two-button field cap with short brim, no insignia. No 1955 marshal shoulder boards or medals.', ['https://photo.81.cn/tsjs/2014-09/23/content_6150269_25.htm']),
 ('tojo_hideki','东条英机',1884,[1940], 'Hideki Tojo, distinctive balding head, round wire spectacles and short neat moustache. Plain khaki Imperial Japanese Army high-collar tunic, bareheaded. Neutral archival expression, no heroic propaganda or invented medals.', ['https://www.ndl.go.jp/portrait/e/datas/142/']),
 ('yamashita_tomoyuki','山下奉文',1885,[1940], 'Tomoyuki Yamashita, distinctive broad full face and strong cheeks, very short hair, small neat moustache, plain khaki Imperial Japanese Army tunic and plain peaked cap. Neutral documentary expression, not Tojo, no spectacles or invented medals.', ['https://www.awm.gov.au/collection/C47879']),
 ('alexei_kaledin','卡列金',1861,[1917], 'Aleksei Maksimovich Kaledin, Don Cossack general, distinctive broad face, strong gray moustache, short gray hair, dark Imperial Russian high-collar tunic, plain dark field cap with subdued red band. No Soviet insignia or Red Army uniform.', ['https://commons.wikimedia.org/wiki/File:A._Kaledin_by_Artsybushev.jpg']),
]

REVISIONS = {
    'portrait_lin_zexu_1840': ('r002', '\nIMPORTANT FRAMING CORRECTION: Make the entire bust SMALLER, no more than 72 percent of canvas width and height. Leave at least 12 percent fully transparent space ABOVE the tallest hat finial. The complete hat ornament must be visible and must never touch the canvas. Keep at least 8 percent fully transparent margin on both sides and below the chest. Clean natural alpha edges, without any colored outline or fringe.\n'),
    'portrait_li_hongzhang_1900': ('r002', '\nIMPORTANT FRAMING CORRECTION: Make the entire bust SMALLER, no more than 72 percent of canvas width and height. Leave at least 12 percent fully transparent space ABOVE the tallest hat finial. The complete red hat ornament must be visible and must never touch the canvas. Keep at least 8 percent fully transparent margin on both sides and below the chest.\n'),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def jobs():
    for gid, name, born, years, brief, sources in SPECS:
        for year in years:
            aid = f'portrait_{gid}_{year}'
            prompt = STYLE + f'\nSUBJECT: {name} ({gid}), interpreted around {year}, approximately {year-born} years old.\n{brief}\n'
            revision, extra = REVISIONS.get(aid, ('r001', ''))
            prompt += extra
            if gid=='mao_zedong':
                # Replaying the two first-run sources keeps their exact prompt
                # bytes; public readable transcriptions use the approved alias.
                prior=RAW/aid/revision/'prompt.txt'
                if prior.exists():
                    stored=prior.read_text(encoding='utf-8')
                    legacy=''.join(map(chr,[27611,27901,19996]))
                    if stored.replace(legacy,'李德胜')==prompt:prompt=stored
            yield dict(id=aid, general_id=gid, subject=name, reference_year=year,
                       prompt=prompt, revision=revision, reference_urls=sources,
                       reference_scope='Identity/period research; no exact same-year photographic reconstruction claimed')


def generate(row):
    folder = RAW / row['id'] / row['revision']
    folder.mkdir(parents=True, exist_ok=True)
    prompt, source = folder/'prompt.txt', folder/'source.png'
    if prompt.exists() and prompt.read_text(encoding='utf-8') != row['prompt']:
        raise ValueError('Immutable prompt conflict: '+row['id'])
    if not prompt.exists(): prompt.write_text(row['prompt'], encoding='utf-8')
    if not source.exists():
        with (folder/'generation.log').open('w',encoding='utf-8') as log:
            result = subprocess.run([sys.executable,str(SKILL),'generate','--model','gpt-image-2.5',
                '--quality','high','--size','1024x1024','--background','transparent',
                '--prompt-file',str(prompt),'--out',str(source)],stdout=log,stderr=subprocess.STDOUT,timeout=900)
        if result.returncode or not source.exists():
            raise ValueError('Sub2 generation failed; inspect own generation.log: '+row['id'])
    with Image.open(source) as im:
        if im.mode!='RGBA' or im.getchannel('A').getextrema()[0]!=0:
            raise ValueError('Transparent original required: '+row['id'])
        dimensions=list(im.size)
    return {k:v for k,v in row.items() if k!='prompt'} | dict(
        source_file=source.relative_to(ROOT).as_posix(),source_sha256=sha(source),
        prompt_file=prompt.relative_to(ROOT).as_posix(),prompt_sha256=sha(prompt),
        actual_dimensions=dimensions,source_kind='sub2_image_gen',model='gpt-image-2.5',quality='high',
        image_modified=False,manual_compositing=False,reviewed=False)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workers',type=int,default=2)
    parser.add_argument('--only',nargs='*')
    parser.add_argument('--install-reviewed',action='store_true')
    args=parser.parse_args()
    selected=[r for r in jobs() if not args.only or r['id'] in args.only]
    if args.install_reviewed:
        review=json.loads((RAW/'review.json').read_text(encoding='utf-8'))
        reviewed={r['id']:r for r in review['originals']}
        rows=[generate(r) for r in selected]
        manifest_path=P/'assets/manifest.json'
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        known={r['id']:r for r in manifest['assets']}
        for row in rows:
            evidence=reviewed[row['id']]
            if not evidence['viewed_complete_original'] or evidence['sha256']!=row['source_sha256'] or not evidence['accepted']:
                raise ValueError('Complete source-image review required: '+row['id'])
            source=ROOT/row['source_file'];target=P/'assets/portrait'/(row['id']+'.png')
            if target.exists() and sha(target)!=sha(source):raise ValueError('Immutable installed portrait conflict')
            shutil.copyfile(source,target)
            entry=row | dict(category='portrait',view='three_quarter',era=str(row['reference_year']),
                state='source_reviewed_runtime_pending',game_ready=False,style_version='warlord_portrait_v0222',
                planned_source_request=[1024,1024],runtime_import_max_dimension=512,background='transparent',
                alpha_min=0,engine_path='res://'+target.relative_to(P).as_posix())
            if row['id'] in known and known[row['id']]['source_sha256']!=entry['source_sha256']:
                raise ValueError('Manifest source conflict')
            known[row['id']]=entry
        manifest['assets']=list(known.values())
        manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(dict(installed=len(rows),originals_modified=False)))
        return
    records=[];failures=[]
    with ThreadPoolExecutor(max_workers=max(1,args.workers)) as pool:
        tasks={pool.submit(generate,row):row['id'] for row in selected}
        for future in as_completed(tasks):
            aid=tasks[future]
            try:
                records.append(future.result());print(aid+': whole original ready',flush=True)
            except Exception as e:
                failures.append(dict(id=aid,error=str(e)));print(aid+': FAILED',flush=True)
    RAW.mkdir(parents=True,exist_ok=True)
    report=dict(requested=len(selected),generated=len(records),passed=not failures,
        records=records,failures=failures,source_route='sub2-image-gen/gpt-image-2.5/high',
        source_rasters_modified=False,formal_art_approval=False)
    (RAW/'generation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    raise SystemExit(1 if failures else 0)


if __name__=='__main__': main()
