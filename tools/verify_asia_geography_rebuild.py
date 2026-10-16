"""Rebuild from archived vectors and DEM in memory; never overwrite geography."""
from datetime import datetime, timezone
import hashlib
import json
from build_asia_map import PROJECT, compile_map


def main():
    path=PROJECT/'content/maps/asia_strategic.json'
    published=json.loads(path.read_text(encoding='utf-8'));rebuilt=compile_map()
    fields=sorted(set(published)|set(rebuilt))
    differences=[key for key in fields if published.get(key)!=rebuilt.get(key)]
    result=dict(passed=not differences,created_at_utc=datetime.now(timezone.utc).isoformat(),
        published_map_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        differing_top_level_fields=differences,cells=len(rebuilt['cells']),
        original_data_modified=False,map_file_written=False,
        scope='Full semantic equality of source-vector/physical-DEM rebuild to current continental map, including cell classifications and all non-relief data')
    (PROJECT/'reports/asia_relief_rebuild_verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result),flush=True)
    raise SystemExit(0 if result['passed'] else 1)


if __name__=='__main__':main()
