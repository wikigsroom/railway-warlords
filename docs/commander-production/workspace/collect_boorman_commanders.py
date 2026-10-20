"""Cache academic biographies, never download their raster illustrations."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib, json, requests
from bs4 import BeautifulSoup

BASE=Path(__file__).resolve().parent
OUT=BASE/'research/boorman';OUT.mkdir(parents=True,exist_ok=True)
SLUGS=['cao-kun','xu-shuzheng','duan-zhigui','jin-yunpeng','zhang-zongchang',
       'zhang-zuoxiang','sun-liechen','wu-junsheng','li-jinglin','jiang-dengxuan',
       'yang-yuting','han-linchun','hu-jingyi','sun-yue','yu-xuezhong','wang-chengbin',
       'wu-peifu','zhang-zuolin','zhang-xueliang','feng-yuxiang','sun-chuanfang',
       'qi-xieyuan','lu-yongxiang','yan-xishan','tang-jiyao','chen-jiongming',
       'xu-chongzhi','guo-songling','duan-qirui','li-zongren','bai-chongxi']
def one(slug):
    url='https://xboorman.enpchina.eu/biographie/'+slug+'/'
    f=OUT/(slug+'.html');t=OUT/(slug+'.txt')
    try:
        if not f.exists():
            r=requests.get(url,timeout=35);r.raise_for_status()
            f.write_bytes(r.content)
        soup=BeautifulSoup(f.read_bytes(),'html.parser')
        for e in soup(['script','style','nav','header','footer']):e.decompose()
        body=soup.select_one('article') or soup
        text=body.get_text('\n',strip=True)
        t.write_text(text,encoding='utf-8')
        return dict(slug=slug,url=url,html_file=f.name,text_file=t.name,
                    sha256=hashlib.sha256(f.read_bytes()).hexdigest(),text_length=len(text),passed=True)
    except Exception as e:return dict(slug=slug,url=url,passed=False,error=type(e).__name__+': '+str(e)[:160])
rows=[]
with ThreadPoolExecutor(max_workers=2) as pool:
    for future in as_completed([pool.submit(one,s) for s in SLUGS]):
        result=future.result()
        rows.append(result);print(json.dumps(result,ensure_ascii=False),flush=True)
(OUT/'index.json').write_text(json.dumps(dict(publisher='ENP-China / X-Boorman academic digital edition',
    title='Biographical Dictionary of Republican China',rows=rows),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
