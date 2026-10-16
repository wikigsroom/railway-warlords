"""Run and bind a 100-round native QA match without rewriting published scenarios."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import subprocess
import uuid

from build_release import ENGINE, P, current_version, rule_dependencies_digest, source_digest


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', default='conq_1924', choices=['conq_1920', 'conq_1922', 'conq_1924'])
    parser.add_argument('--player', default='zhili')
    parser.add_argument('--rounds', type=int, default=100)
    parser.add_argument('--seed', default='qa_endurance_20261012_conq_1924')
    args = parser.parse_args()
    if args.rounds < 100:
        parser.error('The long-run acceptance requires at least 100 complete rounds.')
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    folder = P / 'reports/endurance' / run_id
    folder.mkdir(parents=True, exist_ok=False)
    runtime, _ = source_digest()
    rules, _ = rule_dependencies_digest()
    recipe = P / 'content/scenarios' / (args.scenario + '.json')
    sources = [P / 'tests/endurance_soak_test.gd', P / 'tests/immutable_state_fingerprint.gd', Path(__file__)]
    source_records = [{'file': path.relative_to(P).as_posix(), 'sha256': sha(path)} for path in sources]
    initial_recipe = sha(recipe)
    log = folder / 'native.log'
    command = [str(ENGINE), '--headless', '--path', str(P), '--script', 'tests/endurance_soak_test.gd',
               '--', '--output-root', str(folder), '--scenario', args.scenario, '--player', args.player,
               '--rounds', str(args.rounds), '--seed', args.seed]
    print('Native endurance run:', folder.relative_to(P).as_posix(), flush=True)
    with log.open('w', encoding='utf-8') as stream:
        process = subprocess.Popen(command, cwd=P, stdout=stream, stderr=subprocess.STDOUT)
        observed = None
        while process.poll() is None:
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                progress = folder / 'progress.json'
                if progress.is_file():
                    try:
                        value = json.loads(progress.read_text(encoding='utf-8'))
                    except (OSError, json.JSONDecodeError):
                        continue
                    current = (value.get('round'), value.get('commands'), value.get('checkpoints'))
                    if current != observed:
                        print('Endurance progress:', current, 'native PID', process.pid, flush=True)
                        observed = current
    diagnostics = log.read_text(encoding='utf-8', errors='replace')
    result_file = folder / 'result.json'
    result = json.loads(result_file.read_text(encoding='utf-8')) if result_file.is_file() else {}
    unchanged = runtime == source_digest()[0] and rules == rule_dependencies_digest()[0] and initial_recipe == sha(recipe)
    unchanged = unchanged and all(sha(P / row['file']) == row['sha256'] for row in source_records)
    passed = process.returncode == 0 and result.get('passed', False) and unchanged
    passed = passed and result.get('completed_rounds', 0) >= args.rounds and len(result.get('checkpoints', [])) == 20
    passed = passed and result.get('replayed_commands') == 60 and result.get('published_recipe_unchanged', False)
    passed = passed and result.get('starting_deployment_and_all_nonmetadata_fields_preserved', False)
    passed = passed and (folder / 'initial_snapshot.json').is_file() and (folder / 'commands.jsonl').is_file()
    passed = passed and not any(marker in diagnostics for marker in ('SCRIPT ERROR:', '\nERROR:', 'WARNING: ObjectDB'))
    artifacts = [{'file': path.relative_to(P).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size}
                 for path in sorted(folder.iterdir()) if path.is_file()]
    evidence = {'passed': passed, 'version': current_version(), 'created_at_utc': datetime.now(timezone.utc).isoformat(),
                'native_exit_code': process.returncode, 'native_pid': process.pid, 'runtime_source_sha256': runtime,
                'rules_dependency_sha256': rules, 'sources_unchanged_during_run': unchanged, 'sources': source_records,
                'published_scenario_sha256': initial_recipe, 'native_engine_sha256': sha(ENGINE),
                'run_directory': folder.relative_to(P).as_posix(), 'requested_rounds': args.rounds,
                'completed_rounds': result.get('completed_rounds', 0), 'commands': result.get('commands', 0),
                'checkpoint_count': len(result.get('checkpoints', [])), 'replayed_commands': result.get('replayed_commands', 0),
                'physical_android_device_tested': False, 'historical_or_human_balance_acceptance': False,
                'artifacts': artifacts,
                'scope': 'Native 100-round QA deadline extension of a published starting state; all actual rules and AI execute. Ordinary historical conquest remains at its published 80-round budget.'}
    (folder / 'evidence.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    if passed:
        (P / 'reports/endurance_evidence.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({key: evidence[key] for key in ('passed', 'native_exit_code', 'completed_rounds', 'commands', 'checkpoint_count', 'replayed_commands', 'run_directory')}), flush=True)
    if not passed:
        print(diagnostics[-2500:], flush=True)
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
