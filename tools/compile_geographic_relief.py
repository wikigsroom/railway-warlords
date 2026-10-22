"""Numerical presentation DEM from immutable registered scientific GeoTIFFs.

No game-art raster, game cell, coastline, historical land cover or rule is made
or changed. The JSON contains signed elevation samples, not a rendered image.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import base64
import gzip
import hashlib
import json
import math
import sys

P = Path(__file__).resolve().parents[1]
ROOT = P.parents[1]
sys.path.insert(0, str(ROOT / '.toolchain/python-libs'))
import numpy as np
from PIL import Image
import enlarge_maps as source

DEST = P / 'presentation/data/asia_presentation_dem.json'
REPORT = P / 'reports/geographic_relief_v0236/source_compile01.json'
ZOOM = 4
STEP = .05


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
        stream.write('\n')


def main():
    if DEST.exists() or REPORT.exists():
        raise FileExistsError('Refuse to replace an archived numerical DEM or compilation receipt')
    map_path = P / 'content/maps/asia_strategic.json'
    before = sha(map_path)
    data = json.loads(map_path.read_bytes())
    west, south, east, north = data['geographic_bounds']
    width = round((east-west)/STEP)+1
    height = round((north-south)/STEP)+1
    _, xlo, ylo = source.tile_for(north, west, ZOOM)
    _, xhi, yhi = source.tile_for(south, east-1e-8, ZOOM)
    tiles = [(ZOOM, x, y) for x in range(xlo, xhi+1) for y in range(ylo, yhi+1)]
    records = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(source.download, tile) for tile in tiles]
        for f in as_completed(futures):
            records.append(f.result())
            print(f'Physical source tiles {len(records)}/{len(tiles)}', flush=True)
    mosaic = np.full(((yhi-ylo+1)*512, (xhi-xlo+1)*512), -32768.0, dtype=np.float64)
    first_tie = None
    for z, x, y in tiles:
        path = source.DEM / f'{z}_{x}_{y}.tif'
        with Image.open(path) as im:
            grid = np.asarray(im).astype(np.float64)
            scale = im.tag_v2[33550]
            tie = im.tag_v2[33922]
            keys = im.tag_v2[34735]
            tags = {keys[i]: keys[i+3] for i in range(4, len(keys), 4)}
            if tags.get(3072) != 3857 or tags.get(1025) != 2:
                raise ValueError('Expected the registered EPSG:3857 PixelIsPoint source')
            if float(im.tag_v2[42113]) != -32768:
                raise ValueError('Unexpected missing-data sentinel')
        if first_tie is None:
            first_tie = (tie[3], tie[4], scale[0], scale[1])
        ex = first_tie[0]+(x-xlo)*512*first_tie[2]
        ey = first_tie[1]-(y-ylo)*512*first_tie[3]
        if abs(tie[3]-ex)>.001 or abs(tie[4]-ey)>.001 or max(abs(scale[i]-first_tie[i+2]) for i in range(2))>1e-6:
            raise ValueError('Source tile registration is not a continuous mosaic')
        mosaic[(y-ylo)*512:(y-ylo+1)*512, (x-xlo)*512:(x-xlo+1)*512] = grid
    lons = west+np.arange(width)*STEP
    lats = north-np.arange(height)*STEP
    mx = np.radians(lons)*6378137
    my = np.log(np.tan(np.pi/4+np.radians(lats)/2))*6378137
    px = (mx-first_tie[0])/first_tie[2]
    py = (first_tie[1]-my)/first_tie[3]
    # The eastmost node at 180° has no east-neighbour tile. One-sided edge
    # support is recorded, limited to at most one original source pixel.
    edge_x = int(np.count_nonzero((px<0)|(px>mosaic.shape[1]-1)))
    edge_y = int(np.count_nonzero((py<0)|(py>mosaic.shape[0]-1)))
    if min(px)<-1.001 or max(px)>mosaic.shape[1]+.001 or min(py)<-1.001 or max(py)>mosaic.shape[0]+.001:
        raise ValueError('Requested samples extend beyond original DEM support')
    px = np.clip(px, 0, mosaic.shape[1]-1)
    py = np.clip(py, 0, mosaic.shape[0]-1)
    x0 = np.floor(px).astype(int); x1 = np.minimum(x0+1, mosaic.shape[1]-1)
    y0 = np.floor(py).astype(int); y1 = np.minimum(y0+1, mosaic.shape[0]-1)
    fx = px-x0; fy = py-y0
    total = np.zeros((height,width)); weight = np.zeros((height,width))
    for xx, yy, w in [(x0,y0,(1-fy)[:,None]*(1-fx)[None,:]),
                      (x1,y0,(1-fy)[:,None]*fx[None,:]),
                      (x0,y1,fy[:,None]*(1-fx)[None,:]),
                      (x1,y1,fy[:,None]*fx[None,:])]:
        h = mosaic[yy[:,None],xx[None,:]]
        valid = (h!=-32768)&np.isfinite(h)
        total += np.where(valid,h*w,0)
        weight += np.where(valid,w,0)
    if np.any(weight<=0):
        raise ValueError('Missing elevation support; never replace it with guessed mountains')
    sampled = total/weight
    integer = np.rint(sampled).astype('>i2')
    if sampled.min()<=-32768 or sampled.max()>32767:
        raise ValueError('Elevation exceeds signed int16 representation')
    raw = integer.tobytes()
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)
    source_records = sorted(records,key=lambda r:r['id'])
    result = dict(format=1,map_id='asia_strategic',source_id='Tilezen_TerrainTiles_geotiff',
                  source_zoom=ZOOM,source_url='https://registry.opendata.aws/terrain-tiles/',
                  attribution_url='https://github.com/tilezen/joerd/blob/master/docs/attribution.md',
                  attribution='Elevation: Mapzen / Tilezen; underlying SRTM, GMTED2010 and ETOPO1 sources. See original provider attribution.',
                  geographic_bounds=[west,south,east,north],step_degrees=STEP,dimensions=[width,height],
                  registration='node samples; northwest to southeast, inclusive domain endpoints',
                  interpolation='EPSG:3857 registered PixelIsPoint mosaic, bilinear, valid-source weights only',
                  source_projected_pixel_size_m=list(first_tie[2:]),
                  eastern_one_sided_node_columns=edge_x,other_one_sided_node_rows=edge_y,
                  encoding='gzip_base64_signed_int16_big_endian_metres',
                  maximum_rounding_error_m=float(np.max(abs(sampled-integer.astype(np.float64)))),
                  sample_count=width*height,uncompressed_bytes=len(raw),payload_sha256=hashlib.sha256(raw).hexdigest(),
                  minimum_height_m=int(integer.min()),maximum_height_m=int(integer.max()),nodata_samples=0,
                  physical_surface_only=True,historical_landcover_claimed=False,rules_changed=False,
                  source_tiles=source_records,data_base64=base64.b64encode(compressed).decode('ascii'))
    assert sha(map_path)==before
    write(DEST,result)
    report={k:v for k,v in result.items() if k not in ['data_base64','source_tiles']}
    report.update(passed=True,created_at_utc=datetime.now(timezone.utc).isoformat(),compiler_sha256=sha(__file__),
                  output_sha256=sha(DEST),output_bytes=DEST.stat().st_size,source_tiles=source_records,
                  game_map_sha256_before=before,game_map_sha256_after=sha(map_path),
                  original_source_bytes_modified=False,raster_art_generated=False)
    write(REPORT,report)
    print(json.dumps({k:v for k,v in report.items() if k!='source_tiles'}),flush=True)


if __name__=='__main__':
    main()
