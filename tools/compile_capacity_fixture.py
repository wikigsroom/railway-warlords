"""Compile an isolated, real-geography capacity fixture; never edit published maps."""
import hashlib
import itertools
import json
import math
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path
import compile_maps as compiler

P = Path(__file__).resolve().parents[1]
ROOT = P.parents[1]
FIXTURES = P / 'tests/fixtures'
MAP_PATH = FIXTURES / 'capacity_jingfeng.json'
SOURCE_PATH = ROOT / 'design/geodata/srtm90m/capacity_samples.json'
API = 'https://api.opentopodata.org/v1/srtm90m'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sample_keys(cell, radius):
    lat, lon = cell['lat_e6'] / 1e6, cell['lon_e6'] / 1e6
    delta = radius * .5 / 111320
    dx = delta / math.cos(math.radians(lat))
    return [f'{y:.6f},{x:.6f}' for y, x in
            [(lat, lon), (lat + delta, lon), (lat - delta, lon), (lat, lon + dx), (lat, lon - dx)]]


def main():
    FIXTURES.mkdir(parents=True, exist_ok=True)
    originals = {p: sha(p) for p in (P / 'content').rglob('*.json')}
    # This resolution retains the original Jingfeng geographic extent and has
    # more than 4096 usable cells, including actual coastal sea cells.
    bounds, radius = (115.7, 38.7, 122.0, 41.5), 4050
    compiler.compile_map('jingfeng', bounds, radius, output_path=MAP_PATH, max_cells=8192)
    draft = json.loads(MAP_PATH.read_text(encoding='utf-8'))
    keys = sorted({key for cell in draft['cells'] if cell['natural_terrain_id'] != 'sea'
                   for key in sample_keys(cell, radius)})
    cache = json.loads(SOURCE_PATH.read_text(encoding='utf-8')) if SOURCE_PATH.exists() else {
        'dataset': 'SRTM v3 90m', 'api': API,
        'source_url': 'https://www.opentopodata.org/datasets/srtm/',
        'interpolation': 'bilinear', 'samples': {}}
    combined = compiler.ELEVATION | cache['samples']
    def tile(key):
        lat,lon=map(float,key.split(','))
        return math.floor(lat),math.floor(lon)
    missing = sorted((key for key in keys if key not in combined), key=lambda key:(tile(key),key))
    print(f'CAPACITY_ELEVATION requested={len(keys)} missing={len(missing)}', flush=True)
    raw_dir = SOURCE_PATH.parent / 'capacity_responses'
    raw_dir.mkdir(parents=True, exist_ok=True)
    batches=[]
    for _,group in itertools.groupby(missing,key=tile):
        local=list(group)
        batches.extend(local[i:i+50] for i in range(0,len(local),50))
    offset=0
    for batch_index,batch in enumerate(batches):
        url = API + '?' + urllib.parse.urlencode({'locations': '|'.join(batch), 'interpolation': 'bilinear'})
        for attempt in range(4):
            started = time.monotonic()
            try:
                response = subprocess.run(['curl.exe', '--fail', '--silent', '--show-error', '--compressed',
                    '--connect-timeout', '10', '--max-time', '20', url],
                    capture_output=True, check=True, timeout=25)
                raw = response.stdout
                result = json.loads(raw)
                if result.get('status') != 'OK' or len(result.get('results', [])) != len(batch):
                    raise RuntimeError('Incomplete elevation API response')
                for key, row in zip(batch, result['results']):
                    lat, lon = map(float, key.split(','))
                    loc = row['location']
                    if abs(loc['lat'] - lat) > 1e-6 or abs(loc['lng'] - lon) > 1e-6:
                        raise RuntimeError('Elevation response location mismatch')
                    cache['samples'][key] = row['elevation']
                # Keep complete original responses, including nulls, for source review.
                request_id = hashlib.sha256('|'.join(batch).encode()).hexdigest()[:20]
                (raw_dir / f'{request_id}.json').write_bytes(raw)
                break
            except Exception as error:
                print(f'CAPACITY_ELEVATION retry={attempt + 1} offset={offset} error={type(error).__name__} code={getattr(error,"returncode",None)}', flush=True)
                if attempt == 3:
                    raise
                time.sleep(3 * (attempt + 1))
            finally:
                time.sleep(max(0, 1.1 - (time.monotonic() - started)))
        SOURCE_PATH.write_text(json.dumps(cache, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        offset+=len(batch)
        if batch_index%10==0 or offset>=len(missing):
            print(f'CAPACITY_ELEVATION {offset}/{len(missing)} tile={tile(batch[0])}', flush=True)
    compiler.ELEVATION |= cache['samples']
    if any(key not in compiler.ELEVATION for key in keys):
        raise RuntimeError('Missing source samples; do not invent terrain')
    compiler.compile_map('jingfeng', bounds, radius, output_path=MAP_PATH, max_cells=8192)
    fixture = json.loads(MAP_PATH.read_text(encoding='utf-8'))
    valid = [c for c in fixture['cells'] if c['region_id'] != 'restricted']
    unsampled = [c['id'] for c in valid if c['natural_terrain_id'] != 'sea' and c['elevation_m'] is None]
    if len(valid) < 4096 or unsampled:
        raise RuntimeError(f'Fixture insufficient: usable={len(valid)} unsampled={unsampled}')
    fixture['id'] = 'qa_capacity_jingfeng'
    fixture['name'] = '京奉容量测量（地理夹具，非历史起局）'
    fixture['qa_capacity_fixture'] = True
    fixture['military_deployment_claimed'] = False
    fixture['fixture_source'] = {
        'compiler_sha256': sha(Path(compiler.__file__)),
        'elevation_cache_sha256': sha(SOURCE_PATH),
        'production_elevation_cache_sha256': sha(compiler.ELEVATION_PATH),
        'total_cells': len(fixture['cells']), 'usable_cells': len(valid),
        'restriction_preserved': True, 'queried_sample_count': len(keys),
        'generated_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    MAP_PATH.write_text(json.dumps(fixture, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    preserved = all(sha(path) == digest for path, digest in originals.items())
    report = {'passed': preserved, 'fixture': str(MAP_PATH.relative_to(ROOT)),
              'fixture_sha256': sha(MAP_PATH), **fixture['fixture_source'],
              'production_content_files_preserved': len(originals),
              'published_content_changed': not preserved,
              'historical_military_start': False,
              'data_docs': ['https://www.opentopodata.org/', 'https://www.opentopodata.org/datasets/srtm/']}
    (P / 'reports/capacity_geography.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False), flush=True)
    if not preserved:
        raise RuntimeError('Published content was modified')


if __name__ == '__main__':
    main()
