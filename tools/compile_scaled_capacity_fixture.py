"""Derive a QA workload from the largest complete production map, without changing geography."""
from pathlib import Path
import hashlib, json

P=Path(__file__).resolve().parents[1]
source=P/'content/maps/conquest_china.json'
fixture=P/'tests/fixtures/capacity_full_conquest.json'
digest=hashlib.sha256(source.read_bytes()).hexdigest()
data=json.loads(source.read_text(encoding='utf-8'))
usable=[c for c in data['cells'] if c['region_id']!='restricted']
if len(data['cells'])!=74762 or any(c['elevation_m'] is None for c in usable if c['natural_terrain_id']!='sea'):
    raise ValueError('The complete sampled fivefold production map is required.')
data.update(id='qa_capacity_conquest',name='东部中国容量测试图',qa_capacity_fixture=True,military_deployment_claimed=False)
data['fixture_source']={'production_map_id':'conquest_china','production_map_sha256':digest,
    'total_cells':len(data['cells']),'usable_cells':len(usable),'restriction_preserved':True,
    'geography_resampled_for_fixture':False,'historical_military_start':False}
fixture.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
report={'passed':hashlib.sha256(source.read_bytes()).hexdigest()==digest,
    'fixture':fixture.relative_to(P.parents[1]).as_posix(),
    'fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),**data['fixture_source'],
    'published_content_changed':False,'historical_military_start':False}
(P/'reports/capacity_geography.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
