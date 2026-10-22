"""Expected inventory for the explicit, immutable map source catalogs."""
import json
from pathlib import Path

P = Path(__file__).resolve().parents[1]
BASELINE_COUNT = 74
ADDITIONAL_COUNT = 804
MAP_COUNT = BASELINE_COUNT + ADDITIONAL_COUNT
CATEGORY_COUNTS = {'tile': 176, 'scenery': 480, 'building': 148}
CATALOGS = [
    ('map_bank_plan.json', 'map_bank_generation.json', 666),
    ('map_settlement_extension_plan.json', 'map_settlement_extension_generation.json', 74),
    ('map_surface_extension_plan.json', 'map_surface_extension_generation.json', 56),
    ('map_urban_extension_plan.json', 'map_urban_extension_generation.json', 8),
]


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def planned_rows():
    return [row for catalog, _, _ in CATALOGS for row in
            read(P/'presentation/data'/catalog)['assets']]


def production_rows(require_complete=False):
    rows = []; complete = True
    for _, filename, count in CATALOGS:
        path = P/'reports'/filename
        value = read(path) if path.exists() else {}
        passed = value.get('passed') and not value.get('running') and \
                 value.get('completed') == count and not value.get('failures')
        complete = complete and bool(passed)
        rows.extend(value.get('assets', []))
        if require_complete and not passed:
            raise RuntimeError('Complete production ledger required: '+filename)
    return rows, complete
