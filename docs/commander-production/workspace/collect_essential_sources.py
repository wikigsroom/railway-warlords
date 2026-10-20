"""Cache individual institutional biographies; never scrape image assets."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib,json,requests
from bs4 import BeautifulSoup
BASE=Path(__file__).resolve().parent;OUT=BASE/'research/essential';OUT.mkdir(parents=True,exist_ok=True)
SOURCES={
 'gdws_guan':('文史广东 / 广东省人民政府文史研究馆','关天培在虎门','https://www.gdwsw.gov.cn/rwcq/content/post_25991.html'),
 'dpm_sengge':('故宫博物院','僧格林沁','https://www.dpm.org.cn/lemmas/243417.html'),
 'weihai_ding':('威海市委党史研究院','丁汝昌（1836—1895.2）','https://www.weihai.gov.cn/art/2021/1/22/art_58901_3536345.html'),
 'hunan_luo':('湖南省人民政府 / 湖南省委宣传部','罗荣光故居','https://hunan.gov.cn/hnszf/c101487/202108/t20210830_20409865.html'),
 'weihai_liu':('威海市委党史研究院','刘步蟾（1852—1895.2）','https://www.weihai.gov.cn/art/2021/1/22/art_58901_3536266.html'),
 'cppcc_yang_fang':('贵州省政协','杨芳：绘像紫光阁的名臣','https://www.gzszx.gov.cn/gzzxb/web/doc/detail/2509/A3'),
 'ge_yunfei_memorial':('兰州新区政府转载 / 葛云飞史迹','葛云飞：我自励千秋','https://www.lzxq.gov.cn/system/2017/11/08/000109327.shtml'),
 'boorman_zhang_xun':('ENP-China / X-Boorman academic edition','Zhang Xun','https://xboorman.enpchina.eu/biographie/zhang-xun/'),
 'boorman_zhang_fakui':('ENP-China / X-Boorman academic edition','Zhang Fakui','https://xboorman.enpchina.eu/biographie/zhang-fakui/'),
 'shanghai_zhang_fakui':('上海市松江区史志办','抗日战争时期的张发奎','https://www.songjiang.gov.cn/sjsz/sjds/sjkzjy/files/basic-html/page179.html'),
 'boorman_tang_shengzhi':('ENP-China / X-Boorman academic edition','Tang Shengzhi','https://xboorman.enpchina.eu/biographie/tang-shengzhi/'),
 'nlpi_tang_shengzhi':('国立公共资讯图书馆','民国近代史：唐生智','https://edata.nlpi.edu.tw/CNH/Personage/personage.aspx?ID=0000161'),
 'he_yingqin_office':('人民网党史频道 / 文史精华','蒋介石夺何应钦兵权','https://dangshi.people.com.cn/n1/2017/0223/c85037-29103257.html'),
 'he_yingqin_life':('中国大百科全书出版社','何应钦','https://www.zgbk.com/ecph/words?Name=%E4%BD%95%E5%BA%94%E9%92%A6&SiteID=1&SourceID=524211&Type=bkzyb&subSourceType=000003000006000002'),
 'anu_bremer':('Australian National University / Australian Dictionary of Biography','Bremer, Sir James John (1786–1850)','https://adb.anu.edu.au/biography/bremer-sir-james-john-1823/text2091'),
 'nam_first_china':('National Army Museum','First China War','https://www.nam.ac.uk/explore/first-china-war-1839-1842'),
 'nam_gough_life':('National Army Museum','Lieutenant-General Viscount Hugh Gough (1779–1869)','https://collection.nam.ac.uk/detail.php?acc=2018-10-7-1'),
 'rmg_parker':('Royal Museums Greenwich','Captain William Parker, 1781–1866','https://www.rmg.co.uk/collections/objects/rmgc-object-1144147'),
 'nam_grant':('National Army Museum','Sir James Hope Grant, 1862','https://collection.nam.ac.uk/detail.php?acc=1998-06-81-1'),
 'nam_second_china':('National Army Museum','Second China War','https://www.nam.ac.uk/explore/second-china-war'),
 'napoleon_montauban':('Fondation Napoléon','Cousin de Montauban, Charles Guillaume','https://www.napoleon.org/en/history-of-the-two-empires/biographies/cousin-de-montauban-charles-guillaume/'),
 'bnf_montauban':('BnF / Biblissima','Cousin de Montauban de Palikao (1796–1878)','https://portail.biblissima.fr/ark:/43093/pdatae0fe785bc9d4d1e17b852ebae1899d5a4e624215'),
 'npg_napier':('National Portrait Gallery','Robert Cornelis Napier, 1st Baron Napier of Magdala','https://www.npg.org.uk/collections/search/person/mp03247/robert-cornelis-napier-1st-baron-napier-of-magdala'),
 'bl_gaselee':('British Library Archives','Photo 1255(22): Gaselee at the British Legation','https://searcharchives.bl.uk/catalog/040-003188904'),
 'dnb_gaselee':('Dictionary of National Biography, 1927 supplement / Wikisource','Gaselee, Alfred','https://en.wikisource.org/wiki/Dictionary_of_National_Biography,_1927_supplement/Gaselee,_Alfred'),
}
def fetch(item):
 key,(publisher,title,url)=item;p=OUT/(key+'.html')
 row=dict(id=key,publisher=publisher,title=title,url=url,retrieved_utc=datetime.now(timezone.utc).isoformat())
 try:
  if not p.exists():
   response=requests.get(url,timeout=40);response.raise_for_status();p.write_bytes(response.content)
  raw=p.read_bytes();soup=BeautifulSoup(raw,'html.parser')
  for n in soup(['script','style','nav','header','footer']):n.decompose()
  text=soup.get_text(' ',strip=True)
  if len(text)<180:raise ValueError('Insufficient biography text')
  (OUT/(key+'.txt')).write_text(text,encoding='utf-8')
  row.update(local_file=p.name,sha256=hashlib.sha256(raw).hexdigest(),locally_cached_original=True,text_characters=len(text),retrieval_status='cached_original')
 except Exception as e:row.update(locally_cached_original=False,retrieval_status='native_download_unavailable',error=type(e).__name__)
 return row
if __name__=='__main__':
 with ThreadPoolExecutor(max_workers=4) as workers:rows=list(workers.map(fetch,SOURCES.items()))
 (OUT/'index.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps([dict(id=r['id'],cached=r['locally_cached_original'],characters=r.get('text_characters',0)) for r in rows]))
