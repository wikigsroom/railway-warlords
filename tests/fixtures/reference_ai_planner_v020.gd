class_name CapacityReferenceAI020
extends RefCounted

var content: ContentRegistry
var kernel: CommandKernel
var moved: Dictionary={}
var attack_cache: Dictionary={}
var attack_global: Array=[]
var attack_geometry: Array=[]
var combat_profiles: Dictionary={}
var combat_generals: Dictionary={}
var combat_statuses: Dictionary={}

func prepare_attack_cache(state: Dictionary) -> void:
	var context=[state.difficulty,state.player_faction_id,state.date,state.weather,state.relations]
	if context!=attack_global or not is_same(attack_geometry,state.map.cells) or not state.map.cells.is_read_only():
		attack_cache.clear();attack_global=context.duplicate(true);attack_geometry=state.map.cells
	combat_profiles.clear();combat_generals.clear();combat_statuses.clear()
	for f in state.factions:combat_profiles[f.id]=f.profile_snapshot
	for g in state.generals:combat_generals[g.id]=g
	for status in state.statuses:
		if not combat_statuses.has(status.target_id):combat_statuses[status.target_id]=[]
		combat_statuses[status.target_id].append(status)

func combat_context(unit: Dictionary) -> Array:
	if unit.is_empty():return []
	return [unit,combat_profiles.get(unit.owner_id,{}),combat_generals.get(unit.general_id,{}),combat_statuses.get(unit.id,[])]

func cached_attack(state: Dictionary, unit: Dictionary, command: Dictionary) -> Dictionary:
	var context=combat_context(unit)
	var record=attack_cache.get(unit.id,{})
	if record.is_empty() or record.context!=context:
		record={"context":context.duplicate(true),"targets":{}};attack_cache[unit.id]=record
	var hex=HexGrid.coordinate(command.target_hex);var key=HexGrid.key(hex)
	var target=StateAccess.at(state,"units",hex);var city=StateAccess.at(state,"cities",hex)
	var target_context=[combat_context(target),city,VisibilityRules.hex_visible(state,unit.owner_id,hex)]
	var saved=record.targets.get(key,{})
	if not saved.is_empty() and saved.context==target_context:return saved.preview
	var preview=kernel.preview(state,command)
	record.targets[key]={"context":target_context.duplicate(true),"preview":preview}
	return preview

func _init(registry: ContentRegistry, commands: CommandKernel) -> void:content=registry;kernel=commands

func make(state: Dictionary, type: String, arguments: Dictionary = {}) -> Dictionary:
	var c=arguments.duplicate(true);c.type=type;c.actor_id=state.turn_order[state.phase_index];c.expected_version=state.state_version;return c

func choose(state: Dictionary) -> Dictionary:
	prepare_attack_cache(state)
	var owner=state.turn_order[state.phase_index]
	var troops=state.units.filter(func(u):return u.owner_id==owner and u.position!=null)
	troops.sort_custom(func(a,b):return str(a.id)<str(b.id))
	var enemies=state.units.filter(func(u):return StateAccess.hostile(state,owner,u.owner_id) and VisibilityRules.unit_visible(state,owner,u))
	for passenger in state.units:
		if passenger.owner_id!=owner or passenger.cargo_parent_id==null:continue
		var ship=StateAccess.find(state,"units",passenger.cargo_parent_id)
		if ship.get("position")==null:continue
		var destination=ship.position
		for objective in state.objectives:
			if objective.type=="disembark" and objective.target_ids.has(passenger.id):destination=objective.destination
		var shores: Array=[]
		for dir in HexGrid.DIRECTIONS:shores.append(HexGrid.coordinate(ship.position)+dir)
		shores.sort_custom(func(a,b):return HexGrid.distance(a,HexGrid.coordinate(destination))<HexGrid.distance(b,HexGrid.coordinate(destination)))
		for shore in shores:
			var c=make(state,"Disembark",{"unit_id":passenger.id,"target_hex":HexGrid.position(shore)})
			if kernel.preview(state,c).valid and state.objectives.any(func(o):return o.type=="disembark" and o.target_ids.has(passenger.id) and HexGrid.distance(shore,HexGrid.coordinate(o.destination))<=1):return c
	if owner==state.player_faction_id:
		for objective in state.objectives:
			if objective.type=="metric" and objective.metric=="air_recon" and state.metrics.air_recon<objective.required:
				for city in state.cities:
					if city.owner_id!=owner:continue
					var c=make(state,"AirRecon",{"city_id":city.id,"target_hex":city.position.duplicate()})
					if kernel.preview(state,c).valid:return c
	var best={};var best_score=-1.0
	for u in troops:
		if not u.attack_ready or u.ammo<=0:continue
		if u.general_id!=null and u.hp*100<u.max_hp*55:continue
		var targets: Array=[]
		for enemy in enemies:targets.append({"hex":enemy.position,"id":enemy.id})
		for city in state.cities:
			if StateAccess.hostile(state,owner,city.owner_id) and city.fort_hp>0:targets.append({"hex":city.position,"id":""})
		for target in targets:
			if not CombatRules.in_range(u,target.hex,content):continue
			var command=make(state,"Attack",{"unit_id":u.id,"target_hex":target.hex})
			var p=cached_attack(state,u,command)
			if not p.valid:continue
			var score=float(p.damage+p.fort_damage)-float(p.counter)*1.3
			var enemy=StateAccess.find(state,"units",target.id)
			if not enemy.is_empty() and p.damage>=enemy.hp:score+=120
			if p.counter>=u.hp:score-=150
			if u.general_id!=null:
				var skill=make(state,"ActivateSkill",{"unit_id":u.id,"target_id":target.id,"target_hex":target.hex})
				var sp=kernel.preview(state,skill)
				if sp.valid and content.definition("skills",sp.skill_id).consumes_main_attack and float(sp.damage+sp.fort_damage)-sp.counter>score:command=skill;score+=15
			if score>best_score:best_score=score;best=command
	if not best.is_empty() and best_score>0:return best
	for u in troops:
		if u.hp*100<u.max_hp*65:
			var c=make(state,"Reinforce",{"unit_id":u.id})
			if kernel.preview(state,c).valid:return c
		if u.def_id=="engineer" and u.work_ready:
			for edge in state.map.rail_edges:
				if edge.damage!="intact":
					var c=make(state,"EngineerWork",{"unit_id":u.id,"edge_id":edge.id,"action":"repair"})
					if kernel.preview(state,c).valid:return c
	for u in troops:
		if u.ap_left<=0 or moved.has(u.id) or state.engineer_jobs.any(func(j):return j.unit_id==u.id):continue
		var goal={};var goal_distance=100000
		var retreat=u.general_id!=null and u.hp*100<u.max_hp*55
		if retreat:
			var home=StateAccess.nearest_city(state,HexGrid.coordinate(u.position),owner)
			if not home.is_empty():goal=home.position;goal_distance=HexGrid.distance(HexGrid.coordinate(u.position),HexGrid.coordinate(goal))
		var mission_goal=false
		for objective in state.objectives:
			if owner!=state.player_faction_id:continue
			var cargo_goal=objective.type=="disembark" and state.units.any(func(v):return objective.target_ids.has(v.id) and v.cargo_parent_id==u.id)
			if (objective.type=="escort" and objective.target_ids.has(u.id)) or cargo_goal:
				goal=objective.destination;goal_distance=HexGrid.distance(HexGrid.coordinate(u.position),HexGrid.coordinate(goal));mission_goal=true
		for city in state.cities:
			if retreat:break
			if mission_goal:break
			if StateAccess.hostile(state,owner,city.owner_id):
				var d=HexGrid.distance(HexGrid.coordinate(u.position),HexGrid.coordinate(city.position))
				if d<goal_distance:goal_distance=d;goal=city.position
		for enemy in enemies:
			if retreat:break
			if mission_goal:break
			var d=HexGrid.distance(HexGrid.coordinate(u.position),HexGrid.coordinate(enemy.position))
			if d<goal_distance:goal_distance=d;goal=enemy.position
		if goal.is_empty():continue
		var paths=MovementRules.reachable(state,u,content)
		var origin=HexGrid.coordinate(u.position);var target_hex=HexGrid.coordinate(goal)
		var candidate={};var score_best=-100000.0
		for key in paths.costs:
			var h=HexGrid.from_key(key)
			if h==origin or not StateAccess.at(state,"units",h).is_empty():continue
			var score=float(goal_distance-HexGrid.distance(h,target_hex))*12-float(paths.costs[key])*.15
			var d=content.definition("units",u.def_id)
			var distance=HexGrid.distance(h,target_hex)
			if distance>=d.range_min and distance<=d.range_max:score+=10
			if distance<d.range_min and not mission_goal:score-=40
			var cover=content.definition("terrains",StateAccess.cell(state,h).terrain_id).cover_defense;score+=cover*.2
			if u.hp*100<u.max_hp*35 and MovementRules.adjacent_hostile(state,u,h,content):score-=40
			if retreat and MovementRules.adjacent_hostile(state,u,h,content):score-=120
			if score>score_best:score_best=score;candidate=HexGrid.position(h)
		moved[u.id]=true
		if not candidate.is_empty() and score_best>0:return make(state,"Move",{"unit_id":u.id,"target_hex":candidate})
	if state.units.size()<220:
		for city in state.cities:
			if city.owner_id!=owner or city.recruit_queue.size()>=1:continue
			var nearby=StateAccess.nearest_city(state,HexGrid.coordinate(city.position),owner)
			if nearby.is_empty():continue
			var c=make(state,"Recruit",{"city_id":city.id,"def_id":"rifle","stack":1})
			if StateAccess.faction(state,owner).resources.food>40 and kernel.preview(state,c).valid:return c
	# A neutral AI only declares against a reachable neighboring power, preserving deterministic diplomacy.
	if state.mode=="conquest" and not state.factions.any(func(f):return not f.eliminated and StateAccess.hostile(state,owner,f.id)):
		for f in state.factions:
			if f.id==owner or f.eliminated:continue
			var own_cities=state.cities.filter(func(c):return c.owner_id==owner)
			var neighboring=state.cities.any(func(c):return c.owner_id==f.id and own_cities.any(func(a):return HexGrid.distance(HexGrid.coordinate(c.position),HexGrid.coordinate(a.position))<=10))
			if neighboring:
				var c=make(state,"Diplomacy",{"target_faction_id":f.id,"action":"declare_war"})
				if kernel.preview(state,c).valid:return c
	attack_cache.clear();attack_global=[];attack_geometry=[]
	return make(state,"EndPhase")
