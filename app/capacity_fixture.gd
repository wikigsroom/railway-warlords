class_name CapacityFixture
extends RefCounted

# Only explicitly invoked QA tools use this workload. It is never a scenario
# in the player catalog and makes no historical deployment claim.
static func create(content: ContentRegistry, map: Dictionary, distribution: String = "balanced", minimum_cells: int = 4096) -> Dictionary:
	if not map.get("qa_capacity_fixture",false) or map.get("military_deployment_claimed",true):return {}
	var usable=map.cells.filter(func(c):return c.region_id!="restricted")
	if usable.size()<minimum_cells:return {}
	var recipe=content.scenarios.campaign_1924_02.duplicate(true)
	recipe.id="qa_capacity";recipe.map_id=map.id;recipe.full_visibility=true;recipe.events=[];recipe.round_limit=80
	content.maps[map.id]=map;content.scenarios.qa_capacity=recipe
	var s=StateBuilder.create(content,"qa_capacity",recipe.player_default,{})
	if s.is_empty():return {}
	s.units=[];s.generals=[];s.statuses=[];s.visibility=[];s.engineer_jobs=[];s.authored_events=[]
	s.protected_commander_id=null;s.protected_general_id=null
	s.objectives=[{"id":"qa_workload","type":"capture","target_ids":["qa_nonexistent_goal"],"required":1,"progress":0,"protected":false}]
	s.qa_capacity_fixture=true;s.historical_military_deployment=false;s.capacity_distribution=distribution
	# Repeatable QA workload only; production matches retain their random seeds.
	s.match_id="qa_capacity_jingfeng_"+distribution
	s.combat_random=CombatRandom.initialize(s.match_id)
	var shape_hash=ContentRegistry.fingerprint(map)
	s.content_hash=ContentRegistry.fingerprint({"production_content_hash":content.content_hash,"fixture_map_hash":shape_hash,"distribution":distribution})
	s.fixture_map_hash=shape_hash;s.production_content_hash=content.content_hash
	for f in s.factions:
		f.resources={"cash":10000,"food":10000,"arms":10000};f.general_whitelist=[];f.airfield_whitelist=[]
	StateAccess.invalidate_occupancy()
	var anchor=map.cities.filter(func(c):return c.id=="jinzhou")[0].position
	var origin=HexGrid.coordinate(anchor)
	var ordered=usable.duplicate()
	ordered.sort_custom(func(a,b):
		var ah=HexGrid.coordinate(a.position);var bh=HexGrid.coordinate(b.position)
		var ad=HexGrid.distance(ah,origin);var bd=HexGrid.distance(bh,origin)
		return ad<bd if ad!=bd else (ah.x<bh.x if ah.x!=bh.x else ah.y<bh.y))
	var tracks={}
	for edge in s.map.rail_edges:
		if edge.damage=="intact" and MovementRules.rail_available(s,edge):
			for p in edge.path_hexes:tracks[HexGrid.key(HexGrid.coordinate(p))]=true
	var city_hexes={}
	for c in s.cities:city_hexes[HexGrid.key(HexGrid.coordinate(c.position))]=true
	var occupied={};var serial=0
	for definition in content.tables.units:
		var count=24 if definition.id=="militia" else 18
		for i in range(count):
			var destination: Dictionary={}
			for cell in ordered:
				var h=HexGrid.coordinate(cell.position);var key=HexGrid.key(h)
				if occupied.has(key) or city_hexes.has(key):continue
				var terrain=content.definition("terrains",cell.terrain_id)
				var profile=definition.movement_profile
				var legal=terrain.get("cost_"+profile,0)>0
				if profile=="rail":legal=tracks.has(key)
				elif profile in ["water","sea","river"]:
					legal=terrain.get("cost_water",0)>0
					if profile=="river" and cell.terrain_id=="sea":
						legal=HexGrid.DIRECTIONS.any(func(d):
							var near=StateAccess.cell(s,h+d)
							return not near.is_empty() and not content.definition("terrains",near.terrain_id).water)
				elif cell.get("water_under_bridge",false):legal=false
				if legal:destination=cell.position.duplicate();occupied[key]=true;break
			if destination.is_empty():return {}
			var owner=s.turn_order[serial%2]
			if distribution=="concentrated":owner=s.turn_order[1] if serial%10==9 else s.turn_order[0]
			elif distribution=="single_faction":owner=s.turn_order[0]
			var stack=1+i%int(definition.max_stack)
			s.units.append(StateBuilder.unit("qa_capacity_%03d"%serial,definition.id,owner,destination,content,stack))
			serial+=1
	s.initial_player_count=s.units.filter(func(u):return u.owner_id==s.player_faction_id).size()
	VisibilityRules.refresh(s,content);StateAccess.freeze_map(s.map)
	return s
