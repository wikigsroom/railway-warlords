"""Compile sourced place markers and land-clipped game control zones. No raster editing."""
from pathlib import Path
import hashlib
import json
import math
import sys

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]
sys.path.insert(0, str(ROOT / '.toolchain/python-libs'))
from pyproj import Transformer
from shapely import constrained_delaunay_triangles, voronoi_polygons
from shapely.geometry import Point, Polygon, MultiPoint, box
from shapely.ops import unary_union, transform
from compile_maps import ADMIN_LAYERS

SOURCES = {
    'county1914': {'title': '1914年6月2日大总统申令：各省所属道区域表（政府公报第745号）', 'url': 'https://zh.wikisource.org/zh-hans/各省所屬道區域表', 'scope': '当时县名和省道隶属；不提供县界或旧县署坐标'},
    'jingzhao': {'title': '1914年10月4日大总统申令：京兆地方区域表（政府公报第869号）', 'url': 'https://zh.wikisource.org/wiki/京兆地方區域表', 'scope': '京兆地方二十县的当时县名与隶属'},
    'funing': {'title': '抚宁区政府公开地方资料', 'url': 'https://www.chinafuning.gov.cn/main/file/2023-11-07/1699342459284297ec9de8ba5594a840018ba8b4219420c7.pdf', 'scope': '旧城沿革及直隶永平府到民国的建置'},
    'qianan': {'title': '迁安年鉴2025：历史沿革', 'url': 'https://www.qianan.gov.cn/main/file/2026-01-29/17696764596044028927d9be53906385019c08efce547ffc.pdf', 'scope': '1914年津海道，1928年河北省'},
    'yingkou': {'title': '营口市人民政府：历史沿革', 'url': 'https://www.yingkou.gov.cn/005/005001/005001002/about.html', 'scope': '1913年营口县，1914年辽沈道驻营口'},
    'beiyingzi': {'title': '河北省文化和旅游厅：北营子长城古村', 'url': 'https://whly.hebei.gov.cn/c/2026-01-12/583926.html', 'scope': '明代北翼城及关城以北约1.5公里的村落位置'},
    'wall_villages': {'title': '东北大学秦皇岛分校民族学学院：长城村落田野调查', 'url': 'https://mzxxy.neuq.edu.cn/info/1105/2712.htm', 'scope': '板厂峪、董家口、城子峪由明代戍边聚落演化的历史；不使用现代人口与道路设施'},
    'village_paper': {'title': '北京市文物局：文博2016年第3期，京西古村调查', 'url': 'https://wwj.beijing.gov.cn/bjww/resource/cms/article/362762/515607/2018071114324641086.pdf', 'scope': '传统村落与明清建筑；不采用现代旅游设施'},
    'cuandixia': {'title': '北京市规划自然资源委：爨底下传统村落', 'url': 'https://ghzrzyw.beijing.gov.cn/zhengwuxinxi/gzdt/mtg/202312/t20231220_3505469.html', 'scope': '约五百年历史、古军商道'},
    'sanjiadian': {'title': '北京市农业农村局：古往今来三家店', 'url': 'https://nyncj.beijing.gov.cn/nyj/snxx/gqxx/325890251/index.html', 'scope': '清代碑记和二百年以上古民居、京西商道'},
    'chadao': {'title': '北京市文物局：八达岭之藩篱——岔道城', 'url': 'https://wwj.beijing.gov.cn/bjww/wwjzzcslm/1737418/1738090/wwgs/623027/index.html', 'scope': '明代城堡与驿路村落'},
    'anqing': {'title': '安庆市投资促进局：安庆概况', 'url': 'https://tzcjj.anqing.gov.cn/zspt/2003708301.html', 'scope': '民国时期安徽省会驻安庆'},
    'kaifeng': {'title': '开封市党史和地方史志研究室：历史沿革', 'url': 'https://www.kfdsw.com/index/detail/id/3.html', 'scope': '开封的民国建置及省会沿革，1954年省会迁郑'},
    'tianjin': {'title': '保定市人民政府：历史沿革', 'url': 'https://www.baoding.gov.cn/bdgklist-70-37.html', 'scope': '1913年直隶省会迁天津；本表省城等级限定1920—1924'},
    'nanjing': {'title': '江苏省档案馆：省会迁镇江档案', 'url': 'https://m.dajs.gov.cn/art/2022/11/10/art_123_9708.html', 'scope': '1929年省会从南京迁镇江；1920—1924南京为江苏省城'},
    'geonames': {'title': 'GeoNames CN gazetteer / CC BY 4.0', 'url': 'https://download.geonames.org/export/dump/readme.txt', 'scope': '现代同名居民点的大致地理定位；不能用来判断1920年的行政等级'},
}

# Coordinates here are coarse search anchors, never purported historical survey points.
# The compiler records the matched GeoNames P feature and its precision separately.
# Names and ranks come from the 1914 order and specific local primary sources above.
COUNTIES = [
    ('funing', '抚宁', 119.24,39.88,'直隶','funing'),
    ('changli','昌黎',119.16,39.71,'直隶','county1914'),
    ('lulong','卢龙',118.87,39.89,'直隶','county1914'),
    ('qianan','迁安',118.70,40.00,'直隶','qianan'),
    ('zunhua','遵化',117.96,40.18,'直隶','county1914'),
    ('fengrun','丰润',118.16,39.83,'直隶','county1914'),
    ('yutian','玉田',117.73,39.89,'直隶','county1914'),
    ('leting','乐亭',118.91,39.43,'直隶','county1914'),
    ('baodi','宝坻',117.31,39.72,'京兆地方','jingzhao'),
    ('jixian','蓟县',117.41,40.04,'京兆地方','jingzhao'),
    ('jinghai','静海',116.93,38.94,'直隶','county1914'),
    ('qingxian','青县',116.82,38.58,'直隶','county1914'),
    ('cangxian','沧县',116.86,38.30,'直隶','county1914'),
    ('xianghe','香河',117.00,39.76,'京兆地方','jingzhao'),
    ('tongxian','通县',116.66,39.91,'京兆地方','jingzhao'),
    ('shunyi','顺义',116.66,40.13,'京兆地方','jingzhao'),
    ('miyun','密云',116.84,40.38,'京兆地方','jingzhao'),
    ('huairou','怀柔',116.63,40.32,'京兆地方','jingzhao'),
    ('changping','昌平',116.23,40.22,'京兆地方','jingzhao'),
    ('fangshan','房山',115.99,39.69,'京兆地方','county1914'),
    ('liangxiang','良乡',116.14,39.74,'京兆地方','county1914'),
    ('pinggu','平谷',117.12,40.14,'京兆地方','jingzhao'),
    ('sanhe','三河',117.08,39.98,'京兆地方','jingzhao'),
    ('yongqing','永清',116.49,39.32,'京兆地方','jingzhao'),
    ('sui_zhong','绥中',120.34,40.33,'奉天','county1914'),
    ('xingcheng','兴城',120.73,40.61,'奉天','county1914'),
    ('liaoyang','辽阳',123.18,41.27,'奉天','county1914'),
    ('haicheng','海城',122.75,40.85,'奉天','county1914'),
    ('xinmin','新民',122.82,42.00,'奉天','county1914'),
    ('zhengding','正定',114.57,38.15,'直隶','county1914'),
    ('dingxian','定县',114.99,38.52,'直隶','county1914'),
    ('hejian','河间',116.10,38.45,'直隶','county1914'),
    ('pingyao','平遥',112.18,37.19,'山西','county1914'),
    ('datong','大同',113.30,40.09,'山西','county1914'),
    ('linfen','临汾',111.52,36.09,'山西','county1914'),
    ('jining','济宁',116.59,35.42,'山东','county1914'),
    ('taian','泰安',117.13,36.19,'山东','county1914'),
    ('weixian','潍县',119.10,36.71,'山东','county1914'),
    ('linyi','临沂',118.34,35.06,'山东','county1914'),
    ('luoyang','洛阳',112.47,34.68,'河南','county1914'),
    ('anyang','安阳',114.35,36.10,'河南','county1914'),
    ('hefei','合肥',117.28,31.87,'安徽','county1914'),
    ('wuhu','芜湖',118.36,31.34,'安徽','county1914'),
    ('yangzhou','江都',119.43,32.40,'江苏','county1914'),
    ('changshu','常熟',120.75,31.65,'江苏','county1914'),
    ('jiaxing','嘉兴',120.75,30.77,'浙江','county1914'),
    ('shaoxing','绍兴',120.58,30.01,'浙江','county1914'),
    ('xiangyang','襄阳',112.14,32.01,'湖北','county1914'),
    ('huangpi','黄陂',114.38,30.88,'湖北','county1914'),
    ('xianning','咸宁',114.29,29.88,'湖北','county1914'),
    ('xiaogan','孝感',113.92,30.92,'湖北','county1914'),
    ('qishui','蕲水',115.27,30.45,'湖北','county1914'),
    ('suzhou_anhui','宿县',116.97,33.64,'安徽','county1914'),
    ('huaiyuan','怀远',117.18,32.97,'安徽','county1914'),
    ('chuxian','滁县',118.32,32.32,'安徽','county1914'),
    ('hexian','和县',118.35,31.72,'安徽','county1914'),
    ('jiangpu','江浦',118.63,32.06,'江苏','county1914'),
    ('liuhe','六合',118.85,32.34,'江苏','county1914'),
    ('zhaoqing','高要',112.46,23.05,'广东','county1914'),
    ('qujing','曲靖',103.79,25.49,'云南','county1914'),
]
VILLAGES = [
    ('beiyingzi','北营子',119.75,40.03,'直隶','beiyingzi','明代北翼城一带的长城村落，位于山海关关城以北约1.5公里。'),
    ('cuandixia','爨底下',115.42,39.97,'京兆地方','cuandixia','京西古军商道上的明清村落。'),
    ('lingshui','灵水',115.75,39.98,'京兆地方','village_paper','京西传统村落，保留明清民居与科举文化。'),
    ('sanjiadian','三家店',116.10,39.95,'京兆地方','sanjiadian','永定河出山口的古村与商道节点；不绘制后来的丰沙铁路。'),
    ('liuliqu','琉璃渠',116.09,39.94,'京兆地方','village_paper','京西古村与传统琉璃烧造所在地。'),
    ('chadao','岔道',115.98,40.36,'直隶','chadao','明代岔道堡周围的村落；民初属于直隶延庆县，不能提前归入1928年后的察哈尔省。'),
    ('banchangyu','板厂峪',119.565,40.193,'直隶','wall_villages','由明代长城关口营堡演化的聚落；沿真实山谷定位。'),
    ('dongjiakou','董家口',119.662,40.214,'直隶','wall_villages','明代戍边军户后裔村落，位于长城沿线。'),
    ('chengziyu','城子峪',119.623,40.220,'直隶','wall_villages','长城沿线的历史军户村落，采用同名村的位置。'),
]
CAPITALS = [
    ('anqing','安庆',117.04,30.51,'安徽','anqing','安徽省署驻地，使用民初省城等级。'),
    ('kaifeng','开封',114.31,34.80,'河南','kaifeng','民初河南省署驻地；郑州在这一时期不是省会。'),
]

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def geonames():
    path=ROOT/'design/geodata/settlements/CN.txt'
    if not path.exists():
        path=ROOT/'design/geodata/settlements/cities15000/cities15000.txt'
    if not path.exists(): raise RuntimeError('Download the official GeoNames gazetteer first.')
    points=[]
    for line in path.open(encoding='utf-8'):
        row=line.rstrip('\n').split('\t')
        if len(row)<19 or row[6]!='P' or row[8]!='CN':continue
        points.append({'id':int(row[0]),'name':row[1],'ascii':row[2], 'aliases':set(row[3].split(','))|{row[1],row[2]}, 'lat':float(row[4]),'lon':float(row[5]),'code':row[7]})
    return points,path

def matched(points, name, lon,lat, aliases=()):
    def normalized(s):return s.casefold().replace("'",'').replace('’','').replace(' ','')
    names={normalized(n) for n in [name,name+'县',name+'市',name+'区',name+'镇',name+'村',name+'城关',*aliases]}
    choices=[p for p in points if abs(p['lon']-lon)<.12 and abs(p['lat']-lat)<.12 and any(normalized(s) in names for s in p['aliases'])]
    if not choices:return None
    return min(choices,key=lambda p:(p['lat']-lat)**2+((p['lon']-lon)*math.cos(math.radians(lat)))**2)

def rows(points, path):
    result=[]; missing=[];gazetteer_sha=sha(path)
    unconfirmed_old_seats={'wuhu','xiangyang','xianning','luoyang'}
    county_dao={}
    for dao,keys in {
        '津海道':'funing changli lulong qianan zunhua fengrun yutian leting jinghai qingxian cangxian hejian',
        '保定道':'zhengding dingxian','辽沈道':'sui_zhong xingcheng liaoyang haicheng xinmin',
        '冀宁道':'pingyao','雁门道':'datong','河东道':'linfen',
        '济宁道':'jining linyi','济南道':'taian','胶东道':'weixian','河北道':'anyang',
        '安庆道':'hefei chuxian hexian','淮泗道':'suzhou_anhui huaiyuan',
        '金陵道':'jiangpu liuhe','苏常道':'changshu','淮扬道':'yangzhou',
        '钱塘道':'jiaxing','会稽道':'shaoxing','江汉道':'huangpi xiaogan qishui',
    }.items():
        for key in keys.split():county_dao[key]=dao
    extra_aliases={'cangxian':['沧州','Cangzhou'],'weixian':['潍坊','Weifang'],'dingxian':['定州','Dingzhou'],'suzhou_anhui':['宿州','Suzhou'],'chuxian':['滁州','Chuzhou'],'yangzhou':['扬州','Yangzhou'],'zhaoqing':['肇庆','Zhaoqing'],'jixian':['蓟州','Jizhou'],'qishui':['浠水','Xishui']}
    for raw,kind in [(r,'county') for r in COUNTIES]+[(r,'village') for r in VILLAGES]+[(r,'capital') for r in CAPITALS]:
        key,name,lon,lat,admin,source,*notes=raw
        if key in unconfirmed_old_seats:
            missing.append({'id':key,'name':name,'reason':'Modern city point does not reliably identify the period county seat; omitted pending old-town coordinate verification.'});continue
        # High-level modern names with relocated seats must match the old urban
        # settlement instead of today's county administration point.
        match_name='肇庆' if key=='zhaoqing' else '扬州' if key=='yangzhou' else name
        hit=matched(points,match_name,lon,lat,[key.title(),*extra_aliases.get(key,[])])
        if not hit:
            # The officially documented relative location is the only permitted
            # coarse village fallback. Other unresolved same-name points are omitted.
            if kind!='village':missing.append({'id':key,'name':name,'reason':'No matching populated-place coordinate; not drawn.'});continue
            coord={'lon':lon,'lat':lat,'geonames_id':None,'precision_m':1500,'method':'government_gazetteer_relative_location'}
        else:
            coord={'lon':hit['lon'],'lat':hit['lat'],'geonames_id':hit['id'],'feature_code':hit['code'],'precision_m':1000,'method':'GeoNames_same_named_populated_place','gazetteer_sha256':gazetteer_sha}
        historical_admin=admin+(' · '+county_dao[key] if key in county_dao else '')
        county_name=name if name.endswith('县') else name+'县'
        note=notes[0] if notes else f'民初{historical_admin}所属的{county_name}县城。'
        result.append({'id':'place_'+key,'name':name,'kind':kind,'administration':historical_admin,'province':admin,'rank_period':'1920—1924','active_from':'1920-01-01','longitude':coord['lon'],'latitude':coord['lat'],'location':coord,'sources':[source,'county1914','geonames'] if kind=='county' else [source,'geonames'], 'note':note})
    return result,missing

def projector(m):
    f=Transformer.from_crs('EPSG:4326',m['projection'],always_xy=True)
    extent=transform(f.transform,box(*m['geographic_bounds']))
    minx,_,_,maxy=extent.bounds
    factor=48/m['hex_radius_m']
    def world(lon,lat):
        x,y=f.transform(lon,lat);return ((x-minx)*factor,(maxy-y)*factor)
    return world

def mesh_geo(geometry):
    triangles=[]; borders=[]
    geos=[geometry] if geometry.geom_type=='Polygon' else list(geometry.geoms) if hasattr(geometry,'geoms') else []
    for g in geos:
        if g.geom_type!='Polygon' or g.area<.1:continue
        borders.append([[round(x,3),round(y,3)] for x,y in g.exterior.coords])
        for ring in g.interiors:borders.append([[round(x,3),round(y,3)] for x,y in ring.coords])
        for tri in constrained_delaunay_triangles(g).geoms:
            if not g.covers(tri):raise RuntimeError('A polity triangle left its surveyed land polygon.')
            triangles.extend([[round(x,3),round(y,3)] for x,y in list(tri.exterior.coords)[:3]])
    return triangles,borders

def control_zones(m, year):
    # A strategic control overlay is deliberately distinct from dated province
    # boundaries. Regions use the actual dated research province geometry. Only
    # provinces containing authored cities receive a control tint; contested
    # provinces split by their city influence. This is game control, not a claim
    # of surveyed military or county boundaries. The missing Jingzhao outline
    # is never invented; its verified county membership remains point metadata.
    cities=m['cities'];pts=[tuple(c['render_position']) for c in cities]
    if len(pts)<2:return []
    land=unary_union([Polygon(s['exterior'],s['holes']).buffer(0) for s in m['render_land']]).intersection(Polygon(m['render_extent']))
    world=projector(m);results=[]
    for region in ADMIN_LAYERS[year]:
        geo=transform(world,region['geometry']).intersection(land)
        if geo.is_empty:continue
        seeds=[c for c in cities if region['geometry'].covers(Point(c['lon_e6']/1e6,c['lat_e6']/1e6))]
        if not seeds:continue
        seeds_at=[tuple(c['render_position']) for c in seeds]
        cells=[geo] if len(seeds)==1 else list(voronoi_polygons(MultiPoint(seeds_at),extend_to=box(*geo.bounds).buffer(100),ordered=True).geoms)
        for city,cell in zip(seeds,cells):
            area=cell.intersection(geo);triangles,borders=mesh_geo(area)
            if triangles:results.append({'city_id':city['id'],'province':region['name'],'source_period':region['period'],'triangles':triangles,'borders':borders,'bounds':list(area.bounds),'area_px2':area.area,'maximum_influence_m':None})
    return results

def main():
    points,gazetteer=geonames();places,missing=rows(points,gazetteer)
    out={'schema':1,'version':'0.2.3','sources':SOURCES,'places':places,'maps':{},'role_overrides':{}}
    caps={'beijing':'national_capital','tianjin':'capital','fengtian_city':'capital','taiyuan':'capital','jinan':'capital','nanjing':'capital','hangzhou':'capital','wuchang':'capital','changsha':'capital','nanchang':'capital','fuzhou':'capital','guangzhou':'capital','nanning':'capital','kunming':'capital','guiyang':'capital','chengdu':'capital','xian':'capital','lanzhou':'capital'}
    counties={'zhuozhou','guan','luanzhou','dezhou','xinyang','zhengzhou','guilin','pingxiang','yueyang','suzhou','zhenjiang','hanyang','xuzhou','ningbo'}
    towns={'nanyuan','changxindian','langfang','yangcun','machang','bengbu','pukou','zhuzhou','shijiazhuang','tangshan'}
    for file in sorted((PROJECT/'content/maps').glob('*.json')):
        m=json.loads(file.read_text(encoding='utf-8'))
        if 'geographic_bounds' not in m:continue
        world=projector(m);xmin,ymin,xmax,ymax=m['geographic_bounds']
        markers=[]
        for p in places:
            if not xmin<=p['longitude']<=xmax or not ymin<=p['latitude']<=ymax:continue
            node=dict(p);node['world']=[round(v,2) for v in world(p['longitude'],p['latitude'])]
            markers.append(node)
        for city in m['cities']:
            role=caps.get(city['id'],'pass' if city['id']=='jiumenkou' else 'county' if city['id']=='shanhaiguan' or city['id'] in counties else 'market' if city['id'] in towns else 'city')
            out['role_overrides'][city['id']]={'kind':role,'rank_period':'1920—1924','sources':['tianjin'] if city['id']=='tianjin' else ['nanjing'] if city['id']=='nanjing' else ['county1914'], 'note': '军用城池等级与历史行政等级分别显示。'}
        zones={year:control_zones(m,year) for year in ['1920','1922','1924']}
        out['maps'][m['id']]={'markers':markers,'control_zones_by_year':zones,'map_sha256':sha(file),'historical_county_boundaries_claimed':False,'control_legend':'当前战局势力 · 城池控制区','control_geometry':'ENP-China dated province polygons, clipped to surveyed Natural Earth land; contested provinces subdivided by city control influence; not a historical military border survey'}
        print(m['id'],len(markers),'additional places',len(zones['1924']),'land-only zones',flush=True)
    target=PROJECT/'presentation/data/settlements_v023.json';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    report={'passed':True,'version':'0.2.3','places':len(places),'kinds':{k:sum(p['kind']==k for p in places) for k in ['village','market','county','capital']},'omitted_unresolved':missing,'gazetteer':str(gazetteer.relative_to(ROOT)),'gazetteer_sha256':sha(gazetteer),'presentation_data_sha256':sha(target),'immutable_gameplay_maps':{k:v['map_sha256'] for k,v in out['maps'].items()},'source_count':len(SOURCES),'raster_editing':False}
    (PROJECT/'reports/settlement_compilation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'places':len(places),'omitted':missing},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
