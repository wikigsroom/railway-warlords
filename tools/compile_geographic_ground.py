"""Compile numeric material references from archived ecological polygons.

The lattice is independent of operation hexes. It is not a historical land-use
survey, artwork, vegetation map or a source for movement/combat modifiers.
"""
from collections import Counter
from pathlib import Path
import base64
import gzip
import hashlib
import json
import time

from compile_terrain_surfaces import P, ROOT, SOURCE, family_for
import numpy as np
import shapely
from shapely.strtree import STRtree


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    started = time.monotonic()
    output = P / 'presentation/data/asia_ground_regions.json'
    assert not output.exists(), 'Do not overwrite a compiled source without review'
    authority = json.loads((P / 'presentation/data/terrain_surface_regions.json').read_bytes())
    for suffix, expected in authority['source_files_sha256'].items():
        assert sha(SOURCE.with_suffix(suffix)) == expected
    cache_path = ROOT / 'output/geodata/ground_coverage_ecoregions_cache.json.gz'
    with gzip.open(cache_path, 'rt', encoding='utf-8') as stream:
        cache = json.load(stream)
    assert cache['sources'] == authority['source_files_sha256']
    assert cache['classifier_sha256'] == sha(P / 'tools/compile_terrain_surfaces.py')
    regions = cache['regions']
    tree = STRtree(shapely.from_wkb([bytes.fromhex(value) for value in cache['wkb']]))
    # Family ordering exactly matches the runtime Texture2DArray registry.
    families = sorted(json.loads((P / 'presentation/data/ground_macro_catalog.json').read_bytes())['records'])
    west, south, east, north, step = 20., -10., 180., 80., .1
    width, height = 1601, 901
    material = np.zeros((height, width), dtype=np.uint8)
    ecological = np.full((height, width), 65535, dtype=np.uint16)
    ambiguities = 0
    for first in range(0, height, 32):
        last = min(first + 32, height)
        xs, ys = np.meshgrid(west + np.arange(width)*step, north - np.arange(first, last)*step)
        pairs = tree.query(shapely.points(xs.ravel(), ys.ravel()), predicate='covered_by')
        ids = np.full(xs.size, -1, dtype=np.int32)
        for index in np.unique(pairs[1]):
            selected = pairs[0, pairs[1] == index]
            # At an exact polygon boundary use the lower ECO_ID deterministically.
            duplicate = selected[ids[selected] >= 0]
            ambiguities += len(duplicate)
            replace = ids[selected] < 0
            if len(duplicate):
                replace |= np.array([regions[int(index)]['id'] < regions[int(i)]['id'] if i >= 0 else True for i in ids[selected]])
            ids[selected[replace]] = int(index)
        flat_material = material[first:last].reshape(-1)
        flat_eco = ecological[first:last].reshape(-1)
        for index in np.unique(ids[ids >= 0]):
            selected = np.flatnonzero(ids == index)
            for below in [False, True]:
                subset = selected[(ys.ravel()[selected] < 32) == below]
                if not len(subset):
                    continue
                # A plain sample asks only for regional substrate. DEM rock
                # highlights are evaluated from measured slopes by the renderer.
                cell = dict(terrain_id='plain', lat_e6=31000000 if below else 33000000, lon_e6=100000000)
                family, _ = family_for(regions[int(index)], cell, float('inf'))
                # Preserve the existing eastern/southern subtropical gate.
                if below and regions[int(index)]['biome'] == 4:
                    for eastern in [False, True]:
                        part = subset[(xs.ravel()[subset] > 70) == eastern]
                        selected_family = 'subtropical_humus' if eastern else 'temperate_meadow'
                        flat_material[part] = families.index(selected_family) + 1
                else:
                    if family in ['temperate_litter', 'boreal_litter', 'conifer_litter']:
                        family = 'temperate_meadow'
                    elif family == 'dry_woodland_litter':
                        family = 'dry_steppe'
                    if family:
                        flat_material[subset] = families.index(family) + 1
                flat_eco[subset] = regions[int(index)]['id']
        print(json.dumps(dict(rows=last, total_rows=height, classified=int(np.count_nonzero(material[first:last])))), flush=True)
    raw = material.tobytes()
    eco_raw = ecological.astype('>u2').tobytes()
    result = dict(format=1, map_id='asia_strategic', source_id=authority['source_id'], source_year=2017,
        source_url=authority['source_url'], attribution=authority['attribution'], license=authority['license'],
        source_files_sha256=authority['source_files_sha256'], classifier_sha256=cache['classifier_sha256'],
        source_cache_sha256=sha(cache_path), geographic_bounds=[west, south, east, north],
        dimensions=[width, height], step_degrees=step, family_names=families,
        encoding='gzip_base64_uint8_family_index_plus_one_zero_unclassified',
        uncompressed_bytes=len(raw), payload_sha256=hashlib.sha256(raw).hexdigest(),
        data_base64=base64.b64encode(gzip.compress(raw, mtime=0)).decode('ascii'),
        ecological_encoding='gzip_base64_uint16_big_endian_65535_unclassified',
        ecological_payload_sha256=hashlib.sha256(eco_raw).hexdigest(),
        ecological_data_base64=base64.b64encode(gzip.compress(eco_raw, mtime=0)).decode('ascii'),
        counts={families[int(index)-1] if index else 'unclassified': int(count) for index,count in Counter(raw).items()},
        exact_polygon_boundary_ties=ambiguities, boundary_tie_rule='lowest_ECO_ID',
        no_nearest_region_fill=True, historical_landuse_survey=False, forest_or_wetland_created=False,
        rules_map_modified=False, artwork_generated=False, full_source_images_modified=False)
    output.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':'))+'\n', encoding='utf-8')
    report = P / 'reports/geographic_ground_v0237/compilation01.json'
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(dict(passed=True, data_file=output.relative_to(P).as_posix(),
        data_sha256=sha(output), controller_sha256=sha(Path(__file__)),
        nodes=width*height, classified_nodes=int(np.count_nonzero(material)),
        elapsed_seconds=round(time.monotonic()-started, 2), scope='Numerical ecological references only; not historical land cover'), indent=2)+'\n', encoding='utf-8')
    print(report.read_text(), flush=True)


if __name__ == '__main__':
    main()
