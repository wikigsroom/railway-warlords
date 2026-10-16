"""Make test-only timing probes from the current implementation, without editing it."""
from pathlib import Path
import hashlib
import json

P = Path(__file__).resolve().parents[1]
F = P / 'tests/fixtures'
sources = {name: (P / name).read_text(encoding='utf-8') for name in (
    'ai/ai_planner.gd', 'domain/command_kernel.gd', 'domain/movement_rules.gd')}
movement = sources['domain/movement_rules.gd'].replace('class_name MovementRules\n', '', 1)
movement = movement.replace('extends RefCounted\n', 'extends RefCounted\nstatic var compute_us=0\nstatic var sort_us=0\n', 1)
movement = movement.replace('\tvar graph=compute_reachable(state,unit,content,budget)',
    '\tvar compute_start=Time.get_ticks_usec()\n\tvar graph=compute_reachable(state,unit,content,budget)\n\tcompute_us+=Time.get_ticks_usec()-compute_start')
movement = movement.replace('\t\topen.sort_custom(func(a,b):return a.cost<b.cost)',
    '\t\tvar sort_start=Time.get_ticks_usec()\n\t\topen.sort_custom(func(a,b):return a.cost<b.cost)\n\t\tsort_us+=Time.get_ticks_usec()-sort_start')
(F / 'capacity_probe_movement.gd').write_text(movement, encoding='utf-8')
planner = sources['ai/ai_planner.gd'].replace('class_name AIPlanner\n', '', 1)
planner = planner.replace('extends RefCounted\n',
    'extends RefCounted\nconst Probe=preload("res://tests/fixtures/capacity_probe.gd")\n', 1)
planner = planner.replace('MovementRules.reachable(', 'Probe.reachable(')
(F / 'capacity_probe_planner.gd').write_text(planner, encoding='utf-8')
resolve = sources['domain/command_kernel.gd'].split('\nfunc resolve(', 1)[1]
resolve = 'func resolve(' + resolve
for before, after in (
    ('StateAccess.clone_transaction(', 'Probe.clone_transaction('),
    ('MovementRules.resolve_move(', 'Probe.resolve_move('),
    ('VisibilityRules.refresh(', 'Probe.refresh('),
    ('VictoryRules.check(', 'Probe.victory_check('),
    ('TurnRules.end_phase(', 'Probe.end_phase(')):
    resolve = resolve.replace(before, after)
(F / 'capacity_probe_kernel.gd').write_text(
    'extends CommandKernel\nconst Probe=preload("res://tests/fixtures/capacity_probe.gd")\n\n' + resolve,
    encoding='utf-8')
(F / 'capacity_probe_sources.json').write_text(json.dumps({
    'source_sha256': {name: hashlib.sha256((P / name).read_bytes()).hexdigest() for name in sources},
    'purpose': 'Timing-only copies; independent full-state comparison in the driver.'
}, indent=2), encoding='utf-8')
print('Created current test-only timing copies.')
