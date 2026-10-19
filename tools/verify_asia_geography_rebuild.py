"""Rebuild from archived vectors and DEM in memory; never overwrite geography."""
from datetime import datetime, timezone
import hashlib
import json
from build_asia_map import PROJECT, compile_map
from compile_coast_detail import geometry_for, source_for, capture_baseline, PLAN


def main():
    path=PROJECT/'content/maps/asia_strategic.json'
    published=json.loads(path.read_text(encoding='utf-8'));rebuilt=compile_map()
    # The original Natural Earth/DEM builder remains the authority for cells,
    # cities, rivers, administration and rules. Compose the separately sourced
    # marine drawing fields, which have their own independent raw-GIS audit.
    baseline=capture_baseline()['maps']['asia_strategic']
    source,_=source_for('asia_strategic',PLAN['asia_strategic'],rebuilt,check=True)
    visual,_=geometry_for(rebuilt,source,baseline);rebuilt.update(visual)
    fields=sorted(set(published)|set(rebuilt))
    differences=[key for key in fields if published.get(key)!=rebuilt.get(key)]
    result=dict(passed=not differences,created_at_utc=datetime.now(timezone.utc).isoformat(),
        published_map_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        differing_top_level_fields=differences,cells=len(rebuilt['cells']),
        original_data_modified=False,map_file_written=False,
        scope='Full semantic equality of original rule-vector/DEM rebuild plus independently audited GSHHG marine display geometry; includes every cell classification, city, river, rail and historical field')
    (PROJECT/'reports/asia_relief_rebuild_verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result),flush=True)
    raise SystemExit(0 if result['passed'] else 1)


if __name__=='__main__':main()
