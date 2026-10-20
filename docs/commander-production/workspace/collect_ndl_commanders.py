from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import hashlib,json,re,urllib.request
from urllib.parse import urljoin
from bs4 import BeautifulSoup

P=Path(__file__).resolve().parent/'research/ndl'
P.mkdir(parents=True,exist_ok=True)
ROOT='https://www.ndl.go.jp'

def fetch(url,name):
    path=P/(name+'.html')
    if not path.exists():
        req=urllib.request.Request(url,headers={'User-Agent':'Historical-game-research/1.0'})
        with urllib.request.urlopen(req,timeout=35) as response:data=response.read()
        path.write_bytes(data)
    return BeautifulSoup(path.read_bytes(),'html.parser')

links={}
for category in ['Military-Officer','Military-Officer_2','Naval-Officer']:
    soup=fetch(ROOT+'/portrait/category/'+category,category)
    for a in soup.select('a[href]'):
        href=a.get('href','')
        if re.fullmatch('/portrait/datas/[^/]+/?',href):links[urljoin(ROOT,href)]=a.get_text(' ',strip=True)

def one(item):
    url,label=item; sid=url.rstrip('/').split('/')[-1]
    soup=fetch(url,'person_'+sid)
    main=soup.find('main') or soup
    for element in main.select('script,style,rt'):element.decompose()
    text=main.get_text('\n',strip=True)
    (P/('person_'+sid+'.txt')).write_text(text,encoding='utf-8')
    return {'id':'ndl_'+sid,'url':url,'label':label,'text_file':str(P/('person_'+sid+'.txt')),'source_sha256':hashlib.sha256((P/('person_'+sid+'.html')).read_bytes()).hexdigest()}

rows=[];errors=[]
with ThreadPoolExecutor(max_workers=4) as pool:
    for future in as_completed([pool.submit(one,item) for item in links.items()]):
        try:rows.append(future.result())
        except Exception as e:errors.append(str(e))
(P/'index.json').write_text(json.dumps({'entries':sorted(rows,key=lambda r:r['id']),'errors':errors},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'listed':len(links),'downloaded':len(rows),'errors':errors},ensure_ascii=False))
