"""Record the consulted lifespan sources without inventing missing birthdays."""
import json
from pathlib import Path
P=Path(__file__).resolve().parents[1]
SOURCES={
 'daoguang':('museum_dynastic_biography','https://www.dpm.org.cn/court/lineage/226239.html'),
 'xianfeng':('museum_dynastic_biography','https://www.dpm.org.cn/court/lineage/226247.html'),
 'ito_hirobumi':('national_library_biography','https://www.ndl.go.jp/portrait/e/datas/12/'),
 'nicholas_ii':('royal_collection_authority','https://www.rct.uk/collection/2926975/the-coronation-procession-of-nicholas-ii-emperor-of-russia'),
 'wu_peifu':('academic_authority','https://ecpo.cats.uni-heidelberg.de/ecpo/agent-information.php?agentid=1773'),
 'zhang_zuolin':('academic_authority','https://digital.janeaddams.ramapo.edu/items/show/35986'),
 'zhang_xueliang':('museum_biography','https://www.024glsmy.cn/zhangxueliang/index.shtml'),
 'feng_yuxiang':('encyclopedia','https://lex.dk/Feng_Yuxiang'),
 'sun_chuanfang':('encyclopedia','https://www.zgbk.com/ecph/words?Name=%E5%AD%99%E4%BC%A0%E8%8A%B3&SiteID=1&SourceID=85626&Type=bkzyb&subSourceType=000003000005000006'),
 'qi_xieyuan':('secondary_reference_pending_primary_lifespan_check','https://zh.wikipedia.org/wiki/%E9%BD%90%E7%87%AE%E5%85%83'),
 'lu_yongxiang':('museum_biography','https://www.dpm.org.cn/lemmas/245438.html'),
 'yan_xishan':('academic_authority','https://digital.janeaddams.ramapo.edu/items/show/41915'),
 'tang_jiyao':('national_library_catalog','https://edata.nlpi.edu.tw/CNH/Personage/personage.aspx?ID=0000024'),
 'chen_jiongming':('national_library_catalog','https://edata.nlpi.edu.tw/CNH/Personage/personage.aspx?ID=0002599'),
 'xu_chongzhi':('academic_biographical_dictionary','https://xboorman.enpchina.eu/biographie/xu-chongzhi/'),
 'guo_songling':('secondary_reference_pending_primary_lifespan_check','https://zh.wikipedia.org/wiki/%E9%83%AD%E6%9D%BE%E9%BE%84'),
 'lin_zexu':('museum_collection_and_year_reference','https://digitalarchive.npm.gov.tw/Collection/Detail/28680?dep=P'),
 'hong_xiuquan':('academic_encyclopedia','https://onlinelibrary.wiley.com/doi/abs/10.1002/9780470670606.wbecc1486'),
 'zeng_guofan':('government_cultural_biography','https://whhlyt.hunan.gov.cn/whhlyt/english/Culture/CulturalFigures/202205/t20220527_24654725.html'),
 'li_hongzhang':('museum_collection_authority','https://www.npg.org.uk/collections/search/portrait/mw225127/Li-Hongzhang-Li-Hung-Chang'),
 'yamagata_aritomo':('national_library_biography','https://www.ndl.go.jp/portrait/e/datas/208/'),
 'waldersee':('secondary_reference_and_museum_context','https://en.wikipedia.org/wiki/Alfred_von_Waldersee'),
 'kuropatkin':('academic_encyclopedia','https://www.enciklopedija.hr/clanak/kuropatkin-aleksej-nikolajevic'),
 'sun_yat_sen':('museum_biography_and_photograph_catalog','https://www.sunyat-sen.org/portal/list/index.html?id=216'),
 'duan_qirui':('encyclopedia','https://www.zgbk.com/ecph/words?ID=57244&SiteID=1'),
 'chiang_kai_shek':('university_library_authority','https://onlinebooks.library.upenn.edu/webbin/who/Chiang%2C%20Kai-shek%2C%201887-1975'),
 'li_zongren':('historical_association_biography','https://www.huangpu.org.cn/hpjs/201209/t20120923_3116368.html'),
 'bai_chongxi':('official_oral_history','https://www.mnd.gov.tw/en/informationservices/publication/72322'),
 'mao_zedong':('official_biography_dates','https://www.12371.cn/2023/12/22/VIDE1703229361350208.shtml'),
 'peng_dehuai':('official_biography','https://cpc.people.com.cn/GB/64162/126778/126780/7490066.html'),
 'tojo_hideki':('national_library_biography','https://www.ndl.go.jp/portrait/e/datas/142/'),
 'yamashita_tomoyuki':('academic_encyclopedia','https://onlinelibrary.wiley.com/doi/abs/10.1002/9781444338232.wbeow710'),
 'alexei_kaledin':('contemporary_encyclopedia','https://en.wikisource.org/wiki/1922_Encyclop%C3%A6dia_Britannica/Kaledin%2C_Alexei'),
}

def main():
 path=P/'presentation/data/general_lifespans.json';data=json.loads(path.read_text(encoding='utf-8'))
 for gid,person in data['generals'].items():
  kind,url=SOURCES[gid];person.update(reference_urls=[url],source_type=kind,source_status='consulted_year_pair_with_precision_limits',source_review_date='2026-10-18',likeness_approval=False)
  for stage in person['stages']:
   if stage['id']=='late':stage['label']='生前晚期' if person['late_stage_is_last_living_period'] else '暮年'
  person['precision_note']='仅登记生卒年；界面使用约岁，不将未知生日伪设为1月1日。'
  if person['date_precision']=='day':person['precision_note']='年龄按公历生日计算；逝世后停止增龄，显示生前阶段。'
  if gid in ['qi_xieyuan','guo_songling','waldersee']:person['source_status']='year_pair_secondary_reference_primary_check_pending'
  if gid=='li_zongren':person['source_disagreement']='采用黄埔同学会及故宫图书所载1891年；部分英文资料记1890年，保留分歧，未认证具体生日。'
  if gid=='chen_jiongming':person['source_disagreement']='采用国立公共资讯图书馆人物资料1878年；另有辞典记1877年，生日亦存在1月13日与18日差异，保留年精度。'
  if gid=='alexei_kaledin':person['source_disagreement']='俄历与公历死亡日期存在1月29日和2月11日两种表达；本表只用1861—1918年，不混用历法。'
  if gid=='hong_xiuquan':
   person['portrait_evidence_note']='未据可认证生前肖像复原；依据文字记述及后世纪念形象作游戏绘制。不能将误认木刻或1951年纪念像称为同年写生。'
   person['reference_urls'].append('https://m.thepaper.cn/newsDetail_forward_10832840')
  if gid=='lin_zexu':person['portrait_evidence_note']='馆藏图为后世绘制及题跋材料，非1840年照片；各阶段均为游戏绘制。'
 data['age_display_policy']='Use exact birthday only where day precision is explicitly sourced; otherwise show approximate age. No portrait before birth or before age 16. Posthumous views retain last living form and never keep aging.'
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'people':len(data['generals']),'referenced':len(SOURCES),'independent_likeness_approval':False}))

if __name__=='__main__':main()
