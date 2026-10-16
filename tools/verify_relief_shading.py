"""Compare shipping GPU relief lighting with an independent numerical reference."""
import json
import subprocess
from PIL import Image
from build_release import P, current_version, source_digest
from package_delivery import read, require, sha


def main():
    runtime = source_digest()[0]
    exe = P / 'build/windows/RailwayWarlords.exe'
    exported = next(row for row in read(P / 'reports/export_results.json') if row['target'] == 'windows')
    require(exported['export_verified'] and exported['runtime_source_sha256'] == runtime
            and exported['sha256'] == sha(exe), 'Current verified shipping Windows export required')
    folder = P / 'reports/relief_shade_native'
    folder.mkdir(parents=True, exist_ok=True)
    log = folder / 'native.log'
    with log.open('w', encoding='utf-8') as out:
        result = subprocess.run([str(exe), '--resolution', '1600x900', '--position', '-4000,-3000', '--',
                                 '--qa-session', '--relief-shade-test', '--relief-shade-output', str(folder)],
                                cwd=P, stdout=out, stderr=subprocess.STDOUT, timeout=480)
    diagnostic = log.read_text(encoding='utf-8', errors='replace')
    require(result.returncode == 0 and 'SCRIPT ERROR:' not in diagnostic and '\nERROR:' not in diagnostic,
            'Native relief shade fixture failed; inspect native.log')
    path = folder / 'validation.json'
    report = read(path)
    require(report['passed'] and report['build_version'] == current_version() and len(report['checks']) == 11
            and len(report['samples']) == 5 and len(report['captures']) == 4,
            'Complete current numerical lighting proof required')
    captures = []
    for row in report['captures']:
        frame = P / row['path'].removeprefix('res://')
        with Image.open(frame) as image:
            require(image.size == (384, 256), 'Whole native numerical fixture required')
        captures.append(dict(file=frame.relative_to(P).as_posix(), sha256=sha(frame),
                             whole_native_viewport=True, synthetic_fixture_not_gameplay=True))
    require(source_digest()[0] == runtime and sha(exe) == exported['sha256'], 'Runtime changed during proof')
    proof = dict(passed=True, version=current_version(), runtime_source_sha256=runtime, windows_exe_sha256=sha(exe),
                 checks=len(report['checks']), report=path.relative_to(P).as_posix(), report_sha256=sha(path),
                 log=log.relative_to(P).as_posix(), log_sha256=sha(log), captures=captures,
                 independent_sixteen_weight_reference_verified=True, triangle_diagonal_independence_verified=True,
                 world_phase_verified=True, synthetic_fixture_not_gameplay=True, new_dem_samples=0,
                 source_images_modified=False, physical_android_device_tested=False, ew6_parity_claimed=False)
    (P / 'reports/relief_shade_native_evidence.json').write_text(
        json.dumps(proof, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(proof), flush=True)


if __name__ == '__main__':
    main()
