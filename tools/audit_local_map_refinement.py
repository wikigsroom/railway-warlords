"""Independent source/coordinate checks for the two finer local operation maps."""
from pathlib import Path
import json
import math
import sys

import refine_local_maps as local

sys.path.insert(0, str(local.ROOT / '.toolchain/python-libs'))
import shapefile
from shapely.geometry import Point, box, shape
from shapely.ops import transform, unary_union
from pyproj import Transformer


def main():
    baseline = local.read(local.WORK / 'baseline.json')
    samples = local.read(local.WORK / 'samples.json')
    source = local.read(local.WORK / 'river_source.json')
    requested = local.read(local.WORK / 'request.json')
    checks, measurements = [], []

    def check(ok, name):
        checks.append(dict(name=name, passed=bool(ok)))
        if not ok:
            print('LOCAL_SOURCE_FAILED ' + name, flush=True)

    # Read every original response rather than trusting the aggregated cache.
    reconstructed = {}
    for record in samples['source_responses']:
        path = local.ROOT / record['file']
        check(local.sha(path) == record['sha256'], 'original_response:' + path.stem)
        raw = local.read(path)
        for row in raw['results']:
            key = f"{row['location']['lat']:.6f},{row['location']['lng']:.6f}"
            if key in reconstructed:
                raise ValueError('Duplicate original response point: ' + key)
            reconstructed[key] = row['elevation']
    check(reconstructed == samples['samples'], 'all_92120_values_match_original_provider_bytes')
    check(set(reconstructed) == set(requested['points']), 'every_requested_coordinate_returned_exactly_once')
    check(samples['null_samples'] == 0, 'no_missing_elevation_returns')
    check(local.sha(local.ROOT / source['source_file']) == source['source_sha256'], 'original_hydrorivers_shapefile_unchanged')
    reader = shapefile.Reader(str(local.ROOT / source['source_file']), encoding='utf-8')
    selected = {mid: [] for mid in local.MAPS}
    identifiers = {key for values in source['reach_ids'].values() for key in values}
    for item in reader.iterShapeRecords(bbox=(114.1, 30.4, 118.98, 32.26)):
        if int(item.record.as_dict()['HYRIV_ID']) in identifiers:
            geometry = shape(item.shape.__geo_interface__)
            for mid in local.MAPS:
                region = box(*baseline['source_files'][mid]['geographic_bounds'])
                if geometry.intersects(region):
                    selected[mid].append(geometry.intersection(region))
    for mid in local.MAPS:
        path = local.WORK / 'candidates' / (mid + '.json')
        new, old = local.read(path), baseline['source_files'][mid]
        check(new['geographic_bounds'] == old['geographic_bounds'] and new['projection'] == old['projection'], mid + ':original_real_geography_and_projection')
        check(new['hex_radius_px'] == old['hex_radius_px'] == 48 and new['hex_radius_m'] * 5 == old['hex_radius_m'], mid + ':fivefold_scale_unchanged_hex')
        check(len({c['id'] for c in new['cells']}) == len(new['cells']) == len({tuple(c['position'].values()) for c in new['cells']}), mid + ':unique_full_grid')
        forward = Transformer.from_crs('EPSG:4326', new['projection'], always_xy=True)
        inverse = Transformer.from_crs(new['projection'], 'EPSG:4326', always_xy=True)
        minx, _, _, maxy = transform(forward.transform, box(*new['geographic_bounds'])).bounds
        river = transform(forward.transform, unary_union(selected[mid]))
        max_coordinate_error = 0
        max_river_distance = 0
        outside_operable = 0
        low_support = 0
        west, south, east, north = new['geographic_bounds']
        cells = {(c['position']['q'], c['position']['r']): c for c in new['cells']}
        for (q, r), cell in cells.items():
            xy = minx + 375 * q, maxy - math.sqrt(3) * 250 * (r + q * .5)
            lon, lat = inverse.transform(*xy)
            error = max(abs(lon - cell['lon_e6'] / 1e6), abs(lat - cell['lat_e6'] / 1e6))
            max_coordinate_error = max(max_coordinate_error, error)
            inside = west <= cell['lon_e6'] / 1e6 <= east and south <= cell['lat_e6'] / 1e6 <= north
            outside_operable += not inside and cell['region_id'] != 'restricted'
            if cell['terrain_id'] == 'river':
                max_river_distance = max(max_river_distance, river.distance(Point(xy)))
            if cell.get('elevation_quality'):
                low_support += 1
            key = f"{cell['lat_e6'] / 1e6:.6f},{cell['lon_e6'] / 1e6:.6f}"
            if cell['elevation_m'] != reconstructed[key]:
                raise ValueError('Cell centre elevation differs from the original provider return: ' + cell['id'])
        check(max_coordinate_error <= .000000501, mid + ':every_cell_matches_inverse_real_projection')
        check(outside_operable == 0, mid + ':no_playable_cells_outside_real_authored_frame')
        check(max_river_distance <= 250.01, mid + ':every_rule_water_cell_within_one_radius_of_original_major_channel')
        for city in new['cities']:
            previous = next(c for c in old['cities'] if c['id'] == city['id'])
            check(all(city[k] == previous[k] for k in ('id', 'name', 'lon_e6', 'lat_e6', 'administration_by_year')), city['id'] + ':dated_identity_and_real_coordinate_retained')
            x, y = forward.transform(city['lon_e6'] / 1e6, city['lat_e6'] / 1e6)
            at = city['position'];cx = minx + at['q'] * 375;cy = maxy - math.sqrt(3) * 250 * (at['r'] + at['q'] * .5)
            check(abs(math.hypot(cx - x, cy - y) - city['strategic_hex_displacement_m']) <= .51 and math.hypot(cx - x, cy - y) <= 500, city['id'] + ':independently_measured_city_displacement_under_500m')
            check(max(abs(city['render_position'][i] - previous['render_position'][i] * 5) for i in (0, 1)) <= .04, city['id'] + ':visual_point_exactly_fivefold')
        measurements.append(dict(map_id=mid, cells=len(new['cells']), sha256=local.sha(path),
            max_coordinate_error_deg=max_coordinate_error, max_rule_river_distance_m=max_river_distance,
            flagged_low_elevation_support_cells=low_support, source_reaches=len(selected[mid])))
    report = dict(passed=all(row['passed'] for row in checks), checks=checks, maps=measurements,
        samples_sha256=local.sha(local.WORK / 'samples.json'), original_source_values_modified=False,
        historical_river_banks_or_harbor_locations_surveyed=False, artwork_modified=False, runtime_installed=False)
    target = local.P / 'reports/local_map_refinement/geography_preinstall.json'
    local.write(target, report)
    print(json.dumps(dict(passed=report['passed'], checks=len(checks), maps=measurements), ensure_ascii=False), flush=True)
    return int(not report['passed'])


if __name__ == '__main__':
    raise SystemExit(main())
