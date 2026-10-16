"""Seal actual completed AI reports against their rule-code dependencies."""
from pathlib import Path
import json
import hashlib
from datetime import datetime, timezone
from build_release import rule_dependencies_digest, source_digest

P=Path(__file__).resolve().parents[1]


def main():
    dependency_hash,modified=rule_dependencies_digest()
    fingerprint=json.loads((P/'reports/sample_state_v2.json').read_text(encoding='utf-8'))['content_hash']
    catalog=json.loads((P/'content/scenarios/catalog.json').read_text(encoding='utf-8'))
    expected_short=0
    for scenario_id in catalog['scenarios']:
        recipe=json.loads((P/'content/scenarios'/f'{scenario_id}.json').read_text(encoding='utf-8'))
        expected_short += 3 if recipe.get('mode')=='campaign' else 1
    rows=[]
    for name,count in [('ai_soak.json',expected_short),('ai_full_conquest.json',6)]:
        path=P/'reports'/name;report=json.loads(path.read_text(encoding='utf-8'))
        if not report['invariants_passed'] or report['cases']!=count or report['content_hash']!=fingerprint or path.stat().st_mtime<modified:
            raise SystemExit('Completed current-rule evidence required: '+name)
        if name=='ai_full_conquest.json' and not report['meets_80_round_conquest']:
            raise SystemExit('The actual 80-round conquest requirement is not met.')
        rows.append({'file':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'completed_after_rule_edits':True})
    result={'created_at_utc':datetime.now(timezone.utc).isoformat(),'content_hash':fingerprint,
            'rules_dependency_sha256':dependency_hash,'runtime_source_sha256_at_seal':source_digest()[0],
            'reports':rows,'scope':'Actual completed native AI tests; renderer-only revisions retain this evidence only while all rule dependencies and report bytes match.'}
    (P/'reports/ai_dependency_evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Sealed {expected_short} short cases and 6 full conquests against their unchanged rule dependencies.')


if __name__=='__main__':main()
