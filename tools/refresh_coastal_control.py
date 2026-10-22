"""Rebuild control influence on reviewed coastal land, preserving all map rules."""
from datetime import datetime, timezone
import copy
import json
import shutil

import refine_local_maps as local
from compile_settlements import control_zones
from compile_coast_detail import encode
from build_release import current_version

P, WORK = local.P, local.WORK
MAPS = ['jingjin', 'jingfeng', 'conquest_china']


def main():
    assert current_version() == '0.2.34'
    pipeline = local.read(P / 'reports/local_map_refinement/presentation_pipeline.json')
    assert pipeline['passed'] and pipeline['terminal']
    before = WORK / 'prior_coastal_control_rebuild'
    assert not before.exists(), 'Keep each completed or failed control rebuild immutable.'
    before.mkdir()
    failed_check = P / 'reports/settlement_geography_validation.json'
    if failed_check.exists():
        shutil.copyfile(failed_check, before / 'pre_rebuild_validation.json')
    catalog_path = P / 'presentation/data/coast_geometry.json'
    shutil.copyfile(catalog_path, before / catalog_path.name)
    catalog = local.read(catalog_path)
    map_hashes = {path.name: local.sha(path) for path in (P / 'content/maps').glob('*.json')}
    place_hash = local.sha(P / 'presentation/data/settlements_v023.json')
    pending, records = {}, []
    for mid in MAPS:
        entry = catalog['maps'][mid]
        path = P / entry['file']
        assert local.sha(path) == entry['data_sha256']
        shutil.copyfile(path, before / path.name)
        old = local.read(path)
        new = copy.deepcopy(old)
        data = local.read(P / 'content/maps' / (mid + '.json'))
        assert local.sha(P / 'content/maps' / (mid + '.json')) == entry['map_sha256']
        assert old['settlement_source_sha256'] == place_hash
        years = {}
        for year in ['1920', '1922', '1924']:
            zones = control_zones(data, year)
            for zone in zones:
                # Compatibility with the coastal mesh schema. The source now
                # already includes current land clipping; no old-coast gap is
                # carried over from the archived pre-coast control triangles.
                zone['area'] = zone.pop('area_px2')
                zone['source_area'] = zone['area']
                zone['removed_water_area'] = 0.0
            years[year] = zones
        new['control_zones_by_year'] = years
        new['control_revision'] = 'dated_province_city_influence_on_current_reviewed_land_v0234'
        assert {k:v for k,v in old.items() if k != 'control_zones_by_year'} == {
            k:v for k,v in new.items() if k not in ['control_zones_by_year', 'control_revision']}
        pending[mid] = (path, encode(new))
        records.append(dict(map_id=mid, previous_mesh_sha256=local.sha(path),
            source_map_sha256=entry['map_sha256'], land_and_coast_and_admin_values_unchanged=True,
            cities_and_dated_province_sources_unchanged=True,
            zones_by_year={year:len(zones) for year,zones in years.items()}))
        print('COASTAL_CONTROL_COMPILED ' + mid, flush=True)
    for mid, (path, raw) in pending.items():
        path.write_bytes(raw)
        catalog['maps'][mid]['data_sha256'] = local.sha(path)
        next(row for row in records if row['map_id'] == mid)['current_mesh_sha256'] = local.sha(path)
    catalog_path.write_bytes(encode(catalog))
    assert place_hash == local.sha(P / 'presentation/data/settlements_v023.json')
    assert map_hashes == {path.name:local.sha(path) for path in (P / 'content/maps').glob('*.json')}
    local.write(P / 'reports/local_map_refinement/coastal_control_rebuild.json', dict(
        passed=True, created_at_utc=datetime.now(timezone.utc).isoformat(), maps=records,
        source_settlements_sha256=place_hash, catalog_sha256=local.sha(catalog_path),
        compiler_sha256=local.sha(__file__), source_administration='ENP_China_republican_provinces_CC0',
        source_support='Dated province polygons and authored real city points, partitioned as game influence and intersected with the current reviewed land.',
        historical_military_boundary_survey_claimed=False, geography_or_rule_cells_modified=False,
        new_rasters=0, native_visual_approval=False))
    print('COASTAL_CONTROL_WRITTEN_PENDING_INDEPENDENT_VALIDATION', flush=True)


if __name__ == '__main__':
    main()
