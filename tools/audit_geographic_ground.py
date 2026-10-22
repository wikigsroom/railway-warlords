"""Re-read original GIS polygons; audit every numeric ecological reference.

This deliberately does not use the compiler's WKB cache. Original scientific
data and immutable art remain untouched. Probes are runtime test inputs.
"""
from pathlib import Path
import base64
import gzip
import hashlib
import json
import time

from compile_terrain_surfaces import P, SOURCE, load_regions, family_for
import numpy as np
import shapely


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    started = time.monotonic()
    out = P / 'reports/geographic_ground_v0237'
    report = out / 'source_audit01.json'
    assert not report.exists()
    source = P / 'presentation/data/asia_ground_regions.json'
    data = json.loads(source.read_bytes())
    for suffix, expected in data['source_files_sha256'].items():
        assert sha(SOURCE.with_suffix(suffix)) == expected
    material = np.frombuffer(gzip.decompress(base64.b64decode(data['data_base64'])), dtype='u1').reshape(901,1601)
    eco = np.frombuffer(gzip.decompress(base64.b64decode(data['ecological_data_base64'])), dtype='>u2').reshape(901,1601)
    assert hashlib.sha256(material.tobytes()).hexdigest() == data['payload_sha256']
    assert hashlib.sha256(eco.tobytes()).hexdigest() == data['ecological_payload_sha256']
    print('Reading original shapefile polygons (compiler geometry cache not used)', flush=True)
    rows, tree = load_regions()
    source_ids = np.array([r['id'] for r in rows], dtype=np.uint16)
    wrong_eco = wrong_family = ties = 0
    for first in range(0,901,32):
        last = min(first+32,901)
        xs, ys = np.meshgrid(20+np.arange(1601)*.1,80-np.arange(first,last)*.1)
        points = shapely.points(xs.ravel(),ys.ravel())
        pairs = tree.query(points,predicate='covered_by')
        expected = np.full(points.size,65535,dtype=np.uint16)
        np.minimum.at(expected,pairs[0],source_ids[pairs[1]])
        ties += int(len(pairs[0])-len(np.unique(pairs[0])))
        wrong_eco += int(np.count_nonzero(expected != eco[first:last].ravel()))
        # Distinct raw polygon IDs plus real lat/lon gates validate pigments;
        # the historical-cover withholding policy is tested explicitly below.
        expected_material = np.zeros(points.size,dtype=np.uint8)
        for index in np.unique(pairs[1]):
            region = rows[int(index)]
            chosen = np.flatnonzero(expected == region['id'])
            for below in [False,True]:
                for eastern in [False,True]:
                    selected = chosen[((ys.ravel()[chosen]<32)==below) & ((xs.ravel()[chosen]>70)==eastern)]
                    if not len(selected):continue
                    cell=dict(terrain_id='plain',lat_e6=31000000 if below else 33000000,lon_e6=100000000 if eastern else 60000000)
                    family,_ = family_for(region,cell,float('inf'))
                    family={'temperate_litter':'temperate_meadow','conifer_litter':'temperate_meadow',
                            'boreal_litter':'temperate_meadow','dry_woodland_litter':'dry_steppe'}.get(family,family)
                    if family:expected_material[selected]=data['family_names'].index(family)+1
        wrong_family += int(np.count_nonzero(expected_material != material[first:last].ravel()))
        print(json.dumps(dict(rows=last,incorrect_ecological_ids=wrong_eco,incorrect_families=wrong_family)),flush=True)
    assert wrong_eco == wrong_family == 0
    assert np.all(material[eco==65535]==0)
    forbidden=[data['family_names'].index(f)+1 for f in ['temperate_litter','conifer_litter','boreal_litter','dry_woodland_litter']]
    assert not np.isin(material,forbidden).any()
    samples=[]
    for y in range(0,901,13):
        for x in range(0,1601,17):
            samples.append(dict(node=[x,y],family_index_plus_one=int(material[y,x]),ecoregion_id=int(eco[y,x])))
    probes = out / 'source_probes01.json'
    probes.write_text(json.dumps(dict(data_sha256=sha(source),scope='All-node raw polygon audit subsample for native decoding',probes=samples),separators=(',',':'))+'\n',encoding='utf-8')
    result=dict(passed=True,created_at_utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        controller_sha256=sha(Path(__file__)),source_data_sha256=sha(source),source_files_sha256=data['source_files_sha256'],
        nodes_audited=int(material.size),wrong_ecological_ids=wrong_eco,wrong_material_families=wrong_family,
        boundary_ties=ties,compiler_wkb_cache_used=False,raw_source_polygon_reader_used=True,
        classifier_function_shared_with_existing_registry=True,native_probes=len(samples),probes_sha256=sha(probes),
        historical_forest_floor_withheld=True,no_unreferenced_polygon_gap_fill=True,
        historical_landuse_survey=False,art_approval=False,elapsed_seconds=round(time.monotonic()-started,2))
    report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
