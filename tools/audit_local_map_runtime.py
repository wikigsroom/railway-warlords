"""Bind the installed local refinement to the audited source and retained maps."""
import json
from pathlib import Path
import subprocess

import refine_local_maps as local

P, WORK = local.P, local.WORK
BASELINE_COMMIT = 'a7a2715ff503be8adb7f96e8ad310234d974bc49'


def previous(relative):
    return subprocess.run(['git', 'show', BASELINE_COMMIT + ':' + relative], cwd=P,
                          check=True, stdout=subprocess.PIPE).stdout


def main():
    baseline = local.read(WORK / 'baseline.json')
    installation = local.read(P / 'reports/local_map_refinement/installation.json')
    pipeline = local.read(P / 'reports/local_map_refinement/presentation_pipeline.json')
    checks, retained = [], []

    def check(ok, name):
        checks.append(dict(name=name, passed=bool(ok)))

    check(pipeline['terminal'] and pipeline['passed'], 'six_presentation_stages_completed')
    for mid in local.MAPS:
        path = P / 'content/maps' / (mid + '.json')
        check(local.sha(path) == installation['installed_map_hashes'][mid]
              == local.sha(WORK / 'candidates' / path.name), mid + ':installed_bytes_match_audited_candidate')
        new, old = local.read(path), baseline['source_files'][mid]
        scale = old['hex_radius_m'] / new['hex_radius_m']
        def scaled(points):
            return [[round(v * scale, 2) for v in p] for p in points]
        check(scale == 5 and new['hex_radius_px'] == old['hex_radius_px'] == 48,
              mid + ':fivefold_geographic_scale_with_fixed_operation_hex')
        check(new['geographic_bounds'] == old['geographic_bounds'] and new['projection'] == old['projection'],
              mid + ':real_frame_and_projection_retained')
        check(new['render_extent'] == scaled(old['render_extent']), mid + ':complete_vector_extent_scaled_exactly')
        check(new['render_coast'] == [scaled(row) for row in old['render_coast']], mid + ':coast_vectors_scaled_exactly')
        check(new['render_land'] == [dict(exterior=scaled(row['exterior']),
              holes=[scaled(h) for h in row['holes']]) for row in old['render_land']],
              mid + ':all_land_exteriors_and_holes_retained')
    # Compare actual bytes with the last committed release, not only a compiler
    # status flag or a filename list. No files are checked out or overwritten.
    for path in sorted((P / 'content/maps').glob('*.json')):
        if path.stem in local.MAPS:
            continue
        relative = path.relative_to(P).as_posix()
        check(path.read_bytes() == previous(relative), relative + ':unchanged_from_previous_commit')
        retained.append(relative)
    for folder in ['content/definitions', 'content/scenarios']:
        for path in sorted((P / folder).glob('*.json')):
            relative = path.relative_to(P).as_posix()
            check(path.read_bytes() == previous(relative), relative + ':authored_content_retained')
            retained.append(relative)
    for relative in ['assets/manifest.json', 'docs/asset-provenance/index.json',
                     'presentation/data/music_catalog.json']:
        check((P / relative).read_bytes() == previous(relative), relative + ':provenance_retained')
    old_places = local.read(WORK / 'prior_catalogues/settlements_v023.json')
    new_places = local.read(P / 'presentation/data/settlements_v023.json')
    check(all(old_places[k] == new_places[k] for k in old_places if k != 'maps'),
          'all_authored_place_records_and_sources_retained')
    for mid in old_places['maps']:
        if mid not in local.MAPS:
            check(old_places['maps'][mid] == new_places['maps'][mid], mid + ':settlement_and_control_inputs_retained')
    coast_receipt_path = P / 'reports/local_map_refinement/coastal_control_rebuild.json'
    coast_receipt = local.read(coast_receipt_path)
    coast_catalog = local.read(P / 'presentation/data/coast_geometry.json')
    check(coast_receipt['passed'] and not coast_receipt['geography_or_rule_cells_modified'],
          'coastal_control_rebuild_has_separate_scope_receipt')
    for row in coast_receipt['maps']:
        mid = row['map_id']
        path = P / coast_catalog['maps'][mid]['file']
        prior = WORK / 'prior_coastal_control_rebuild' / path.name
        old_mesh, new_mesh = local.read(prior), local.read(path)
        check(local.sha(prior) == row['previous_mesh_sha256'] and
              local.sha(path) == row['current_mesh_sha256'] == coast_catalog['maps'][mid]['data_sha256'],
              mid + ':old_and_new_coastal_controls_bound_to_actual_bytes')
        check({k:v for k,v in old_mesh.items() if k != 'control_zones_by_year'} ==
              {k:v for k,v in new_mesh.items() if k not in ['control_zones_by_year','control_revision']},
              mid + ':every_non_control_mesh_value_retained')
    settlement_validation_path = P / 'reports/settlement_geography_validation.json'
    settlement_validation = local.read(settlement_validation_path)
    check(settlement_validation['passed'] and len(settlement_validation['checks']) == 207,
          'independent_current_settlement_and_coastal_control_geometry_passed')
    archive = WORK / 'srtm_original_responses.zip'
    check(local.sha(archive) == installation['raw_archive_sha256'], 'immutable_original_response_archive_retained')
    report = dict(passed=all(row['passed'] for row in checks), checks=checks,
        failed=[row['name'] for row in checks if not row['passed']],
        baseline_commit=BASELINE_COMMIT,
        retained_authored_data_files=retained,
        installed_map_sha256=installation['installed_map_hashes'],
        presentation_pipeline_sha256=local.sha(P / 'reports/local_map_refinement/presentation_pipeline.json'),
        coastal_control_receipt_sha256=local.sha(coast_receipt_path),
        current_settlement_validation_sha256=local.sha(settlement_validation_path),
        raster_scope='Manifest and provenance bytes only; individual media are checked separately by validate_project.',
        source_rasters_modified=False, new_rasters=0, new_music_generated=False,
        historical_river_bank_or_harbor_survey_claimed=False,
        physical_android_device_tested=False, ew6_parity_claimed=False)
    local.write(P / 'reports/local_map_refinement/scope.json', report)
    print(json.dumps(dict(passed=report['passed'], checks=len(checks), failed=report['failed'])), flush=True)
    return int(not report['passed'])


if __name__ == '__main__':
    raise SystemExit(main())
