"""Wait for the previous portrait coordinator; keep three gateway jobs total."""
from pathlib import Path
import json,subprocess,sys,time
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1]
REPORT=ROOT/'output/imagegen/warlord/commander_expansion_v0228/boorman_commanders_generation.json'
while True:
 try:d=json.loads(REPORT.read_text('utf-8'))
 except (FileNotFoundError,ValueError,PermissionError):time.sleep(10);continue
 if d.get('terminal'):
  if not d.get('passed'):raise SystemExit('Previous generation failed; retry the same route first.')
  break
 time.sleep(10)
with (BASE/'essential_commanders_coordinator.log').open('a',encoding='utf-8') as log:
 result=subprocess.run([sys.executable,'-X','utf8',str(BASE/'generate_expansion_portraits.py'),'--roster',str(BASE/'essential_commanders.json'),'--workers','3'],stdout=log,stderr=subprocess.STDOUT)
raise SystemExit(result.returncode)
