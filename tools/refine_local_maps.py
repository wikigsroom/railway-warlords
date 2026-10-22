"""Refine the two remaining local boards in their original geographical frame.

Native Python only. Candidates and raw elevation responses stay outside the
runtime until independently reviewed. No art raster is generated or modified.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
from collections import deque
import hashlib
import json
import math
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import shutil
import zipfile

P = Path(__file__).resolve().parents[1]
ROOT = P.parents[1]
WORK = ROOT / 'output/local-map-refinement-v0234'
API = 'https://api.opentopodata.org/v1/srtm90m'
MAPS = ['hankou', 'ningpu']
RADIUS = 250
DIRECTIONS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + '.pending')
    pending.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n', encoding='utf-8')
    pending.replace(path)


def keys(cell):
    lat, lon = cell['lat_e6'] / 1e6, cell['lon_e6'] / 1e6
    delta = RADIUS * .5 / 111320
    dx = delta / math.cos(math.radians(lat))
    return [f'{y:.6f},{x:.6f}' for y, x in
            [(lat, lon), (lat + delta, lon), (lat - delta, lon), (lat, lon + dx), (lat, lon - dx)]]


def source_identity():
    return {mid: sha(P / 'content/maps' / (mid + '.json')) for mid in MAPS}


def prepare():
    import compile_maps as compiler
    initial = source_identity()
    assert all(read(P / 'content/maps' / (mid + '.json'))['hex_radius_m'] == 1250 for mid in MAPS), 'This migration starts from the archived 0.2.33 local maps, not from an already refined map.'
    baseline = WORK / 'baseline.json'
    if baseline.exists():
        assert read(baseline)['source_hashes'] == initial, 'Source changed after candidate preparation.'
    else:
        write(baseline, dict(source_hashes=initial, base_version='0.2.33', source_files={
            mid: read(P / 'content/maps' / (mid + '.json')) for mid in MAPS}))
    counts = {}
    requested = set()
    for mid in MAPS:
        path = WORK / 'pre_elevation' / (mid + '.json')
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            old = read(baseline)['source_files'][mid]
            compiler.compile_map(mid, old['geographic_bounds'], RADIUS, output_path=path,
                                 max_cells=20000, land_source='ne_10m_land', elevation_samples={})
        draft = read(path)
        counts[mid] = len(draft['cells'])
        requested.update(key for cell in draft['cells'] if cell['natural_terrain_id'] != 'sea' for key in keys(cell))
    assert source_identity() == initial
    write(WORK / 'request.json', dict(api=API, dataset='SRTM v3 90m', interpolation='bilinear',
        points=sorted(requested), source_hashes=initial, candidates=counts, radius_m=RADIUS,
        documentation=['https://www.opentopodata.org/datasets/srtm/', 'https://www.opentopodata.org/api/'],
        physical_reference_epoch='SRTM February 2000; not a period land-use or shoreline survey'))
    print('LOCAL_REFINEMENT_PREPARED ' + json.dumps(dict(cells=counts, elevation_points=len(requested))), flush=True)


def validate_response(data, batch):
    assert data.get('status') == 'OK' and len(data.get('results', [])) == len(batch)
    for key, row in zip(batch, data['results']):
        lat, lon = map(float, key.split(','))
        assert row['dataset'] == 'srtm90m'
        assert abs(row['location']['lat'] - lat) < 1e-7 and abs(row['location']['lng'] - lon) < 1e-7
        value = row['elevation']
        assert value is None or isinstance(value, (float, int)) and math.isfinite(value)


def major_channels():
    """Use the same source reaches as the existing local river presentation."""
    import shapefile
    from shapely.geometry import box, shape
    folder = ROOT / 'design/geodata/surface_detail_sources/HydroRIVERS_v10_as_shp'
    source = next(folder.rglob('*as.shp'))
    baseline = read(WORK / 'baseline.json')
    regions = {mid: box(*baseline['source_files'][mid]['geographic_bounds']) for mid in MAPS}
    result = {mid: [] for mid in MAPS}
    identities = {mid: [] for mid in MAPS}
    reader = shapefile.Reader(str(source), encoding='utf-8')
    for item in reader.iterShapeRecords(bbox=(114.1, 30.4, 118.98, 32.26)):
        record = item.record.as_dict()
        if int(record['ORD_STRA']) < 6:
            continue
        for mid, region in regions.items():
            if not box(*item.shape.bbox).intersects(region):
                continue
            geo = shape(item.shape.__geo_interface__).intersection(region)
            if geo.is_empty:
                continue
            result[mid].append(geo)
            identities[mid].append(int(record['HYRIV_ID']))
    write(WORK / 'river_source.json', dict(source_id='hydrorivers_v10_as', source_sha256=sha(source),
        source_url='https://www.hydrosheds.org/products/hydrorivers', reach_ids=identities,
        source_file=source.relative_to(ROOT).as_posix(), stream_order_min=6,
        historical_banks_or_widths_claimed=False, new_river_connections_invented=False))
    assert all(result.values()), 'Actual major source reaches required in both local maps.'
    return result


def attach_harbors(data):
    """Keep city centres in place; derive separate shore approaches on their bank.

    These are tactical grid abstractions, not asserted historical wharf surveys.
    Never add a city, waterway, road, bridge or fictional historical settlement.
    """
    grid = {(c['position']['q'], c['position']['r']): c for c in data['cells']}
    water = {'river', 'sea', 'port'}
    for city in data['cities']:
        if not city['port']:
            continue
        start = (city['position']['q'], city['position']['r'])
        visited, queue, shores = {start}, deque([start]), []
        while queue:
            q, r = queue.popleft()
            adjacent_water = []
            for dq, dr in DIRECTIONS:
                key = q + dq, r + dr
                cell = grid.get(key)
                if not cell or cell['region_id'] == 'restricted':
                    continue
                if cell['terrain_id'] in water:
                    adjacent_water.append(key)
                elif key not in visited:
                    visited.add(key)
                    queue.append(key)
            if adjacent_water:
                shores.append(((q, r), adjacent_water))
        assert shores, 'No reachable real river shore for ' + city['id']
        def distance(key):
            x, y = 72 * key[0], math.sqrt(3) * 48 * (key[1] + key[0] * .5)
            return (x - city['render_position'][0]) ** 2 + (y - city['render_position'][1]) ** 2
        shore, waters = min(shores, key=lambda row: (distance(row[0]), row[0]))
        wet = min(waters, key=lambda key: (distance(key), key))
        city['harbor_position'] = dict(q=shore[0], r=shore[1])
        city['harbor_water_position'] = dict(q=wet[0], r=wet[1])
        city['harbor_position_status'] = 'source_channel_adjacent_tactical_approach_not_surveyed_historical_wharf'
        city['harbor_source_id'] = 'hydrorivers_v10_as'
    cities = {c['id']: c for c in data['cities']}
    pairs = [('hankou', 'wuchang'), ('hanyang', 'wuchang')] if data['id'] == 'hankou' else [('pukou', 'nanjing')]
    for crossing, (a, b) in zip(data['crossings'], pairs):
        assert crossing['id'] == f'ferry_{a}_{b}' and crossing['kind'] == 'ferry' and not crossing['rail_allowed']
        crossing.update({'from': cities[a]['harbor_position'], 'to': cities[b]['harbor_position'],
            'from_city_id': a, 'to_city_id': b,
            'endpoint_status': 'derived_same_bank_shore_approach_not_surveyed_historical_wharf'})


def fetch():
    request = read(WORK / 'request.json')
    assert source_identity() == request['source_hashes']
    points = request['points']
    records = []
    values = {}
    total = math.ceil(len(points) / 100)
    for offset in range(0, len(points), 100):
        batch = points[offset:offset + 100]
        identifier = hashlib.sha256('|'.join(batch).encode()).hexdigest()[:24]
        path = WORK / 'responses' / (identifier + '.json')
        path.parent.mkdir(parents=True, exist_ok=True)
        url = API + '?' + urllib.parse.urlencode(dict(locations='|'.join(batch), interpolation='bilinear'))
        if path.exists():
            data = read(path)
            validate_response(data, batch)
        else:
            for attempt in range(4):
                started = time.monotonic()
                try:
                    with urllib.request.urlopen(url, timeout=40) as response:
                        raw = response.read()
                    data = json.loads(raw)
                    validate_response(data, batch)
                    assert not path.exists()
                    path.write_bytes(raw)
                    write(path.with_suffix('.source.json'), dict(url=url, retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
                        sha256=sha(path), bytes=len(raw), batch_points=len(batch)))
                    break
                except Exception as error:
                    write(WORK / 'last_fetch_error.json', dict(batch=offset // 100, attempt=attempt,
                        type=type(error).__name__, message=str(error), original_source_hashes_preserved=source_identity() == request['source_hashes']))
                    if isinstance(error, urllib.error.HTTPError) and error.code == 429:
                        raise SystemExit('Provider quota reached. Resume the same saved batch later; do not create duplicate jobs.')
                    if attempt == 3:
                        raise
                    time.sleep(3 * (attempt + 1))
                finally:
                    time.sleep(max(0., 1.1 - (time.monotonic() - started)))
        for key, row in zip(batch, data['results']):
            values[key] = row['elevation']
        records.append(dict(file=path.relative_to(ROOT).as_posix(), sha256=sha(path), points=len(batch)))
        if len(records) % 10 == 0 or len(records) == total:
            write(WORK / 'fetch_progress.json', dict(completed_batches=len(records), total_batches=total, points=len(values)))
            print(f'LOCAL_SRTM_FETCH {len(records)}/{total}; points={len(values)}', flush=True)
    assert source_identity() == request['source_hashes'] and len(values) == len(points)
    write(WORK / 'samples.json', dict(dataset='SRTM v3 90m', api=API, interpolation='bilinear',
        source_responses=records, samples=values, source_hashes=request['source_hashes'],
        null_samples=sum(x is None for x in values.values()), negative_samples=sum(x is not None and x < 0 for x in values.values())))
    print('LOCAL_SRTM_SAMPLES_SAVED', flush=True)


def compile_candidates():
    import compile_maps as compiler
    baseline = read(WORK / 'baseline.json')
    sampled = read(WORK / 'samples.json')
    assert source_identity() == baseline['source_hashes'] == sampled['source_hashes']
    values = sampled['samples']
    assert sampled['null_samples'] == 0, 'Missing physical samples require review.'
    if sampled['negative_samples']:
        review = read(WORK / 'negative_sample_review.json')
        low = {key for key, value in values.items() if value is not None and value < 0}
        assert {row['point'] for row in review['rows'] if row['srtm90m'] < 0} == low
        assert review.get('policy') == 'retain_original_values_flag_uncertainty_exclude_low_support_from_relief_rendering'
        assert all(row['srtm30m'] is not None for row in review['rows'])
    rivers = major_channels()
    rows = []
    for mid in MAPS:
        old = baseline['source_files'][mid]
        path = WORK / 'candidates' / (mid + '.json')
        path.parent.mkdir(parents=True, exist_ok=True)
        compiler.compile_map(mid, old['geographic_bounds'], RADIUS, output_path=path, max_cells=20000,
            land_source='ne_10m_land', elevation_samples=values, elevation_source='SRTM90m_v3',
            primary_river_geometries=rivers[mid], port_snap_max_m=RADIUS * 2)
        new = read(path)
        # Preserve the already reviewed vector frame; refine the operation grid
        # in the same projection rather than replacing it with a new coastline.
        scale = old['hex_radius_m'] / RADIUS
        def points(line):
            return [[round(float(v) * scale, 2) for v in p] for p in line]
        for key in ['render_extent']:
            new[key] = points(old[key])
        for key in ['render_land']:
            new[key] = [dict(exterior=points(p['exterior']), holes=[points(h) for h in p['holes']]) for p in old[key]]
        new['render_coast'] = [points(p) for p in old['render_coast']]
        new['physical_detail_source'] = old.get('physical_detail_source', '')
        new.update(scale_revision='local_geographic_linear_5x_v0234', scale_baseline_version='0.2.33',
            geographic_linear_scale=scale, physical_grid_source='natural_earth_land_10m_v5_1_1')
        west, south, east, north = old['geographic_bounds']
        for cell in new['cells']:
            lon, lat = cell['lon_e6'] / 1e6, cell['lat_e6'] / 1e6
            inside = west <= lon <= east and south <= lat <= north
            cell['render_land_covered'] = inside and cell['natural_terrain_id'] != 'sea'
            if not inside:
                cell['region_id'] = 'restricted'
            if cell['terrain_id'] == 'river':
                cell['natural_terrain_id'] = 'river'
            if any(values.get(key) is not None and values[key] < 0 for key in keys(cell)):
                cell['elevation_quality'] = 'negative_sample_in_support_unverified_ground_height'
        new['terrain_classification']['low_sample_policy'] = 'Original source values retained; affected support excluded from relief shading and contours, not asserted as real below-sea-level terrain.'
        new['terrain_classification']['elevation_accuracy_notice'] = 'Radar DEM physical reference, not ground survey or historical land-use reconstruction. SRTM mission absolute vertical accuracy specification: 16 m at 90% confidence; this is not a per-cell guarantee.'
        new['sources'] = [s if s != 'natural_earth_land_50m' else 'natural_earth_land_10m_v5_1_1' for s in old['sources']]
        new['sources'].append('hydrorivers_v10_as')
        new['primary_river_source'] = 'hydrorivers_v10_as_order_6_and_above'
        new['river_rule_geometry'] = 'continuous_hex_sampling_of_same_source_reaches_as_presentation; symbolic_water_width_not_surveyed_banks'
        attach_harbors(new)
        for city in new['cities']:
            previous = next(c for c in old['cities'] if c['id'] == city['id'])
            assert all(city[k] == previous[k] for k in ['id', 'name', 'lon_e6', 'lat_e6', 'administration_by_year'])
            assert max(abs(city['render_position'][i] - previous['render_position'][i] * scale) for i in [0, 1]) <= .04
            assert city['strategic_hex_displacement_m'] <= RADIUS * 2
        write(path, new)
        rows.append(dict(map_id=mid, old_cells=len(old['cells']), new_cells=len(new['cells']),
            old_radius_m=old['hex_radius_m'], new_radius_m=RADIUS, scale=scale,
            candidate_sha256=sha(path), real_bounds_unchanged=new['geographic_bounds'] == old['geographic_bounds'],
            terrain_counts={key: sum(c['natural_terrain_id'] == key for c in new['cells']) for key in ['plain', 'hill', 'mountain', 'peak', 'river', 'sea']},
            negative_centres=sum(c['elevation_m'] is not None and c['elevation_m'] < 0 for c in new['cells']),
            null_centres=sum(c['elevation_m'] is None for c in new['cells'])))
        rows[-1]['cities'] = [dict(id=c['id'], city_displacement_m=c['strategic_hex_displacement_m'],
            harbor_position=c['harbor_position'], harbor_water_position=c['harbor_water_position']) for c in new['cities']]
        print('LOCAL_CANDIDATE_COMPILED ' + json.dumps(rows[-1]), flush=True)
    write(WORK / 'candidate_validation.json', dict(passed=True, runtime_installed=False,
        source_hashes=baseline['source_hashes'], samples_sha256=sha(WORK / 'samples.json'), maps=rows,
        original_sources_modified=False, artwork_modified=False, historical_landuse_claimed=False,
        native_render_reviewed=False, gameplay_balance_reviewed=False))


def install():
    """Install the audited candidate reversibly; this is not release approval."""
    baseline = read(WORK / 'baseline.json')
    assert source_identity() == baseline['source_hashes'], 'The original source maps must still match the saved baseline.'
    audit = read(P / 'reports/local_map_refinement/geography_preinstall.json')
    assert audit['passed'] and {row['map_id'] for row in audit['maps']} == set(MAPS)
    for row in audit['maps']:
        assert row['sha256'] == sha(WORK / 'candidates' / (row['map_id'] + '.json'))
    backup = WORK / 'prior_runtime_maps'
    backup.mkdir(exist_ok=True)
    for mid in MAPS:
        original = P / 'content/maps' / (mid + '.json')
        target = backup / original.name
        if not target.exists():
            shutil.copyfile(original, target)
        assert sha(target) == baseline['source_hashes'][mid]
    catalogs = WORK / 'prior_catalogues'
    catalogs.mkdir(exist_ok=True)
    for source in (P / 'presentation/data').glob('*.json'):
        target = catalogs / source.name
        if not target.exists():
            shutil.copyfile(source, target)
    for source in ['content/geography_sources.json', 'reports/settlement_compilation.json']:
        target = WORK / ('prior_' + Path(source).name)
        if not target.exists():
            shutil.copyfile(P / source, target)
    # Portable original-response archive, with every provider byte retained.
    archive = WORK / 'srtm_original_responses.zip'
    if not archive.exists():
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as output:
            for source in sorted((WORK / 'responses').glob('*.json')):
                output.write(source, 'responses/' + source.name)
            for filename in ['request.json', 'samples.json', 'negative_sample_review.json',
                             'srtm30m_negative_crosscheck.json', 'srtm30m_negative_crosscheck.source.json']:
                output.write(WORK / filename, filename)
    with zipfile.ZipFile(archive) as source:
        assert source.testzip() is None
        for row in read(WORK / 'samples.json')['source_responses']:
            filename = 'responses/' + Path(row['file']).name
            assert hashlib.sha256(source.read(filename)).hexdigest() == row['sha256']
    registry = read(P / 'content/geography_sources.json')
    river = read(WORK / 'river_source.json')
    assert not any(row['id'] == river['source_id'] for row in registry['sources'])
    registry['sources'].append(dict(id=river['source_id'], title='HydroRIVERS v1.0 Asia',
        url=river['source_url'], license='HydroSHEDS License Agreement',
        use='汉口、宁浦主河道物理中心线与战术水格；现代 DEM 衍生参考，不宣称为1924年河岸、河宽或码头测绘。',
        access_date='2026-10-22', files=[river['source_file']],
        file_hashes={river['source_file']:river['source_sha256']}))
    srtm = next(row for row in registry['sources'] if row['id'] == 'SRTM90m_v3')
    srtm['additional_sample_sets'] = [dict(file=(WORK / 'samples.json').relative_to(ROOT).as_posix(),
        sha256=sha(WORK / 'samples.json'), points=92120, local_hex_radius_m=250,
        original_response_archive=archive.relative_to(ROOT).as_posix(), archive_sha256=sha(archive),
        raw_negative_values_retained=True, low_support_cells_excluded_from_relief_inference=True)]
    for mid in MAPS:
        shutil.copyfile(WORK / 'candidates' / (mid + '.json'), P / 'content/maps' / (mid + '.json'))
    write(P / 'content/geography_sources.json', registry)
    write(P / 'reports/local_map_refinement/installation.json', dict(
        status='installed_pending_presentation_rebuild_and_native_qa', source_hashes=baseline['source_hashes'],
        installed_map_hashes=source_identity(), raw_archive_sha256=sha(archive),
        new_rasters=0, source_rasters_modified=False, release_verified=False, physical_android_device_tested=False))
    print('LOCAL_MAPS_INSTALLED_PENDING_NATIVE_QA', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('step', choices=['prepare', 'fetch', 'compile', 'install'])
    args = parser.parse_args()
    {'prepare': prepare, 'fetch': fetch, 'compile': compile_candidates, 'install': install}[args.step]()
