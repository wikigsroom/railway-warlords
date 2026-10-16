"""Capture the actual expanded-map EXE and its runtime source selections."""
import json
import math
import subprocess
from datetime import datetime, timezone
from build_release import P, current_version, source_digest
from package_delivery import sha
from map_bank_inventory import ADDITIONAL_COUNT, MAP_COUNT


def source_material_point(map_id, family, lon, lat, region=None):
    data=json.loads((P/'content/maps'/f'{map_id}.json').read_text(encoding='utf-8'))
    rows=json.loads((P/'presentation/data/surface_regions.json').read_text(encoding='utf-8'))['maps'][map_id]
    candidates=[cell for cell in data['cells'] if rows.get(cell['id'],[''])[0]==family
                and (region is None or int(rows[cell['id']][1])==region)]
    if not candidates:raise RuntimeError('No actual material reference cell: '+map_id+'/'+family)
    cell=min(candidates,key=lambda cell:(cell['lon_e6']/1e6-lon)**2+(cell['lat_e6']/1e6-lat)**2)
    q,r=cell['position']['q'],cell['position']['r']
    return f'{q*72:.3f},{math.sqrt(3)*48*(r+q*.5):.3f}'


def tributary_point(map_id):
    hydro=json.loads((P/'presentation/data/hydrography_fine.json').read_text(encoding='utf-8'))
    rows=[row for row in hydro['maps'][map_id] if row['stream_order'] in [2,3,4]]
    if not rows:raise RuntimeError('Actual native tributary evidence requires source reaches')
    # Choose a long existing source reach; this is not a synthesized junction.
    row=max(rows,key=lambda row:sum(math.dist(a,b) for a,b in zip(row['points'],row['points'][1:])))
    point=row['points'][len(row['points'])//2]
    return f'{point[0]:.3f},{point[1]:.3f}'


def source_city_point(map_id, city_id):
    data=json.loads((P/'content/maps'/f'{map_id}.json').read_text(encoding='utf-8'))
    city=next(row for row in data['cities'] if row['id']==city_id)
    q,r=city['position']['q'],city['position']['r']
    return f'{q*72:.3f},{math.sqrt(3)*48*(r+q*.5):.3f}'


def main():
    runtime, modified = source_digest(); version = current_version()
    exe = P/'build/windows/RailwayWarlords.exe'
    exports = json.loads((P/'reports/export_results.json').read_text(encoding='utf-8'))
    win = next(row for row in exports if row['target']=='windows')
    if not win['export_verified'] or win['sha256']!=sha(exe) or win['runtime_source_sha256']!=runtime:
        raise SystemExit('Verified current native EXE is required')
    jobs = [
        ('mountain','燕山丘陵与多种村落','campaign_1924_03','1920x1080',['--focus-point','16848,7000','--capture-zoom','1.05']),
        ('coast','渤海海岸与山海关','campaign_1924_03','1920x1080',['--focus-city','shanhaiguan','--capture-zoom','.88']),
        ('river','天津河岸与交通节点','campaign_1924_05','1920x1080',['--focus-point',source_city_point('jingjin','tianjin'),'--capture-zoom','.85']),
        ('village','历史村落与平原','campaign_1924_03','1920x1080',['--focus-place','place_dongjiakou','--capture-zoom','1.15']),
        ('forest','来源林地的疏密树冠','asia_1927','1920x1080',['--focus-point','4896,1912','--capture-zoom','.72']),
        ('forest_x30','2400×1080 移动布局林地','asia_1927','2400x1080',['--focus-point','4896,1912','--capture-zoom','.72','--ui-scale','1.2','--mobile-ui-test']),
        ('sand','塔克拉玛干来源沙土材质','asia_1927','1920x1080',['--focus-point',source_material_point('asia_strategic','sandy_ground',83,39,843),'--capture-zoom','1.25']),
        ('gravel','戈壁荒漠来源砾土材质','asia_1927','1920x1080',['--focus-point',source_material_point('asia_strategic','arid_gravel',108,44,824),'--capture-zoom','1.25']),
        ('wet_soil','渤海盐生草甸区域湿土','campaign_1924_05','1920x1080',['--focus-point',source_material_point('jingjin','wetland_ground',117.55,39.27,742),'--capture-zoom','1.15']),
        ('tributaries','来源山谷支流与地表纹理','campaign_1924_03','1920x1080',['--focus-point',tributary_point('jingfeng'),'--capture-zoom','1.15']),
        ('yangtze','汉口长江主河与冲积土','legion_07','1920x1080',['--focus-city','hankou','--capture-zoom','1.05']),
    ]
    captures=[]
    for name, label, scenario, resolution, extra in jobs:
        path=P/'reports/screenshots/map_bank_native'/f'{name}.png'
        path.parent.mkdir(parents=True,exist_ok=True)
        log=P/'reports'/f'map_bank_native_{name}.log'
        args=[str(exe),'--resolution',resolution,'--position','-4000,-3000','--',
              '--qa-session','--scenario',scenario,*extra,'--capture','--capture-path',str(path)]
        with log.open('w',encoding='utf-8') as stream:
            result=subprocess.run(args,cwd=P,stdout=stream,stderr=subprocess.STDOUT,timeout=180)
        diagnostic=log.read_text(encoding='utf-8',errors='replace')
        if result.returncode or 'SCRIPT ERROR:' in diagnostic or '\nERROR:' in diagnostic:
            raise SystemExit('Native map capture failed: '+name)
        meta=json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
        visible=meta.get('map_bank_visible',{})
        if (meta['build_version']!=version or not meta['raw_godot_capture'] or
            not meta['qa_save_isolated'] or not visible.get('active') or
            visible.get('catalog_additional_sources')!=ADDITIONAL_COUNT or visible.get('catalog_map_assets')!=MAP_COUNT or
            min(path.stat().st_mtime,path.with_suffix('.json').stat().st_mtime)<modified):
            raise SystemExit('Current expanded-map capture evidence required: '+name)
        captures.append(dict(name=name,label=label,file=path.relative_to(P).as_posix(),sha256=sha(path),
            metadata_sha256=sha(path.with_suffix('.json')),log=log.relative_to(P).as_posix(),
            runtime_selection=visible,physical_android_device_tested=False))
        print(json.dumps(dict(name=name,passed=True,instances=visible['scenery_instances_intersecting_view'],
            distinct=visible['distinct_scenery_originals_intersecting_view'],
            nearby_same_source_pairs=visible['same_source_pairs_under_250_world_units'])),flush=True)
    mountain=captures[0]['runtime_selection']
    diversity=mountain['distinct_scenery_originals_intersecting_view']>=30 and mountain['same_source_pairs_under_250_world_units']==0
    by_name={row['name']:row['runtime_selection'] for row in captures}
    geographic_materials=all(by_name[name]['surface_material_families_in_view'].get(family,0)>0
        for name,family in [('sand','sandy_ground'),('gravel','arid_gravel'),('wet_soil','wetland_ground'),('yangtze','alluvial_soil')])
    fine_visible=by_name['tributaries']['hydrography']['visible_fine_reaches']>0
    report=dict(passed=diversity and geographic_materials and fine_visible,version=version,created_at_utc=datetime.now(timezone.utc).isoformat(),
        runtime_source_sha256=runtime,windows_exe_sha256=sha(exe),
        raw_native_viewport_captures=True,source_images_modified=False,manual_compositing=False,
        mountain_patch_uses_at_least_30_distinct_originals=diversity,captures=captures,
        source_bound_sand_gravel_wet_and_alluvial_materials_visible=geographic_materials,
        actual_fine_river_reaches_visible=fine_visible,
        physical_android_device_tested=False,formal_art_approval=False,ew6_visual_parity_claimed=False)
    (P/'reports/map_bank_native_evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if not report['passed']:
        raise SystemExit('Native diversity, geographic material or actual tributary evidence failed')


if __name__=='__main__':
    main()
