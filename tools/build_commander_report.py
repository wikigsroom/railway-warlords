"""Publish reviewable names and dated side counts without a complete-OOB claim."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import csv,json
from build_release import P,current_version

def read(p):return json.loads(p.read_text('utf-8-sig'))
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 generals=read(P/'content/definitions/generals.json');services=read(P/'content/definitions/commander_service.json')
 sources=read(P/'content/definitions/commander_sources.json');source_index={r['id']:r for r in sources}
 deployments=read(P/'content/definitions/commander_deployments.json');recall={r['id']:r for r in read(P/'content/definitions/commander_recall_pools.json')}
 starting_ids={e['general_id'] for s in deployments for entries in s['factions'].values() for e in entries}
 reserve_ids={e['general_id'] for s in recall.values() for entries in s['factions'].values() for e in entries}
 deployed_ids=starting_ids|reserve_ids
 portraits=read(P/'presentation/data/general_portraits.json')['generals'];factions={r['id']:r['name'] for r in read(P/'content/definitions/factions.json')}
 csv_dir=P/'docs/data';csv_dir.mkdir(parents=True,exist_ok=True)
 rows=[]
 for person in services:
  assert person['documented_title'] and person['source_ids'] and all(s in source_index for s in person['source_ids']),person['id']
  art=portraits.get(person['id'],{});stages={r['age_stage'] for r in art.get('variants',[])}
  rows.append(dict(id=person['id'],name=person['name'],country=person['country'],birth_year=person['birth_year'],death_year=person['death_year'],command_level=person['command_level'],documented_title=person['documented_title'],documented_year=person.get('documented_year'),full_tenure_verified=False,portrait_stages_registered=len(stages),source_ids=' | '.join(person['source_ids']),reference_urls=' | '.join(person.get('reference_urls',[]))))
  rows[-1].update(has_authored_starting_deployment=person['id'] in starting_ids,
   has_optional_free_world_reserve=person['id'] in reserve_ids,
   catalogue_only_pending_dated_deployment=person['id'] not in deployed_ids)
 with (csv_dir/'commanders.csv').open('w',encoding='utf-8-sig',newline='') as f:
  out=csv.DictWriter(f,fieldnames=list(rows[0]));out.writeheader();out.writerows(rows)
 side_rows=[]
 for scenario in deployments:
  recipe=read(P/'content/scenarios'/(scenario['id']+'.json'))
  for side,entries in scenario['factions'].items():
   options=recall.get(scenario['id'],{}).get('factions',{}).get(side,[])
   side_rows.append(dict(scenario_id=scenario['id'],scenario=recipe['name'],mode=recipe['mode'],date=scenario['anchor_date'],faction=side,faction_name=factions.get(side,side),authored_starting_commanders=len(entries),optional_free_world_reserves=len(options),starting_names=' | '.join(next(r['name'] for r in generals if r['id']==e['general_id']) for e in entries),exhaustive_historical_oob=False))
 with (csv_dir/'scenario_commanders.csv').open('w',encoding='utf-8-sig',newline='') as f:
  out=csv.DictWriter(f,fieldnames=list(side_rows[0]));out.writeheader();out.writerows(side_rows)
 missing=[r for r in side_rows if r['mode']!='legion' and r['authored_starting_commanders']==0]
 result=dict(version=current_version(),military_commanders=len(generals),countries=dict(Counter(r['country'] for r in services)),command_levels=dict(Counter(r['command_level'] for r in services)),military_people_with_four_portrait_stages=sum(r['portrait_stages_registered']==4 for r in rows),military_people_missing_portrait_stages=[r['id'] for r in rows if r['portrait_stages_registered']<4],sources=len(sources),scenario_roster_snapshots=len(deployments),initial_roster_entries=sum(r['authored_starting_commanders'] for r in side_rows),optional_free_world_reserve_entries=sum(r['optional_free_world_reserves'] for r in side_rows),non_training_sides_without_authored_commander=len(missing),unfilled_sides=missing,all_qualifying_asian_commanders_covered=False,complete_historical_orders_of_battle=False,full_service_tenures_verified=False,historical_likeness_approval=False,formal_art_approval=False,updated_at_utc=datetime.now(timezone.utc).isoformat())
 result.update(distinct_starting_commanders=len(starting_ids),distinct_optional_reserve_commanders=len(reserve_ids),
  distinct_commanders_with_authored_gameplay_availability=len(deployed_ids),
  catalogue_only_pending_dated_deployment=len(generals)-len(deployed_ids))
 write(P/'reports/commander_coverage.json',result)
 print(json.dumps({k:v for k,v in result.items() if k not in ['unfilled_sides','military_people_missing_portrait_stages']}))

if __name__=='__main__':main()
