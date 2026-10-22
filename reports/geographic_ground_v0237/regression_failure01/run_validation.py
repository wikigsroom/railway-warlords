"""Run the native rule and interaction checks on Windows, without virtualization."""
from pathlib import Path
import subprocess
import sys
import json
from build_release import current_version
from regression_dependencies import modified as dependency_modified

PROJECT = Path(__file__).resolve().parents[1]
ENGINE = PROJECT.parents[1] / '.toolchain/godot/Godot_v4.7.2-stable_win64_console.exe'
CHECKS = ['run_tests', 'acceptance_test', 'input_test', 'geography_test',
          'progression_test', 'transaction_test', 'strategic_history_test',
          'atlas_render_test', 'combat_presentation_test', 'automation_test', 'rules_worker_test', 'map_scale_test', 'scaled_logistics_test', 'movement_cache_test', 'historical_places_test', 'snapshot_optimization_test']
CHECKS.append('asia_content_test')
CHECKS.append('map_detail_boundary_motion_test')
CHECKS.append('facing_memory_test')
CHECKS.append('relief_surface_test')
CHECKS.append('map_bank_test')
CHECKS.append('surface_geography_test')
CHECKS.append('terrain_surfaces_test')
CHECKS.append('map_material_continuity_test')
CHECKS.append('river_surface_test')
CHECKS.append('control_land_clip_test')
CHECKS.append('ground_coverage_test')
CHECKS.append('general_portraits_test')
CHECKS.append('calendar_test')
CHECKS.append('commander_roster_test')

def main():
    # Build the schema fixture with the current native content registry. Rule
    # tests write their own report, not sample_state_v2.json.
    metadata_log=PROJECT/'reports/export_metadata_validation.log'
    with metadata_log.open('w',encoding='utf-8') as out:
        metadata=subprocess.run([str(ENGINE),'--headless','--path',str(PROJECT),
                                 '--script','tools/export_metadata.gd'],cwd=PROJECT,
                                stdout=out,stderr=subprocess.STDOUT,timeout=1800)
    metadata_text=metadata_log.read_text(encoding='utf-8',errors='replace')
    if metadata.returncode or 'SCRIPT ERROR:' in metadata_text or '\nERROR:' in metadata_text:
        print('Current native metadata export failed',flush=True);return 1
    fingerprint=json.loads((PROJECT/'reports/sample_state_v2.json').read_text(encoding='utf-8'))['content_hash']
    for name in CHECKS:
        modified=dependency_modified(name)
        log = PROJECT / 'reports' / (name + '_v' + current_version().replace('.', '') + '.log')
        report=PROJECT/'reports'/('rule_tests.json' if name=='run_tests' else name.removesuffix('_test')+'_tests.json')
        if '--stale-only' in sys.argv and report.exists() and log.exists() and min(report.stat().st_mtime,log.stat().st_mtime)>=modified:
            value=json.loads(report.read_text(encoding='utf-8'));diagnostic=log.read_text(encoding='utf-8',errors='replace')
            if not value.get('failed',0) and not value.get('failures',[]) and value.get('content_hash',fingerprint)==fingerprint and 'SCRIPT ERROR:' not in diagnostic and '\nERROR:' not in diagnostic:
                print(name+': current passing report retained',flush=True);continue
        with log.open('w', encoding='utf-8') as out:
            result = subprocess.run([str(ENGINE), '--headless', '--path', str(PROJECT),
                                     '--script', 'tests/' + name + '.gd'],
                                    cwd=PROJECT, stdout=out, stderr=subprocess.STDOUT, timeout=1800)
        text = log.read_text(encoding='utf-8', errors='replace')
        errors = [line for line in text.splitlines() if 'SCRIPT ERROR:' in line or line.startswith('ERROR:')]
        print(name + ': ' + ('passed' if result.returncode == 0 and not errors else 'FAILED'), flush=True)
        if result.returncode or errors:
            print('\n'.join(text.splitlines()[-12:]))
            return 1
        value=json.loads(report.read_text(encoding='utf-8'))
        if dependency_modified(name)!=modified or value.get('content_hash',fingerprint)!=fingerprint:
            print('Source or native content identity changed during '+name,flush=True);return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
