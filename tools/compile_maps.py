"""Compile playable hex maps from actual Natural Earth geometry; no raster manipulation."""
from pathlib import Path
import json, math, sys, hashlib, heapq, sqlite3
ROOT = Path(__file__).resolve().parents[3]
PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.toolchain/python-libs'))
import shapefile
from shapely.geometry import shape, Point, box, LineString
from shapely.ops import unary_union, transform
from shapely.prepared import prep
from pyproj import Transformer, CRS
from shapely import from_wkb

ELEVATION_PATH=ROOT/'design/geodata/srtm90m/samples.json'
ELEVATION=json.loads(ELEVATION_PATH.read_text(encoding='utf-8'))['samples'] if ELEVATION_PATH.exists() else {}
ADMIN_ROOT=ROOT/'design/geodata/republican_provinces'

def historical_admin(period):
    """Use research vectors, correcting independently verified name/date anachronisms."""
    wgs=Transformer.from_crs('EPSG:3857','EPSG:4326',always_xy=True)
    records=[]
    if period=='1912-1921':
        reader=shapefile.Reader(str(ADMIN_ROOT/'1912-1921_orig/1912-1921_orig/1912_1921.shp'),encoding='utf-8')
        records=[(r.record.as_dict(),shape(r.shape.__geo_interface__)) for r in reader.iterShapeRecords()]
        prefix='p_12_21'
    else:
        db=sqlite3.connect(ADMIN_ROOT/'1922-1928_gpkg/1922_1928.gpkg');db.row_factory=sqlite3.Row
        for row in db.execute('SELECT * FROM "1922_1928"'):
            blob=row['geom'];envelope=(blob[3]>>1)&7;offset=8+{0:0,1:32,2:48,3:48,4:64}[envelope]
            records.append((dict(row),from_wkb(blob[offset:])))
        db.close();prefix='p_22_28'
    names={'Hebei':'直隶','Jiangxi':'江西','Jilin':'吉林','Ningxia':'甘肃','Qinghai':'甘肃','Gansu':'甘肃','Chuanbian':'川边特别区','Chahaer':'察哈尔特别区','Jehol':'热河特别区','Suiyuan':'绥远特别区','Heilongjiang':'黑龙江','Shanxi':'山西','Shaanxi':'陕西','Yunnan':'云南','Guizhou':'贵州','Guangdong':'广东','Guangxi':'广西','Sichuan':'四川','Henan':'河南','Hubei':'湖北','Hunan':'湖南','Anhui':'安徽','Fengtian':'奉天','Zhejiang':'浙江','Shandong':'山东','Fujian':'福建','Jiangsu':'江苏','Xinjiang':'新疆','Xizang':'西藏地方','Mongolia':'蒙古地方'}
    merged={}
    for record,geo in records:
        english=record[prefix+'_na'];name=names.get(english,record[prefix+'_nz'])
        if not name:continue
        merged.setdefault(name,[]).append(transform(wgs.transform,geo))
    return [{'name':name,'geometry':unary_union(geos).buffer(0),'period':period} for name,geos in merged.items()]

ADMIN_LAYERS={y:historical_admin(p) for y,p in [('1920','1912-1921'),('1922','1922-1928'),('1924','1922-1928')]} if ADMIN_ROOT.exists() else {}

def terrain_from_elevation(lat,lon,radius,samples=None):
    lat=round(lat,6);lon=round(lon,6)
    delta=radius*.5/111320;delta_lon=delta/math.cos(math.radians(lat))
    keys=[f'{y:.6f},{x:.6f}' for y,x in [(lat,lon),(lat+delta,lon),(lat-delta,lon),(lat,lon+delta_lon),(lat,lon-delta_lon)]]
    samples=ELEVATION if samples is None else samples
    values=[samples.get(k) for k in keys];valid=[v for v in values if v is not None]
    if not valid:return 'plain',None,None
    center=values[0] if values[0] is not None else sum(valid)/len(valid);relief=max(valid)-min(valid)
    terrain='plain'
    if center>=2200 and relief>=250:terrain='peak'
    elif (center>=450 and relief>=250) or relief>=450:terrain='mountain'
    elif relief>=75 and center>=100:terrain='hill'
    return terrain,round(center),round(relief)

CITY_ROWS = [
 ('beijing','北京',116.407,39.904,3,'zhili'),('nanyuan','南苑',116.40,39.78,1,'anhui'),
 ('changxindian','长辛店',116.20,39.83,1,'zhili'),('tianjin','天津',117.203,39.084,3,'zhili'),
 ('baoding','保定',115.48,38.87,2,'zhili'),('zhuozhou','涿州',115.98,39.49,1,'anhui'),
 ('langfang','廊坊',116.70,39.54,1,'anhui'),('yangcun','杨村',117.05,39.40,1,'anhui'),
 ('guan','固安',116.30,39.43,1,'zhili'),('machang','马厂',116.87,38.74,1,'zhili'),
 ('tangshan','唐山',118.18,39.63,2,'zhili'),('luanzhou','滦州',118.70,39.74,1,'zhili'),
 ('qinhuangdao','秦皇岛',119.60,39.94,1,'fengtian'),('shanhaiguan','山海关',119.76,40.00,2,'fengtian'),
 ('jiumenkou','九门口',119.7475,40.1161,1,'fengtian'),('jinzhou','锦州',121.13,41.10,2,'fengtian'),
 ('fengtian_city','奉天',123.43,41.80,3,'fengtian'),('changchun','长春',125.32,43.82,2,'fengtian'),
 ('shijiazhuang','石家庄',114.51,38.04,2,'zhili'),('taiyuan','太原',112.55,37.87,3,'jin'),
 ('dezhou','德州',116.36,37.45,1,'zhili'),('jinan','济南',117.12,36.65,2,'zhili'),
 ('qingdao','青岛',120.38,36.07,2,'zhili'),('zhengzhou','郑州',113.63,34.75,2,'zhili'),
 ('xuzhou','徐州',117.28,34.20,2,'jiangsu'),('bengbu','蚌埠',117.39,32.92,1,'anhui'),
 ('pukou','浦口',118.72,32.10,1,'jiangsu'),('nanjing','南京',118.80,32.06,3,'jiangsu'),
 ('zhenjiang','镇江',119.43,32.20,1,'jiangsu'),('suzhou','苏州',120.59,31.30,1,'jiangsu'),
 ('shanghai','上海',121.47,31.23,3,'jiangsu'),('hangzhou','杭州',120.15,30.27,2,'zhejiang'),
 ('ningbo','宁波',121.55,29.87,1,'zhejiang'),('xinyang','信阳',114.09,32.15,1,'zhili'),
 ('hankou','汉口',114.29,30.59,3,'zhili'),('wuchang','武昌',114.32,30.55,2,'zhili'),
 ('hanyang','汉阳',114.26,30.55,1,'zhili'),('yichang','宜昌',111.29,30.69,1,'zhili'),
 ('changsha','长沙',112.94,28.23,2,'xiang'),('nanchang','南昌',115.86,28.68,2,'zhili'),
 ('fuzhou','福州',119.30,26.07,2,'zhili'),('guangzhou','广州',113.26,23.13,3,'south'),
 ('shaoguan','韶关',113.60,24.81,1,'south'),('shantou','汕头',116.68,23.35,1,'south'),
 ('nanning','南宁',108.32,22.82,2,'gui'),('guilin','桂林',110.29,25.27,2,'gui'),
 ('kunming','昆明',102.71,25.04,3,'dian'),('guiyang','贵阳',106.63,26.65,2,'dian'),
 ('chongqing','重庆',106.55,29.56,2,'chuan'),('chengdu','成都',104.07,30.67,3,'chuan'),
 ('xian','西安',108.94,34.34,2,'zhili'),('lanzhou','兰州',103.83,36.06,2,'ma'),
 ('pingxiang','萍乡',113.85,27.63,1,'xiang'),('zhuzhou','株洲',113.13,27.83,1,'xiang'),
 ('yueyang','岳阳',113.13,29.37,1,'xiang'),('jiujiang','九江',115.99,29.71,1,'zhili'),
]
RAILS = [
 ('jingfeng','京奉铁路','1912-01-01',['beijing','langfang','yangcun','tianjin','tangshan','luanzhou','qinhuangdao','shanhaiguan','jinzhou','fengtian_city']),
 ('jinghan','京汉铁路','1906-04-01',['beijing','changxindian','zhuozhou','baoding','shijiazhuang','zhengzhou','xinyang','hankou']),
 ('jinpu','津浦铁路','1912-11-01',['tianjin','dezhou','jinan','xuzhou','bengbu','pukou']),
 ('zhengtai','正太铁路','1907-10-01',['shijiazhuang','taiyuan']),
 ('jiaoji','胶济铁路','1904-06-01',['jinan','qingdao']),
 ('huning','沪宁铁路','1908-04-01',['nanjing','zhenjiang','suzhou','shanghai']),
 ('huhang','沪杭铁路','1909-07-01',['shanghai','hangzhou']),
 ('yuehan_south','粤汉铁路南段','1916-06-01',['guangzhou','shaoguan']),
 ('yuehan_north','粤汉铁路北段','1918-09-01',['wuchang','yueyang','changsha','zhuzhou']),
 ('zhuping','株萍铁路','1905-12-01',['zhuzhou','pingxiang']),
]
DIRECTIONS=[(1,0),(1,-1),(0,-1),(-1,0),(-1,1),(0,1)]
def distance(a,b): return (abs(a[0]-b[0])+abs(a[1]-b[1])+abs(sum(a)-sum(b)))//2
def pos(p): return {'q':p[0],'r':p[1]}
def output(path,data): path.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')

def compile_map(map_id, bounds, radius, *, output_path=None, max_cells=4096,
                land_source='ne_50m_land', elevation_samples=None,
                elevation_source='SRTM90m_v3', primary_river_geometries=None,
                port_snap_max_m=None):
    xmin,ymin,xmax,ymax=bounds
    crs=CRS.from_proj4(f'+proj=laea +lat_0={(ymin+ymax)/2} +lon_0={(xmin+xmax)/2} +datum=WGS84 +units=m')
    forward=Transformer.from_crs('EPSG:4326',crs,always_xy=True)
    inverse=Transformer.from_crs(crs,'EPSG:4326',always_xy=True)
    region=box(xmin-1,ymin-1,xmax+1,ymax+1)
    land_geos=[]
    for sr in shapefile.Reader(str(ROOT/'design/geodata'/land_source/(land_source+'.shp'))).iterShapes():
        geo=shape(sr.__geo_interface__)
        if geo.intersects(region): land_geos.append(geo.intersection(region))
    land=unary_union(land_geos); prepared=prep(land)
    river_geos=[]; river_names=[]
    reader=shapefile.Reader(str(ROOT/'design/geodata/ne_10m_rivers_lake_centerlines/ne_10m_rivers_lake_centerlines.shp'),encoding='utf-8')
    for sr in reader.iterShapeRecords():
        record=sr.record.as_dict(); name=str(record.get('name',''))
        geo=shape(sr.shape.__geo_interface__)
        if geo.intersects(region) and (record.get('scalerank',10)<=4 or any(k in name.lower() for k in ['yangtze','huang','hai','luan','han','huai','pearl'])):
            river_geos.append(transform(forward.transform,geo.intersection(region))); river_names.append(name)
    rivers=unary_union(river_geos) if river_geos else LineString()
    if primary_river_geometries is not None:
        rivers=transform(forward.transform,unary_union(primary_river_geometries))
    projected=transform(forward.transform,box(*bounds)); minx,miny,maxx,maxy=projected.bounds
    origin_x=minx; origin_y=maxy
    cols=math.ceil((maxx-minx)/(1.5*radius))+1
    rows=math.ceil((maxy-miny)/(math.sqrt(3)*radius))+1
    cells=[]; grid={}; legal=[]
    historical_land=prep(unary_union([a['geometry'] for a in ADMIN_LAYERS['1920']])) if ADMIN_LAYERS else None
    for q in range(cols):
        for row in range(rows):
            r=row-q//2
            x=origin_x+1.5*radius*q; y=origin_y-math.sqrt(3)*radius*(r+q*.5)
            lon,lat=inverse.transform(x,y)
            if not(xmin-.05<=lon<=xmax+.05 and ymin-.05<=lat<=ymax+.05): continue
            terrestrial=prepared.contains(Point(lon,lat))
            terrain='plain' if terrestrial else 'sea'; restriction=''
            # Taiwan and territory beyond the authored Chinese theater are not invented warlord holdings.
            if terrestrial and historical_land is not None and not historical_land.covers(Point(lon,lat)):restriction='restricted'
            elevation=None;relief=None
            if terrestrial:
                terrain,elevation,relief=terrain_from_elevation(lat,lon,radius,elevation_samples)
                if not rivers.is_empty and rivers.distance(Point(x,y))<radius*.30:terrain='river'
            key=(q,r); cell={'id':f'c_{q}_{r}','position':pos(key),'terrain_id':terrain,'region_id':restriction or 'theater','lon_e6':round(lon*1e6),'lat_e6':round(lat*1e6),'elevation_m':elevation,'relief_sample_m':relief,'natural_terrain_id':terrain,'terrain_source':elevation_source+'_five_point_samples' if elevation is not None else 'Natural_Earth_land_water'}
            cells.append(cell);grid[key]=cell
            if terrestrial and not restriction:legal.append((key,lon,lat))
    def split_lines(geo):
        if geo.is_empty:return []
        if geo.geom_type=='LineString':return [geo]
        if geo.geom_type in ['MultiLineString','GeometryCollection']:return [x for g in geo.geoms for x in split_lines(g)]
        return []
    def projected_hex(x,y):
        q=(x-origin_x)/(1.5*radius);r=(origin_y-y)/(math.sqrt(3)*radius)-q*.5
        c=[q,-q-r,r];a=[round(v) for v in c];d=[abs(c[i]-a[i]) for i in range(3)]
        i=max(range(3),key=lambda n:d[n]);a[i]=-sum(a[j] for j in range(3) if j!=i)
        return a[0],a[2]
    # Snap actual river centerlines continuously; water topology follows geometry, not painted decoration.
    for line in split_lines(rivers):
        for i in range(math.ceil(line.length/(radius*.3))+1):
            point=line.interpolate(min(i*radius*.3,line.length));key=projected_hex(point.x,point.y)
            if key in grid and grid[key]['terrain_id']!='sea' and grid[key]['region_id']!='restricted':grid[key]['terrain_id']='river'
    cities=[]; taken=set()
    for cid,name,lon,lat,level,owner in CITY_ROWS:
        if not(xmin<=lon<=xmax and ymin<=lat<=ymax):continue
        x,y=forward.transform(lon,lat)
        candidates=[c for c in legal if grid[c[0]]['terrain_id']!='river']
        actual_lines=split_lines(rivers)
        if actual_lines:
            local=min(actual_lines,key=lambda l:l.distance(Point(x,y)));t=local.project(Point(x,y));before=local.interpolate(max(0,t-radius*.2));after=local.interpolate(min(local.length,t+radius*.2));foot=local.interpolate(t)
            vx,vy=after.x-before.x,after.y-before.y
            side=vx*(y-foot.y)-vy*(x-foot.x)
            if cid=='pukou':
                # Pukou is the north-bank rail terminus. Its approximate city point is
                # within the source centerline tolerance, so use Nanjing's opposite bank.
                nx,ny=forward.transform(118.80,32.06)
                side=-(vx*(ny-foot.y)-vy*(nx-foot.x))
            def same_bank(c):
                cx,cy=forward.transform(c[1],c[2]);return (vx*(cy-foot.y)-vy*(cx-foot.x))*side>=0
            bank_candidates=[c for c in candidates if same_bank(c)]
            if bank_candidates:candidates=bank_candidates
        is_port=cid in ['tianjin','qinhuangdao','shanghai','qingdao','nanjing','pukou','hankou','wuchang','hanyang','guangzhou','fuzhou','yichang','jiujiang']
        if is_port:
            shore=[c for c in candidates if any(grid.get((c[0][0]+d[0],c[0][1]+d[1]),{}).get('terrain_id') in ['river','sea'] for d in DIRECTIONS)]
            if port_snap_max_m is not None:
                shore=[c for c in shore if math.dist(forward.transform(c[1],c[2]),(x,y))<=port_snap_max_m]
            if shore:candidates=shore
        candidates.sort(key=lambda c:(forward.transform(c[1],c[2])[0]-x)**2+(forward.transform(c[1],c[2])[1]-y)**2)
        key=next(c[0] for c in candidates if c[0] not in taken)
        taken.add(key);grid[key]['terrain_id']='city'
        owner={'jin':'shanxi','dian':'yunnan','south':'guangdong','chuan':'sichuan','xiang':'local_hunan','gui':'local_guangxi','ma':'local_gansu'}.get(owner,owner)
        names_at_date={'zhuozhou':'涿县','luanzhou':'滦县'}
        cities.append({'id':cid,'name':names_at_date.get(cid,name),'modern_reference_name':name,'lon_e6':round(lon*1e6),'lat_e6':round(lat*1e6),'position':pos(key),'render_position':[round((x-origin_x)/radius*48,2),round((origin_y-y)/radius*48,2)],'level':level,'reference_owner':owner,'key_city':level>=2,'port':cid in ['tianjin','qinhuangdao','shanghai','qingdao','nanjing','pukou','hankou','wuchang','hanyang','guangzhou','fuzhou','yichang','jiujiang'],'strategic_hex_displacement_m':round(math.hypot(origin_x+1.5*radius*key[0]-x,origin_y-math.sqrt(3)*radius*(key[1]+key[0]*.5)-y))})
    cityindex={c['id']:c for c in cities}
    # An unresolved authority is a geographic reference point, never a fabricated faction holding.
    reference_only={'changsha':'湖南地方当局','zhuzhou':'湖南地方当局','pingxiang':'湖南地方当局','nanning':'广西地方当局','guilin':'广西地方当局','guiyang':'贵州地方当局','lanzhou':'甘肃地方当局','xian':'陕西地方当局','chengdu':'四川分区军政','chongqing':'四川分区军政'}
    for city in cities:
        if city['id'] in reference_only:
            city['conquest_reference_only']=True
            city['authority_label']=reference_only[city['id']]
            city['historical_control_status']='not_published_as_contested_until_city_date_control_is_sourced'
        if city['id']=='guangzhou' or city['id']=='shaoguan' or city['id']=='shantou':
            city['reference_only_before']='1921-01-01'
            city['authority_label']='广东军政变动区'
        if city['id']=='shantou':city['control_overrides_by_year']={'1924':'dongjiang'}
        if city['id']=='bengbu':
            city['reference_only_from']='1921-01-01'
            city['authority_label']='安徽地方军政（逐城控制待核）'
            city['historical_control_status']='later_anhui_government_changes_not_a_continuous_anhui_clique_garrison'
            city['historical_control_sources']=['nccu_anhui_government_posts','huaian_anhui_duli_1923']
        if city['id']=='qingdao':
            city['protected_before']='1922-12-10';city['authority_label']='日军占领'
            city['historical_control_sources']=['qingdao_museum_1922_handover']
    edges=[]; nodes=[]; crossings=[]; railset=set()
    def route(a,b):
        queue=[(0,0,a)]; costs={a:0}; prev={}
        while queue:
            _,cost,p=heapq.heappop(queue)
            if cost!=costs[p]:continue
            if p==b:
                path=[b]
                while path[-1]!=a:path.append(prev[path[-1]])
                return path[::-1]
            for d in DIRECTIONS:
                n=(p[0]+d[0],p[1]+d[1]);cell=grid.get(n)
                if not cell or cell['region_id']=='restricted' or cell['terrain_id']=='sea':continue
                if any(c['id']=='jiumenkou' and (c['position']['q'],c['position']['r'])==n for c in cities):continue
                step=1+{'hill':1,'mountain':3,'river':3}.get(cell['terrain_id'],0)
                total=cost+step
                if total<costs.get(n,10**9):costs[n]=total;prev[n]=p;heapq.heappush(queue,(total+distance(n,b),total,n))
        return []
    for rid,name,active,stops in RAILS:
        for ca,cb in zip(stops,stops[1:]):
            if ca not in cityindex or cb not in cityindex:continue
            a=cityindex[ca]['position'];b=cityindex[cb]['position'];path=route((a['q'],a['r']),(b['q'],b['r']))
            if (ca,cb)==('shanhaiguan','jinzhou'):
                # The real coastal corridor passes Zhonghousuo/Suizhong and Ningyuan/Xingcheng,
                # not the Jiumenkou Great Wall mountain pass. Guides are strategic samples.
                guides=[]
                for lon,lat in [(119.90,40.05),(120.33,40.33),(120.73,40.62)]:
                    x,y=forward.transform(lon,lat);guide=projected_hex(x,y)
                    if guide in grid and grid[guide]['terrain_id']!='sea':guides.append(guide)
                stops_hex=[(a['q'],a['r'])]+guides+[(b['q'],b['r'])];guided=[]
                for start,end in zip(stops_hex,stops_hex[1:]):
                    leg=route(start,end)
                    if not leg:guided=[];break
                    guided+=leg if not guided else leg[1:]
                if guided:path=guided
            if not path:continue
            bridges=any(grid[p]['terrain_id']=='river' for p in path)
            eid=f'{rid}_{ca}_{cb}'
            edges.append({'id':eid,'name':name,'node_a':ca,'node_b':cb,'path_hexes':[pos(p) for p in path],'active_from':active,'damage':'intact','is_bridge':bridges,'capacity_max':2 if bridges else 3,'capacity_left':2 if bridges else 3,'source_ids':['rail_network_dates'],'alignment_status':'authored_hex_abstraction_between_real_stations'})
            if rid=='jiaoji':
                edges[-1]['military_access_from']='1923-05-02'
                edges[-1]['military_access_note']='1914年日军占领；1923年1月路产接收，5月2日全路中方路警接管完成。此前本游戏不开放军运。'
                edges[-1]['source_ids'].append('qingdao_gazetteer_jiaoji_handover')
            for p in path:
                railset.add(p)
                if grid[p]['terrain_id']=='river':
                    grid[p]['water_under_bridge']=True
                    grid[p]['terrain_id']='ford'
                elif grid[p]['terrain_id'] not in ['city','port']:grid[p]['terrain_id']='road'
            for a,b in zip(path,path[1:]):
                if grid[a]['terrain_id']=='ford' or grid[b]['terrain_id']=='ford':crossings.append({'id':f'bridge_{eid}_{a[0]}_{a[1]}','from':pos(a),'to':pos(b),'cost':1,'intact':True,'kind':'bridge','rail_allowed':True,'rail_edge_id':eid})
            for cid in [ca,cb]:
                if not any(n['id']==cid for n in nodes):nodes.append({'id':cid,'city_id':cid,'position':cityindex[cid]['position'],'kind':'station'})
    # Pedestrian river crossings are separate from historical rails. No imaginary 1920 Wuhan/Nanjing railway bridge.
    for a,b in [('pukou','nanjing'),('hankou','wuchang'),('hanyang','wuchang')]:
        if a in cityindex and b in cityindex:crossings.append({'id':f'ferry_{a}_{b}','from':cityindex[a]['position'],'to':cityindex[b]['position'],'cost':3,'intact':True,'kind':'ferry','rail_allowed':False})
    def lines(geo):
        if geo.is_empty:return []
        if geo.geom_type=='LineString':return [geo]
        if geo.geom_type in ['MultiLineString','GeometryCollection']:return [x for g in geo.geoms for x in lines(g)]
        return lines(geo.boundary)
    def renderline(line):
        coords=list(line.simplify(radius*.045).coords)
        return [[round((x-origin_x)/radius*48,2),round((origin_y-y)/radius*48,2)] for x,y in coords]
    def polygons(geo):
        if geo.is_empty:return []
        if geo.geom_type=='Polygon':return [geo]
        if geo.geom_type in ['MultiPolygon','GeometryCollection']:return [p for g in geo.geoms for p in polygons(g)]
        return []
    visual_land=transform(forward.transform,land.intersection(box(*bounds)))
    admin_layers={}
    for year,areas in ADMIN_LAYERS.items():
        layer=[]
        for area in areas:
            clipped=area['geometry'].intersection(box(*bounds))
            if clipped.is_empty or clipped.area<.0001:continue
            g=transform(forward.transform,clipped);point=g.representative_point()
            original_boundary=transform(forward.transform,area['geometry'].boundary.intersection(box(*bounds)))
            layer.append({'name':area['name'],'source_period':area['period'],'lines':[renderline(l) for l in lines(original_boundary)],'label_position':[round((point.x-origin_x)/radius*48,2),round((origin_y-point.y)/radius*48,2)]})
        admin_layers[year]=layer
        for city in cities:
            point=Point(city['lon_e6']/1e6,city['lat_e6']/1e6)
            city.setdefault('administration_by_year',{})[year]=next((a['name'] for a in areas if a['geometry'].covers(point)),'未核实')
            if city['id'] in ['beijing','nanyuan','changxindian','zhuozhou','langfang','guan','yangcun']:city['administration_by_year'][year]='京兆地方'
            if city['id']=='qingdao':city['administration_by_year'][year]='胶澳（日军占领）' if year<'1924' else '胶澳商埠'
    labels={'jingjin':[('燕山',116.5,40.18,'land'),('华北平原',115.5,38.98,'land'),('渤海',118.1,38.63,'water')],'jingfeng':[('燕山',118.60,40.65,'land'),('渤海',120.25,39.35,'water')],'conquest_china':[('太行山',113.5,37.4,'land'),('秦岭',108.6,33.8,'land'),('黄海',123.1,35.5,'water'),('东海',123.8,29.4,'water')],'hankou':[],'ningpu':[]}[map_id]
    render_labels=[]
    for name,lon,lat,kind in labels:
        x,y=forward.transform(lon,lat);render_labels.append({'name':name,'kind':kind,'position':[round((x-origin_x)/radius*48,2),round((origin_y-y)/radius*48,2)]})
    coast=transform(forward.transform,land.boundary.intersection(box(*bounds)))
    result={'id':map_id,'name':{'jingjin':'京津战区','jingfeng':'京奉战区','conquest_china':'中国东部征服战区','hankou':'汉口江段','ningpu':'南京—浦口'}[map_id],
      'projection':crs.to_proj4(),'geographic_bounds':bounds,'hex_radius_m':radius,'hex_radius_px':48,
      'cells':cells,'cities':cities,'rail_nodes':nodes,'rail_edges':edges,'crossings':crossings,
      'render_extent':renderline(projected.exterior),
      'render_coast':[renderline(x) for x in lines(coast)],'render_rivers':[renderline(x) for x in lines(rivers.intersection(projected))],
      'render_land':[{'exterior':renderline(p.exterior),'holes':[renderline(r) for r in p.interiors]} for p in polygons(visual_land)],'admin_layers':admin_layers,'render_labels':render_labels,
      'geography_status':'real_natural_earth_geometry_with_declared_strategic_hex_abstraction',
      'sources':['natural_earth_land_50m','natural_earth_rivers_10m','SRTM90m_v3','ENP_China_republican_provinces_CC0','rail_network_dates'],
      'administration_notes':['省界来自ENP-China民国时段研究图层；按官方沿革将河北还原为直隶、1928年前宁夏和青海合回甘肃。','京兆地方按已核实县籍标注节点；原研究图层没有京兆独立边界，故不编造该界线。','行政区划不等同于剧本军事控制；格子归属仍是游戏状态。'],
      'terrain_classification':{'method':elevation_source+' center and four cardinal half-radius samples; relief required for hill and mountain classification, elevation alone never implies hills','invented_forest_blocks':False,'samples_cached':bool(ELEVATION if elevation_samples is None else elevation_samples),'historical_vegetation_claimed':False},
      'notices':['江汉三镇和宁浦两岸保留独立节点；渡口不计入铁路。','粤汉线路仅开放当时南北分段，不连接1936年才贯通的缺口。','征服地图为东部中国战区，不宣称包括全国全部领土。']}
    assert len(cells)<=max_cells,(map_id,len(cells))
    assert len(taken)==len(cities)
    for edge in edges:
        assert all(distance((a['q'],a['r']),(b['q'],b['r']))==1 for a,b in zip(edge['path_hexes'],edge['path_hexes'][1:]))
    output(output_path or PROJECT/'content/maps'/f'{map_id}.json',result)
    return {'id':map_id,'cells':len(cells),'cities':len(cities),'rail_segments':len(edges),'bounds':bounds,'hex_radius_m':radius}

if __name__=='__main__':
    # This archived bootstrap predates the Asia board, reviewed coast vectors
    # and local 250 m grids. Imports remain reusable, but running it against
    # the current project would silently replace them with the five old maps.
    catalog_path=PROJECT/'content/maps/catalog.json'
    existing=json.loads(catalog_path.read_text(encoding='utf-8')).get('maps',[]) if catalog_path.exists() else []
    refined=any((PROJECT/'content/maps'/f'{mid}.json').exists() and
        json.loads((PROJECT/'content/maps'/f'{mid}.json').read_text(encoding='utf-8')).get('hex_radius_m')==250
        for mid in ['hankou','ningpu'])
    if 'asia_strategic' in existing or refined:
        raise SystemExit('Archived five-map bootstrap refused: it would overwrite reviewed geography. Use the source-specific rebuild instructions in docs/52_局部战区五倍比例与独立江岸.md; imports of compile_map remain supported.')
    import enlarge_maps
    enlarge_maps.compile_final()
    specs=[('hankou',(114.10,30.40,114.46,30.76),1250),('ningpu',(118.58,31.90,118.98,32.26),1250)]
    reports=json.loads((PROJECT/'reports/map_scale_v023.json').read_text(encoding='utf-8'))['maps']+[compile_map(*s) for s in specs]
    output(PROJECT/'content/maps/catalog.json',{'maps':['jingjin','jingfeng','conquest_china','hankou','ningpu']})
    output(PROJECT/'reports/map_compilation.json',{'source':'Natural Earth public-domain shapefiles','maps':reports,'compiler_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    import compile_atlas_detail
    compile_atlas_detail.main()
    print(json.dumps(reports,ensure_ascii=False))
