"""Cache published institutional biographies as research, without their images."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import hashlib,json,re,requests
from bs4 import BeautifulSoup

OUT=Path(__file__).resolve().parent/'research/cpc'
SOURCES={
 '朱德':'https://cpc.people.com.cn/GB/64162/126778/126780/7489937.html',
 '刘伯承':'https://cpc.people.com.cn/GB/64162/126778/126780/7490151.html',
 '贺龙':'https://cpc.people.com.cn/GB/64162/126778/126780/7490379.html',
 '徐向前':'https://cpc.people.com.cn/GB/64162/126778/126780/7490461.html',
 '陈毅':'https://cpc.people.com.cn/GB/64162/126778/126780/7490411.html',
 '聂荣臻':'https://cpc.people.com.cn/GB/64162/126778/126780/7490472.html',
 '陈赓':'https://cpc.people.com.cn/GB/64162/126778/127855/7537031.html',
 '黄克诚':'https://cpc.people.com.cn/GB/64162/126778/127855/7537011.html',
 '徐海东':'https://cpc.people.com.cn/GB/64162/126778/127855/7536984.html',
 '张云逸':'https://cpc.people.com.cn/GB/64162/126778/127855/7537178.html',
 '张宗逊':'https://cpc.people.com.cn/GB/64162/126778/127857/7538565.html',
 '许世友':'https://cpc.people.com.cn/GB/64162/126778/127857/7537900.html',
 '王震':'https://cpc.people.com.cn/daohang/n/2013/0226/c357263-20607175.html',
 '叶挺':'https://cpc.people.com.cn/n1/2021/0520/c64387-32108292.html',
 '林彪':'https://cpc.people.com.cn/GB/64162/126778/126780/7490123.html',
 '左权':'https://cpc.people.com.cn/GB/34136/2543720.html',
 '粟裕':'https://cpc.people.com.cn/GB/64162/126778/127855/7536807.html',
 '许光达':'https://cpc.people.com.cn/GB/33840/2543934.html',
 '罗炳辉':'https://cpc.people.com.cn/n1/2023/0529/c443712-40000906.html',
 '周士第':'https://cpc.people.com.cn/GB/64162/126778/127857/7538728.html',
 '肖劲光':'https://cpc.people.com.cn/GB/33840/2546506.html',
 '王宏坤':'https://cpc.people.com.cn/GB/64162/126778/127857/7537459.html',
 '叶剑英':'https://cpc.people.com.cn/GB/64162/126778/126780/7490482.html',
 '刘志丹':'https://cpc.people.com.cn/GB/33840/2544013.html',
 '黄公略':'https://cpc.people.com.cn/n1/2024/1006/c443712-40333531.html',
 '许继慎':'https://www.mod.gov.cn/gfbw/gfjy_index/xjdx/4821811.html',
 '蔡申熙':'https://cpc.people.com.cn/n1/2017/0327/c85037-29170463.html',
 '贺炳炎':'https://cpc.people.com.cn/n/2015/0629/c85037-27223272-2.html',
 '萧克':'https://cpc.people.com.cn/n1/2016/0922/c85037-28731801.html',
}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    def one(item):
        name,url=item;ident='cpc_'+''.join(f'{ord(c):04x}' for c in name);path=OUT/(ident+'.html')
        if not path.exists():
            r=requests.get(url,timeout=40);r.raise_for_status();path.write_bytes(r.content)
        raw=path.read_bytes();soup=BeautifulSoup(raw,'html.parser',from_encoding='utf-8' if b'charset=utf-8' in raw.lower() else None)
        for node in soup.select('script,style'):node.decompose()
        text=soup.get_text('\n',strip=True)
        (OUT/(ident+'.txt')).write_text(text,encoding='utf-8')
        return dict(source_id=ident,name=name,url=url,source_sha256=hashlib.sha256(raw).hexdigest(),text_file=ident+'.txt')
    rows=[];failures=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks={pool.submit(one,item):item[0] for item in SOURCES.items()}
        for f in as_completed(tasks):
            try:r=f.result();rows.append(r);print(r['name'],flush=True)
            except Exception as e:failures.append(dict(name=tasks[f],error=str(e)));print(tasks[f],type(e).__name__,flush=True)
    (OUT/'biographies.json').write_text(json.dumps(dict(rows=rows,failures=failures,remote_images_downloaded=False),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
