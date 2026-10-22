"""Generate independent immutable city sprites through the mandated Sub2 CLI."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import subprocess
import sys
import time

P = Path(__file__).resolve().parents[1]
ROOT = P.parents[1]
WORK = ROOT / 'output/imagegen/warlord/urban_hierarchy_v0235'
CLI = Path('C:/Users/carzy/.codex/skills/sub2-image-gen/scripts/sub2_image_gen.py')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, choices=[1, 2], default=2)
    args = parser.parse_args()
    plan = json.loads((WORK / 'production_plan.json').read_bytes())
    pending = [row for row in plan['assets'] if not (ROOT / row['source_file']).exists()]
    results = []
    started = time.monotonic()

    def generate(row):
        target = ROOT / row['source_file']
        prompt = ROOT / row['prompt_file']
        assert prompt.read_text(encoding='utf-8') == row['prompt'] and not target.exists()
        command = [sys.executable, str(CLI), 'generate', '--model', 'gpt-image-2.5', '--quality', 'high',
                   '--size', '1024x1024', '--background', 'transparent', '--prompt-file', str(prompt), '--out', str(target)]
        with (target.parent / 'generation.log').open('w', encoding='utf-8') as log:
            child = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            print('SUB2_CHILD ' + row['id'] + ' pid=' + str(child.pid), flush=True)
            try:
                code = child.wait(timeout=600)
            except subprocess.TimeoutExpired:
                child.kill(); child.wait(timeout=15); code = -1
        return dict(id=row['id'], native_process_id=child.pid, exit_code=code, source_file=row['source_file'],
                    passed=code == 0 and target.exists() and target.stat().st_size > 1024)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        jobs = {pool.submit(generate, row): row['id'] for row in pending}
        for job in as_completed(jobs):
            result = job.result(); results.append(result)
            print(json.dumps(result), flush=True)
    report = dict(passed=all(row['passed'] for row in results), requested=len(pending), results=results,
                  completed_at_utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.monotonic() - started,
                  source_route='sub2-image-gen/gpt-image-2.5/high', originals_overwritten=False)
    receipt = WORK / ('generation_run_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '.json')
    receipt.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(passed=report['passed'], requested=len(pending), receipt=str(receipt))), flush=True)
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
