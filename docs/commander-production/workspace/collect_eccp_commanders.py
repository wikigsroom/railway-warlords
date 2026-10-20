"""Cache public-domain Library of Congress biography text, never images."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin
import hashlib
import json
import re
import requests
from bs4 import BeautifulSoup

BASE="https://en.wikisource.org/wiki/Eminent_Chinese_of_the_Ch%27ing_Period"
OUT=Path(__file__).resolve().parent/'research/eccp'
# Original index orthography. A person is not counted until the biography's
# life years and actual field command have been checked individually.
NAMES='''關天培 陳化成 葛雲飛 裕謙 奕經 奕山 楊芳 僧格林沁 勝保 德興阿 楊秀清 蕭朝貴 馮雲山 石達開 韋昌輝 洪仁玕 李秀成 陳玉成 李世賢 賴文光 楊輔清 林鳳祥 李開芳 蒙得恩 秦日綱 羅大綱 曾天養 胡以晃 譚紹光 汪海洋 黃文金 林啟容 張樂行 任柱 左宗棠 胡林翼 曾國荃 鮑超 彭玉麟 楊岳斌 劉蓉 江忠源 羅澤南 李續賓 塔齊布 劉銘傳 劉錦棠 劉永福 唐景崧 馮子材 丁汝昌 劉步蟾 鄧世昌 林永升 葉祖珪 方伯謙 葉志超 聶士成 宋慶 馬玉昆 董福祥 榮祿 向榮 和春 張國樑 多隆阿 都興阿 程學啟 陳國瑞 蕭啟江 李成謀 吳長慶 袁世凱 馮國璋 王士珍 曹錕 張勳 姜桂題 王占元 陸榮廷 龍濟光 蔡鍔 李烈鈞 唐繼堯 段祺瑞 張作霖 吳佩孚 孫傳芳 張宗昌 馮玉祥 閻錫山'''.split()

def fetch(path,url):
    if not path.exists():
        r=requests.get(url,timeout=50,headers={'User-Agent':'HistoricalGameResearch/1.0 (public-domain biography facts; text only)'})
        r.raise_for_status();path.write_bytes(r.content)
    return path.read_bytes()

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    data=fetch(OUT/'index.html',BASE)
    soup=BeautifulSoup(data,'html.parser')
    links={}
    for li in soup.select('.mw-parser-output li'):
        a=li.find('a')
        if not a:continue
        text=li.get_text(' ',strip=True)
        for name in NAMES:
            if name in text and name not in links:
                links[name]=urljoin(BASE,a.get('href',''))
    print(json.dumps({'found':len(links),'missing':[n for n in NAMES if n not in links]},ensure_ascii=False),flush=True)
    def one(item):
        name,url=item;ident='eccp_'+''.join(f'{ord(c):04x}' for c in name)
        raw=fetch(OUT/(ident+'.html'),url)
        body=BeautifulSoup(raw,'html.parser')
        for node in body.select('script,style,.mw-editsection,.ws-noexport,.catlinks,.navbox'):node.decompose()
        article=body.select_one('.mw-parser-output')
        text=article.get_text('\n',strip=True) if article else body.get_text('\n',strip=True)
        (OUT/(ident+'.txt')).write_text(text,encoding='utf-8')
        return dict(source_id=ident,name_original=name,url=url,sha256=hashlib.sha256(raw).hexdigest(),
                    text_file=ident+'.txt',publisher='Library of Congress, Orientalia Division; US Government Printing Office, 1943–1944',
                    work='Eminent Chinese of the Ch’ing Period',text_edition='Wikisource transcription of public-domain original; check cited biography facts')
    rows=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks={pool.submit(one,item):item[0] for item in links.items()}
        for future in as_completed(tasks):
            row=future.result();rows.append(row);print(row['name_original'],flush=True)
    (OUT/'index.json').write_text(json.dumps({'rows':sorted(rows,key=lambda x:x['name_original']),
        'missing':[n for n in NAMES if n not in links],'remote_images_downloaded':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
