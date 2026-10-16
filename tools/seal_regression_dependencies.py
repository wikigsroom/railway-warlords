"""Seal passing checks against their actual transitive sources and report bytes."""
import json
from datetime import datetime, timezone
from build_release import source_digest, current_version
from run_validation import CHECKS, PROJECT
from regression_dependencies import dependencies, identity
from package_delivery import sha


def main():
    tag = 'v' + current_version().replace('.', '')
    rows = []
    for check in CHECKS:
        report = PROJECT / 'reports' / ('rule_tests.json' if check == 'run_tests' else check.removesuffix('_test') + '_tests.json')
        log = PROJECT / 'reports' / (check + '_' + tag + '.log')
        digest, changed = identity(check)
        value = json.loads(report.read_text(encoding='utf-8'))
        diagnostic = log.read_text(encoding='utf-8', errors='replace')
        valid = min(report.stat().st_mtime, log.stat().st_mtime) >= changed
        valid = valid and not value.get('failed', 0) and not value.get('failures', [])
        valid = valid and 'SCRIPT ERROR:' not in diagnostic and '\nERROR:' not in diagnostic
        rows.append({'check': check, 'passed': valid, 'dependency_sha256_at_seal': digest,
                     'dependencies': [p.relative_to(PROJECT).as_posix() for p in dependencies(check)],
                     'report': report.name, 'report_sha256': sha(report), 'log': log.name, 'log_sha256': sha(log)})
    evidence = {'passed': all(row['passed'] for row in rows), 'game_version': current_version(),
                'runtime_source_sha256': source_digest()[0], 'created_at_utc': datetime.now(timezone.utc).isoformat(),
                'scope': 'Conservative global-class and explicit scene/script dependency closure, plus all content, schemas, fixtures and raster/font/audio bytes. Native exported screenshots and performance use the complete runtime separately.',
                'checks': rows}
    (PROJECT / 'reports/regression_dependency_evidence.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'passed': evidence['passed'], 'groups': len(rows)}))
    raise SystemExit(0 if evidence['passed'] else 1)


if __name__ == '__main__':
    main()
