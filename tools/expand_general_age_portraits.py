"""Produce whole, independently generated age-stage originals through Sub2.

Existing originals remain immutable. No source image is aged, cropped or composited.
Installation is deliberately separate from generation and requires individual review.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import json
import shutil
import generate_general_portraits as generator

P=generator.P
ROOT=generator.ROOT
RAW=ROOT/'output/imagegen/warlord/portrait_ages_v0222'

EARLY_FACES={
 'daoguang':'Daoguang Emperor, Aisin-Gioro Minning, based on Palace Museum Qing court portraits: long narrow oval face, prominent cheekbones, small almond eyes, straight nose, high forehead and long narrow moustache with a sparse pointed beard in mature years. Preserve the same facial structure at every age.',
 'xianfeng':'Xianfeng Emperor, Aisin-Gioro Yizhu, based on Palace Museum court portraits: lean oval face, almond eyes, straight fine brows, narrow nose, slender mouth, high forehead. He died around age 30. All four versions must remain young adults, with subtle age progression; never gray-haired, wrinkled or elderly.',
 'ito_hirobumi':'Ito Hirobumi, based on National Diet Library portraits: broad high forehead, compact oval cheeks, narrow alert eyes, straight substantial nose, distinctive moustache and short pointed beard in mature years. The youthful version is slender with dark hair and little beard; later versions develop a receding hairline and graying beard.',
 'nicholas_ii':'Nicholas II of Russia, based on Royal Collection portraits: long oval face, deep-set pale blue eyes, straight nose, brushed side-parted brown hair and distinctive neatly trimmed brown moustache and short full beard. Youthful version has a much lighter short beard; retain his individual face rather than George V.',
 'wu_peifu':'Wu Peifu: narrow angular face, close-set alert eyes, high forehead, dark straight brows, thin drooping moustache as an adult.',
 'zhang_zuolin':'Zhang Zuolin: broad compact face, pronounced cheekbones, short nose, distinctive thick dark moustache as an adult.',
 'zhang_xueliang':'Zhang Xueliang: long oval face, large deep-set eyes, straight nose, clean-shaven and neatly swept black hair when young.',
 'feng_yuxiang':'Feng Yuxiang: large solid broad face, heavy brows, strong square jaw, close-cropped hair and a small moustache as an adult.',
 'sun_chuanfang':'Sun Chuanfang: long narrow angular face, very high forehead, receding short hair, thin neat dark moustache.',
 'qi_xieyuan':'Qi Xieyuan: elongated oval face, high receding forehead, small steady eyes, neat short moustache.',
 'lu_yongxiang':'Lu Yongxiang: broad mature face, high forehead, narrow dark eyes, well-groomed long moustache as an adult.',
 'yan_xishan':'Yan Xishan: compact broad oval face, rounded chin, high forehead, short hair and distinctive short neat moustache.',
 'tang_jiyao':'Tang Jiyao: lean oval face, straight brows, high forehead, short tidy hair and restrained thin moustache as an adult.',
 'chen_jiongming':'Chen Jiongming: lean long face, high forehead, receding hairline, thin moustache and thoughtful reserved expression.',
 'xu_chongzhi':'Xu Chongzhi: long broad forehead, lean angular cheeks, short combed-back dark hair and thin neat moustache as an adult.',
 'guo_songling':'Guo Songling: long angular face, high forehead, strong brows, tidy short hair and restrained moustache as an adult.',
}

def clothing(gid,year):
    if gid in ['daoguang','xianfeng']:
        accession=1820 if gid=='daoguang' else 1850
        if year<accession:return 'Plain deep-indigo Qing princely long robe with a modest complete dark informal Qing cap. Young adult Manchu prince, no imperial yellow robe, crown, modern uniform or invented decoration. Qing shaved front hairline with remaining hair secured behind the head.'
        return 'Restrained ochre-yellow Qing imperial informal long robe with plain upright collar and complete modest dark informal Qing round cap. Reference sober museum court portrait clothing, no fantasy crown, armor, medals, lettering or invented dragon emblems. Qing shaved front hairline. Facial age must match the requested living reference year.'
    if gid=='ito_hirobumi':return 'Plain dark Western civilian suit, white shirt and simple dark tie, bareheaded. Civilian statesman, no military uniform, medal rows or later invented insignia. All head and hair inside generous transparent margin.'
    if gid=='nicholas_ii':
        return 'Simple unmarked dark Imperial Russian high-collar officer tunic, bareheaded, subdued plain shoulder boards. No crown, orders, invented medals, Soviet uniform or fantasy armor. Age 49 version has only modest natural graying, never an elderly white-haired man.'
    if gid in ['lin_zexu','zeng_guofan','li_hongzhang']:
        return 'Simple dark blue Qing scholar long gown, upright cloth collar, bareheaded; no official insignia or later military uniform.' if year<1830 or (gid=='zeng_guofan' and year<1840) or (gid=='li_hongzhang' and year<1850) else 'Restrained dark indigo Qing official robe and complete modest Qing official hat; no emperor crown or fantasy armor.'
    if gid=='hong_xiuquan':
        return 'Plain dark Qing-era Chinese scholar long gown, bareheaded, young adult with little facial hair; no crown.' if year<1851 else 'Plain dark ochre long robe with a restrained upright cloth collar, long dark hair, simple unmarked cloth headpiece. No Qing official hat, no modern military uniform, no invented royal crown or armor.'
    if gid=='mao_zedong':
        if year<1930:return 'Young civilian in a plain dark Chinese long gown, long dark hair parted near the center and brushed back, clean-shaven. Slender youthful cheeks, no field cap, no later office costume.'
        if year<1950:return 'Middle-aged civilian in a plain washed slate-gray cotton stand-collar jacket, bareheaded, brushed-back dark hair, age-appropriate face; no post-1949 ceremony, medals or later office insignia.'
        return 'Elderly civilian in a simple slate-gray Zhongshan jacket, bareheaded, thinning gray hair and naturally aged full face. No insignia, medals or invented regalia.'
    if gid=='sun_yat_sen':return 'Plain dark Western civilian suit, white shirt, dark tie, bareheaded; no military rank or medals.'
    if gid=='peng_dehuai':
        if year<1927:return 'Young officer in a plain muted gray early-Republic cotton high-collar tunic, bareheaded, no medals or later rank boards.'
        if year<1950:return 'Plain worn gray cotton field tunic and soft unmarked short-brim two-button cap, no post-1949 marshal insignia.'
        return 'Elderly civilian in a simple worn gray cotton jacket, bareheaded; gray hair, no 1955 marshal boards or medals.'
    if gid in ['tojo_hideki','yamashita_tomoyuki']:
        if year>=1945:return 'Plain drab civilian shirt and jacket, bareheaded, no rank boards, no prisoner labels, no heroic propaganda. Age-appropriate late-life face.'
        return 'Plain muted khaki Imperial Japanese Army high-collar tunic, bareheaded, with no fabricated medals or rank symbols.'
    if gid=='yamagata_aritomo':return 'Plain dark high-collar Meiji-period Japanese officer tunic, bareheaded, restrained fabric and no invented medal rows.'
    if gid in ['waldersee','kuropatkin','alexei_kaledin']:
        nation='Prussian' if gid=='waldersee' else 'Imperial Russian'
        return f'Plain dark {nation} period high-collar officer tunic, bareheaded, simple subdued shoulder boards with no invented marks. No Nazi or Soviet insignia.'
    if year<1911:
        if gid in ['wu_peifu','zhang_zuolin','tang_jiyao','chen_jiongming','guo_songling'] and year<1905:return 'Plain dark late-Qing civilian scholar long gown, bareheaded; no later military cap, regalia or rank boards.'
        return 'Plain dark late-Qing New Army high-collar tunic, simple unmarked field cap; no Republican emblems or medals.'
    if gid in ['wu_peifu','zhang_xueliang','feng_yuxiang','sun_chuanfang','lu_yongxiang','yan_xishan','chen_jiongming','xu_chongzhi'] and year>=1930 and ((gid=='zhang_xueliang' and year>=1950) or (gid=='feng_yuxiang' and year>=1947) or (gid not in ['zhang_xueliang','feng_yuxiang'] and year>=1930)):
        return 'Plain dark Chinese civilian long gown or simple dark civilian jacket, bareheaded; no invented military rank, medals or modern camouflage.'
    return 'Plain muted olive-khaki early Republican high-collar officer tunic, modest unmarked peaked cap, no invented medals or insignia.'

def rows():
    life=json.loads((P/'presentation/data/general_lifespans.json').read_text(encoding='utf-8'))['generals']
    revisions=json.loads((P/'tools/portrait_age_revisions.json').read_text(encoding='utf-8'))
    assets={row['id']:row for row in json.loads((P/'assets/manifest.json').read_text(encoding='utf-8'))['assets']}
    existing_briefs={r[0]:r[4] for r in generator.SPECS}
    style=generator.STYLE.replace('post-1949 uniforms, ','')
    style+='\nThe entire head, hair or cap must have at least 10 percent clear margin above it. A compact chest-up bust with both shoulders inside the frame; clean alpha edges without colored fringes. Not a photograph; consistent fine painted atlas brushwork.\n'
    for gid,person in life.items():
        for stage in person['stages']:
            year=stage['reference_year'];aid=f'portrait_{gid}_{year}'
            # The 12 original 1920s illustrations remain the exact original files.
            original='portrait_'+gid
            if year==1920 and original in assets:aid=original
            if aid in assets:continue
            brief=EARLY_FACES.get(gid,existing_briefs.get(gid,''))
            if gid=='hong_xiuquan':brief='Hong Xiuquan, interpreted from written descriptions and later commemorative depictions, not an authenticated lifetime photograph: broad prominent forehead, long oval face, straight strong brows and serious dark eyes, long straight dark hair, a natural thin moustache and short dark beard only in the mature versions. A dignified scholar, not a fantasy emperor.'
            # Clothing is specified separately so one subject's old prompt cannot
            # give a young or postwar variant the wrong era's costume.
            face=brief.split('. Dark ')[0] if gid in ['kuropatkin','waldersee'] else brief
            revision=revisions.get(aid,{})
            if revision and gid=='hong_xiuquan':face=face.replace('long straight dark hair, ','')
            face=revision.get('face',face)
            costume=revision.get('clothing',clothing(gid,year))
            prompt=style+f'\nSUBJECT: {person["name"]} ({gid}), approximately {year-person["birth_year"]} years old, around {year}. Stage {stage["id"]}.\nIdentity face brief: {face}\nCLOTHING AND AGE FOR THIS SINGLE IMAGE (takes priority over any generic face-brief clothing): {costume}\n'
            yield {'id':aid,'general_id':gid,'subject':person['name'],'reference_year':year,'age_stage':stage['id'],'approximate_age':year-person['birth_year'],'prompt':prompt,'revision':revision.get('revision','r001'),'reference_urls':person.get('reference_urls',[]),'reference_scope':'Interpretive game portrait, age and clothing brief. No exact-year archival photograph or independently approved likeness claimed.'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=3);parser.add_argument('--only',nargs='*');parser.add_argument('--install-reviewed',action='store_true');args=parser.parse_args()
    generator.RAW=RAW
    selected=[r for r in rows() if not args.only or r['id'] in args.only]
    if args.install_reviewed:
        review={r['id']:r for r in json.loads((RAW/'review.json').read_text(encoding='utf-8'))['originals']}
        manifest=json.loads((P/'assets/manifest.json').read_text(encoding='utf-8'));known={r['id']:r for r in manifest['assets']}
        for row in selected:
            source=RAW/row['id']/row['revision']/'source.png';evidence=review[row['id']]
            if not evidence['accepted'] or not evidence['viewed_complete_original'] or evidence['sha256']!=generator.sha(source):raise ValueError('Complete individual source review required: '+row['id'])
            data=generator.generate(row);target=P/'assets/portrait'/(row['id']+'.png')
            if target.exists() and generator.sha(target)!=generator.sha(source):raise ValueError('Installed original is immutable: '+row['id'])
            if not target.exists():shutil.copyfile(source,target)
            known[row['id']]=data|dict(category='portrait',view='three_quarter',era=str(row['reference_year']),state='source_reviewed_runtime_pending',game_ready=False,style_version='warlord_age_portrait_v0222',planned_source_request=[1024,1024],runtime_import_max_dimension=512,background='transparent',alpha_min=0,engine_path='res://'+target.relative_to(P).as_posix())
        manifest['assets']=list(known.values());(P/'assets/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'installed':len(selected),'source_images_modified':False}));return
    complete=[];failed=[]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        tasks={pool.submit(generator.generate,r):r['id'] for r in selected}
        for future in as_completed(tasks):
            aid=tasks[future]
            try:complete.append(future.result());print(aid+': whole age original ready',flush=True)
            except Exception as error:failed.append({'id':aid,'error':str(error)});print(aid+': FAILED',flush=True)
    RAW.mkdir(parents=True,exist_ok=True);(RAW/'generation.json').write_text(json.dumps({'requested':len(selected),'generated':len(complete),'passed':not failed,'records':complete,'failures':failed,'source_route':'sub2-image-gen/gpt-image-2.5/high','image_modified':False,'formal_art_approval':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    raise SystemExit(1 if failed else 0)

if __name__=='__main__':main()
