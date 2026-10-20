"""Fact records, not a fabricated continuous service history or order of battle."""
from pathlib import Path
import hashlib,json,unicodedata

BASE=Path(__file__).resolve().parent
def save(name,value):
    (BASE/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def ident(name):return 'cn_'+''.join(format(ord(c),'x') for c in name)
def person(name,born,died,title,year,level,side,sources,**extra):
    return dict(id=ident(name),name=name,birth_year=born,death_year=died,date_precision='year',country='China',historical_side=side,
        documented_title=title,documented_year=year,command_level=level,appointment_start=None,appointment_end=None,
        appointment_date_status='office_attested; full_tenure_requires_review',source_ids=[r['id'] for r in sources],
        reference_urls=[r['url'] for r in sources],eligibility_status='historical_identity_and_qualifying_office_documented; scenario_appointments_require_review',
        likeness_source_status='no_independent_generated_likeness_approval',portrait_production_status='pending_four_independent_Sub2_originals',**extra)

# The year is an attested office reference, never an invented first appointment.
CPC=[
 ('朱德',1886,1976,'中国工农红军第4军军长',1928,'army_or_higher'),
 ('刘伯承',1892,1986,'八路军第129师师长',1937,'division'),
 ('贺龙',1896,1969,'八路军第120师师长',1937,'division'),
 ('徐向前',1901,1990,'八路军第129师副师长',1937,'deputy_division'),
 ('陈毅',1901,1972,'中国工农红军第22军军长',1930,'army_or_higher'),
 ('聂荣臻',1899,1992,'晋察冀军区司令员兼政治委员',1937,'army_or_higher'),
 ('陈赓',1903,1961,'八路军第129师第386旅旅长',1937,'brigade'),
 ('黄克诚',1902,1986,'冀鲁豫军区司令员兼政治委员',1940,'army_or_higher'),
 ('徐海东',1900,1970,'八路军第115师第344旅旅长',1937,'brigade'),
 ('张云逸',1892,1974,'中国工农红军第7军军长',1929,'army_or_higher'),
 ('张宗逊',1908,1998,'八路军第120师第358旅旅长',1937,'brigade'),
 ('许世友',1905,1985,'八路军山东纵队第3旅旅长',1940,'brigade'),
 ('王震',1908,1993,'八路军第120师第359旅旅长',None,'brigade'),
 ('粟裕',1907,1984,'中国工农红军挺进师师长',1935,'division'),
 ('许光达',1908,1969,'中国工农红军第6军第17师师长',None,'division'),
 ('罗炳辉',1897,1946,'中国工农红军第22军军长',1932,'army_or_higher'),
 ('周士第',1900,1979,'国民革命军第25师师长',1927,'division'),
 ('肖劲光',1903,1989,'中国工农红军第29军军长',None,'army_or_higher'),
 ('王宏坤',1909,1993,'八路军第129师第385旅旅长',1937,'brigade'),
 ('叶剑英',1897,1986,'国民革命军新编第2师代师长',1926,'division'),
 ('刘志丹',1903,1936,'中国工农红军第28军军长',1935,'army_or_higher'),
 ('黄公略',1898,1931,'中国工农红军第6军军长',1930,'army_or_higher'),
 ('叶挺',1896,1946,'国民革命军第11军副军长兼第24师师长',1927,'deputy_army_or_higher'),
 ('林彪',1907,1971,'八路军第115师师长',1937,'division'),
 ('左权',1905,1942,'中国工农红军新编第12军军长',None,'army_or_higher'),
]
def cpc():
    index={r['name']:r for r in json.loads((BASE/'research/cpc/biographies.json').read_text(encoding='utf-8'))['rows']}
    out=[];register={}
    for name,born,died,title,year,level in CPC:
        r=index[name];text=unicodedata.normalize('NFKC',(BASE/'research/cpc'/r['text_file']).read_text(encoding='utf-8'))
        assert (str(born) in text or name=='许世友') and str(died) in text,name
        source=dict(id=r['source_id'],url=r['url'],sha256=r['source_sha256'],publisher='People.cn, CPC News / institutional military-history biographies')
        register[source['id']]=source
        extra={}
        source_list=[source]
        if name=='许世友':
            extra['life_year_note']='1905 follows the 2019 Xinhua institutional biography reproduced by the Ministry of National Defense. The older CPC biography gives 1906. The discrepancy is retained and ages remain approximate.'
            modern=dict(id='mod_xu_shiyou_2019',url='https://www.mod.gov.cn/2018gfbztlbmb/2019-09/20/content_4850807.htm',publisher='Ministry of National Defense / Xinhua',fact_review='Birth year 1905 verified through web research; older account gives 1906.',raw_download_sha256=None)
            register[modern['id']]=modern;source_list.append(modern)
        if name=='叶挺':
            modern=dict(id='nanchang_memorial_ye_ting_2021',url='https://cpc.people.com.cn/n1/2021/0122/c64387-32009116.html',publisher='People.cn / Nanchang August First Uprising Memorial director',fact_review='1927 command of 11th Army, 24th Division verified through institutional interview.',raw_download_sha256=None)
            register[modern['id']]=modern;source_list.append(modern)
        if name in ['周士第','叶剑英']:
            extra['historical_side_note']='The cited National Revolutionary Army command predates later Communist appointments; no faction membership is backdated.'
        out.append(person(name,born,died,title,year,level,'ccp',source_list,**extra))
    save('cpc_commanders.json',dict(schema='commander-expansion-research-1',coverage_complete=False,people=out,source_register=register))
    return out

# ECCP is the Library of Congress Orientalia Division biographical work, ed.
# Arthur Hummel, U.S. Government Printing Office, 1943/1944. PDF page numbers
# below refer to complete digitizations, not a downloaded preface or a search snippet.
ECCP=[
 ('陈国瑞',1837,1883,'清军总兵、提督衔',1868,'historical_regional_command',1,[106,107]),
 ('程学启',1830,1864,'淮军将领、总兵',1862,'historical_field_command',1,[132,133]),
 ('江忠源',1812,1854,'江南军务帮办、楚勇统帅',1853,'historical_field_command',1,[153,154]),
 ('冯子材',1818,1903,'广西提督',1862,'historical_regional_command',1,[261,262,263]),
 ('胡林翼',1812,1861,'湖北巡抚、湘军统帅',1856,'historical_regional_command',1,[350,351,352]),
 ('荣禄',1836,1903,'统率武卫军的军政大臣',1899,'national_high_command',1,[422,423,424]),
 ('李续宾',1818,1858,'湘军统帅',1856,'historical_field_command',1,[480,481]),
 ('刘铭传',1836,1896,'淮军铭字军统帅',1862,'historical_field_command',1,[543,544,545]),
 ('罗泽南',1808,1856,'湘勇统帅',1854,'historical_field_command',1,[557,558]),
 ('鲍超',1828,1886,'浙江提督、霆军统帅',1862,'historical_regional_command',2,[12,13]),
 ('多隆阿',1817,1864,'清军统帅',1862,'historical_field_command',2,[12]),
 ('彭玉麟',1816,1890,'湘军水师统帅',1862,'fleet',2,[20,21,22]),
 ('杨岳斌',1822,1890,'湘军水师统帅',1863,'fleet',2,[21,22]),
 ('宋庆',1820,1902,'南阳镇总兵、毅军统帅',1865,'historical_regional_command',2,[89,90,91]),
 ('曾国荃',1824,1890,'湘军统帅',1860,'historical_field_command',2,[152,153,154]),
 ('左宗棠',1812,1885,'浙江军务统帅',1861,'historical_regional_command',2,[165,166,167,168,169]),
 ('裕谦',1793,1841,'钦差大臣、浙江防务统筹',1841,'historical_theater_command',2,[342,343,344]),
 ('袁世凯',1859,1916,'新建陆军督练',1895,'historical_field_command',2,[353,354,355]),
 ('王士珍',1861,1930,'北洋陆军师级统帅',1905,'division',2,[354]),
 ('冯国璋',1859,1919,'北洋陆军师级统帅',1905,'division',2,[354]),
 ('董福祥',1839,1908,'甘军统帅',1898,'historical_field_command',1,[423]),
 ('吴长庆',1834,1884,'驻朝清军统帅',1882,'historical_field_command',1,[500]),
 ('刘锦棠',1844,1894,'西北清军统帅',1870,'historical_field_command',2,[168]),
 ('刘松山',1833,1870,'西北清军北路统帅',1869,'historical_field_command',2,[168]),
 ('姜桂题',1843,1922,'毅军统帅',1908,'historical_field_command',2,[91]),
 ('李续宜',1823,1863,'湘军统帅、安徽巡抚',1861,'historical_regional_command',1,[481]),
 ('孤拔',1827,1885,'法国远东舰队司令',1884,'fleet',1,[544]),
 ('李士卑斯',1828,1897,'法国海军指挥官',1884,'naval_squadron',1,[544]),
 ('戈登',1833,1885,'常胜军统帅',1863,'historical_field_command',1,[482]),
 ('华尔',1831,1862,'常胜军统帅',1862,'historical_field_command',1,[259,482]),
 ('白齐文',1836,1865,'常胜军统帅',1862,'historical_field_command',1,[259,482]),
 ('何伯',1808,1881,'英国海军司令',1862,'fleet',1,[259]),
 ('卜罗德',1808,1862,'法国海军司令',1862,'fleet',1,[259]),
 ('陈玉成',1837,1862,'太平天国英王、前军主将',1859,'historical_field_command',1,[121,122]),
 ('李秀成',1823,1864,'太平天国忠王、后军主将',1859,'historical_field_command',1,[476,477,478,479,480]),
]
def eccp():
    register={};out=[]
    for volume in [1,2]:
        f=BASE/f'research/eccp/eccp_volume_{volume}.pdf'
        sid=f'eccp_volume_{volume}'
        register[sid]=dict(id=sid,url=f'https://www.bnasie.eu/Asset/Source/bnBook_ID-2729_No-0{volume+2}.pdf',
            sha256=hashlib.sha256(f.read_bytes()).hexdigest(),publisher='Library of Congress, Orientalia Division; U.S. Government Printing Office',
            title="Eminent Chinese of the Ch'ing Period",edition_year=1943 if volume==1 else 1944,volume=volume,
            digitization_catalog='https://www.bnasie.eu/BN/Books?ID=2729')
    for name,born,died,title,year,level,volume,pages in ECCP:
        sid=f'eccp_volume_{volume}';side='taiping' if name in ['陈玉成','李秀成'] else 'qing';extra={}
        if name in ['孤拔','李士卑斯','卜罗德']:
            extra['country']='France';side='french_empire'
        elif name=='何伯':extra['country']='Britain';side='british_empire'
        elif name=='戈登':extra['country']='Britain'
        elif name in ['华尔','白齐文']:extra['country']='United States'
        if name in ['陈国瑞','程学启','李续宾','李续宜']:
            extra['life_year_note']='Birth year is calculated from the scholarly biography\'s death year and traditional sui age. Displayed ages remain approximate; no exact birthday is asserted.'
        if name in ['王士珍','冯国璋']:
            extra['office_note']='The source names these officers among the early Beiyang division commanders. It does not identify a specific division number here; no number or complete tenure is invented.'
        if name=='罗泽南':extra['life_year_note']='The cited biography gives 19 January 1808; some Chinese-year accounts give 1807. This record uses the cited Gregorian year and flags the discrepancy.'
        source_list=[register[sid]]
        if name in ['陈玉成','李秀成']:
            modern=dict(id='yanjin_chen_yucheng' if name=='陈玉成' else 'national_museum_li_xiucheng',
                url='https://www.yanjin.gov.cn/newsinfo/17077.html' if name=='陈玉成' else 'https://www.chnmuseum.cn/zp/zpml/csp/202112/t20211214_253147.shtml',
                publisher='Yanjin County Government' if name=='陈玉成' else 'National Museum of China',
                fact_review='Institutional biography verifies the modern birth-year convention; cross-checked through the web research tool.',raw_download_sha256=None)
            register[modern['id']]=modern;source_list.append(modern)
            extra['life_year_note']='Modern institutional birth-year convention used. Earlier English-language biography uses a traditional-age statement; the difference is retained in the source register.'
        country=extra.pop('country','China')
        r=person(name,born,died,title,year,level,side,source_list,**extra)
        r['country']=country;r['source_pdf_pages']={sid:pages}
        if country!='China':
            r['youth_clothing']='Plain dark nineteenth-century European civilian jacket and shirt, bareheaded; no military rank, medals, invented badges, modern camouflage or modern costume.'
            r['adult_clothing']='Restrained dark nineteenth-century European officer tunic, bareheaded, without invented rank insignia or medals.'
            r['portrait_uniform_not_before']=9999
        out.append(r)
    save('eccp_commanders.json',dict(schema='commander-expansion-research-1',coverage_complete=False,people=out,source_register=register,
        interpretation='Qing-era armies, fleets and regional commands retain their historical titles. They are not relabeled as modern numbered divisions. Office dates are isolated attested references, not complete tenures.'))
    return out

if __name__=='__main__':
    a=cpc();b=eccp()
    print(json.dumps(dict(cpc=len(a),eccp=len(b),total_new_curated=len(a)+len(b))))
