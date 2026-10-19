"""Bind the completed native geometry log/report to their current dependencies."""
from datetime import datetime,timezone
import hashlib
import json
from build_release import P,current_version,source_digest
from regression_dependencies import identity


def main():
    report=P/'reports/coast_geometry_tests.json';log=P/'reports/coast_geometry_native.log'
    value=json.loads(report.read_text(encoding='utf-8'));digest,modified=identity('coast_geometry_test')
    text=log.read_text(encoding='utf-8',errors='replace')
    passed=(value['passed'] and value['build_version']==current_version() and len(value['checks'])==61
            and min(report.stat().st_mtime,log.stat().st_mtime)>=modified
            and 'COAST_GEOMETRY_TEST ' in text and 'SCRIPT ERROR:' not in text and '\nERROR:' not in text)
    result=dict(passed=passed,version=current_version(),runtime_source_sha256=source_digest()[0],
        dependency_sha256=digest,report=report.relative_to(P).as_posix(),report_sha256=hashlib.sha256(report.read_bytes()).hexdigest(),
        log=log.relative_to(P).as_posix(),log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),
        checks=len(value['checks']),created_at_utc=datetime.now(timezone.utc).isoformat(),
        scope='Native Godot source-engine geometry checks, separate from exported executable viewport verification.',
        physical_android_device_tested=False)
    (P/'reports/coast_detail_native_geometry_evidence.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result),flush=True);raise SystemExit(0 if passed else 1)


if __name__=='__main__':main()
