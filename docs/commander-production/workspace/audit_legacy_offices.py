"""Add narrowly sourced military-office facts, preserving raw source snapshots.

Nothing here infers participation from a person's lifetime or claims an entire
tenure from a single biographical mention. Stable IDs survive spelling changes.
"""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,requests,concurrent.futures
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1];P=ROOT/'game/railway_warlords'
CACHE=BASE/'research/legacy_offices';CACHE.mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(p.read_text('utf-8'))
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
specs={
 'palace_lu':('https://www.dpm.org.cn/lemmas/245438.html','故宫博物院','卢永祥人物资料'),
 'guo_cppcc_2017':('https://dangshi.people.com.cn/n1/2017/1110/c85037-29638413.html','人民政协报 / 中国共产党新闻网','郭松龄缘何倒戈反奉'),
 'ndl_208':('https://www.ndl.go.jp/portrait/datas/208','日本国立国会图书馆','山県有朋人物资料'),
 'ndl_142':('https://www.ndl.go.jp/portrait/datas/142','日本国立国会图书馆','東条英機人物资料'),
 'nids_yamashita_2016':('https://www.nids.mod.go.jp/military_archives/news/2016/201604.pdf','日本防卫研究所战史研究中心史料室','史料介绍：山下奉文与马来攻略作战'),
 'waldersee_gsta':('https://gsta.preussischer-kulturbesitz.de/fileadmin/user_upload_gsta/02_Content/Texte/01_Recherche/inventare_preussen_deutschland_china.pdf','普鲁士文化遗产秘密国家档案馆','Preußen–Deutschland–China，Waldersee遗稿目录'),
 'kuropatkin_croatian_encyclopedia':('https://www.enciklopedija.hr/clanak/kuropatkin-aleksej-nikolajevic','Miroslav Krleža Institute of Lexicography','Aleksej Nikolajevič Kuropatkin'),
 'sun_1917_declaration':('https://zh.wikisource.org/zh-hans/%E5%8F%97%E4%BB%BB%E6%B5%B7%E9%99%B8%E8%BB%8D%E5%A4%A7%E5%85%83%E5%B8%A5%E5%AE%A3%E8%A8%80','孙中山1917年9月10日原始宣言 / 维基文库数字转录','受任海陆军大元帅宣言'),
 'chiang_1926_archival_catalogue':('https://gpost.lib.nccu.edu.tw/view_career.php?name=%E8%94%A3%E4%B8%AD%E6%AD%A3','国立政治大学图书馆','中华民国政府官职资料库：个人任命核对'),
 'autumn_harvest_cpc':('https://cpc.people.com.cn/GB/33837/2534129.html','中国共产党新闻网资料中心','秋收起义'),
 'peng_1928_chronology':('https://cpc.people.com.cn/GB/67481/71472/4844879.html','中国共产党新闻网资料中心','彭德怀大事年表（1920—1929）'),
 'kaledin_sholokhov_museum':('https://www.sholokhov.ru/museum/News/2011/n608/','俄罗斯肖洛霍夫国家博物馆','Каледин：150周年生平介绍'),
 'xing_luoyang_daily_20140915':('https://lyrb.lyd.com.cn/images/2014-09/15/1410737462125lyrb20140915004.pdf','洛阳日报，2014年9月15日第4版','邢清忠：对县志编纂者及家属的实地采访'),
}

def collect(item):
 key,(url,publisher,title)=item;path=CACHE/(key+('.pdf' if '.pdf' in url else '.html'))
 # Two pages were read through the web tool. Native downloads failed with a
 # certificate hostname error / connection reset. Record that limitation;
 # never disable TLS or invent a hash of an unreceived original document.
 if key in ['guo_cppcc_2017','sun_1917_declaration','chiang_1926_archival_catalogue']:
  return dict(id=key,url=url,publisher=publisher,title=title,
   retrieval_status='web_tool_verified_native_download_unavailable',
   locally_cached_original=False,accessed_at_utc=datetime.now(timezone.utc).isoformat())
 if not path.exists():
  response=requests.get(url,timeout=45,headers={'User-Agent':'RailwayWarlords-history-research/0.2.28'});response.raise_for_status();path.write_bytes(response.content)
 return dict(id=key,url=url,publisher=publisher,title=title,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),accessed_at_utc=datetime.now(timezone.utc).isoformat())

def main():
 collected=[];errors=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  futures={pool.submit(collect,x):x[0] for x in specs.items()}
  for future in concurrent.futures.as_completed(futures):
   try:collected.append(future.result())
   except Exception as error:errors.append(dict(id=futures[future],error=str(error)))
 write(CACHE/'index.json',dict(sources=collected,errors=errors))
 if errors:print(json.dumps(dict(applied=False,errors=errors)));return 1
 services=read(P/'content/definitions/commander_service.json');by={r['id']:r for r in services}
 sources={r['id']:r for r in read(P/'content/definitions/commander_sources.json')}
 sources.update({r['id']:r for r in collected})
 facts=[
  ('lu_yongxiang','北洋陆军师长、浙江督军','division',None,['palace_lu'],None),
  ('guo_songling','奉军第3军副军长','deputy_army_or_higher',1924,['guo_cppcc_2017'],None),
  ('lin_zexu','钦差大臣、广东防务主持者','historical_theater_command',1839,['eccp_volume_1'],'volume 1 PDF pp.528–532'),
  ('hong_xiuquan','太平天国天王','national_high_command',1851,['eccp_volume_1'],'volume 1 PDF pp.378–383'),
  ('zeng_guofan','湘军统帅','historical_field_command',1853,['eccp_volume_2'],'volume 2 PDF pp.154–159'),
  ('li_hongzhang','淮军统帅','historical_field_command',1862,['eccp_volume_1'],'volume 1 PDF pp.481–488'),
  ('yamagata_aritomo','日清战争第1军司令官','army_or_higher',1894,['ndl_208'],None),
  ('waldersee','驻华多国干涉军总司令','expeditionary_command',1900,['waldersee_gsta'],'VI. HA, NI Waldersee, Alfred Graf von A I / A II'),
  ('kuropatkin','俄军满洲战区统帅','army_or_higher',1904,['kuropatkin_croatian_encyclopedia'],None),
  ('sun_yat_sen','海陆军大元帅','national_high_command',1917,['sun_1917_declaration'],'1917-09-10 declaration'),
  ('chiang_kai_shek','国民革命军总司令','national_high_command',1926,['chiang_1926_archival_catalogue'],'民国15年6月5日任命；仅核对单项事实，不复制官职数据库'),
  ('mao_zedong','秋收起义前敌委员会书记','army_political_co_command',1927,['autumn_harvest_cpc'],None),
  ('peng_dehuai','红军第5军军长兼第13师师长','army_or_higher',1928,['peng_1928_chronology'],'1928-07-24'),
  ('tojo_hideki','陆军大臣','national_high_command',1940,['ndl_142'],None),
  ('yamashita_tomoyuki','第25军司令官','army_or_higher',1941,['nids_yamashita_2016'],None),
  ('alexei_kaledin','俄军第8集团军司令','army_or_higher',1916,['kaledin_sholokhov_museum'],None),
 ]
 for id,title,level,year,ids,pages in facts:
  r=by[id];r.update(documented_title=title,command_level=level,documented_year=year,source_ids=ids,
    reference_urls=list(dict.fromkeys(r['reference_urls']+[sources[s]['url'] for s in ids])),
    appointment_date_status='documented_office_mention_not_complete_tenure')
  if pages:r['source_page_locator']=pages
  if id=='lu_yongxiang':r['historical_note']='故宫资料可证师长与浙江督军经历；该来源未提供师番号及具体任命日，不补造。'
 # The legacy 1924 gameplay fallback is not historical allegiance evidence.
 # In particular Duan must never inherit Zhili from that old fallback.
 for id,side in {'duan_qirui':'anhui','chiang_kai_shek':'kmt','li_zongren':'kmt','bai_chongxi':'kmt','mao_zedong':'ccp','peng_dehuai':'ccp','sun_yat_sen':'guangzhou_government'}.items():
  by[id]['historical_side']=side
 x=by['cn_52116e055fe0'];x.update(name='邢清忠',source_name_variants=['刑清忠'],documented_year=1939,
  name_correction_note='洛阳日报采访县志编纂者及家属，确认名单中的刑清忠应为邢清忠。稳定ID及不可变原图提示词保留原来源写法。',
  life_year_note='1899—1941。县志与英烈材料对病逝或战殁存在差异；不据此登记精确死亡月日。')
 x['source_ids']=list(dict.fromkeys(x['source_ids']+['xing_luoyang_daily_20140915']))
 x['reference_urls']=list(dict.fromkeys(x['reference_urls']+[sources['xing_luoyang_daily_20140915']['url']]))
 generals=read(P/'content/definitions/generals.json')
 next(r for r in generals if r['id']==x['id'])['name']=x['name']
 lives=read(P/'presentation/data/general_lifespans.json');lives['generals'][x['id']]['name']=x['name']
 lives['generals'][x['id']]['precision_note']=x['life_year_note'];lives['generals'][x['id']]['reference_urls']=x['reference_urls']
 write(P/'content/definitions/commander_service.json',services);write(P/'content/definitions/commander_sources.json',list(sources.values()))
 write(P/'content/definitions/generals.json',generals);write(P/'presentation/data/general_lifespans.json',lives)
 print(json.dumps(dict(applied=True,legacy_offices_audited=len(facts),total_sourced=sum(bool(r.get('source_ids')) for r in services),name_correction='stable_id_preserved')))
 return 0
if __name__=='__main__':raise SystemExit(main())
