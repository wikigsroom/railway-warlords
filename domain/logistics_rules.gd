class_name LogisticsRules
extends RefCounted

static func supply_reach(state: Dictionary, owner: String, content: ContentRegistry) -> Dictionary:
	var distance: Dictionary={};var buckets: Array=[[],[],[],[],[],[],[]]
	var probe={"owner_id":owner,"def_id":"rifle","elite_id":null}
	for c in state.cities:
		var usable=c.owner_id==owner or (StateAccess.relation(state,owner,c.owner_id).get("supply",false) and StateAccess.allied(state,owner,c.owner_id))
		if usable and not c.blockaded:
			var h=HexGrid.coordinate(c.position);distance[HexGrid.key(h)]=0;buckets[0].append(h)
	# Every valid cost is an integer from zero through six. Cost buckets retain
	# Dijkstra's minimum-distance order, including zero-cost rail cycles, without
	# sorting and shifting the entire frontier for every surveyed cell.
	for cost in range(7):
		var cursor=0
		while cursor<buckets[cost].size():
			var now:Vector2i=buckets[cost][cursor];cursor+=1
			if cost!=distance[HexGrid.key(now)]:continue
			for next in MovementRules.neighbors(state,now):
				var c=StateAccess.cell(state,next)
				if c.is_empty() or c.region_id=="restricted":continue
				var city=StateAccess.at(state,"cities",next)
				if not city.is_empty() and city.owner_id!=owner and not (StateAccess.allied(state,owner,city.owner_id) and StateAccess.relation(state,owner,city.owner_id).get("supply",false)):continue
				var enemy=StateAccess.at(state,"units",next)
				if (not enemy.is_empty() and StateAccess.hostile(state,owner,enemy.owner_id)) or MovementRules.adjacent_hostile(state,probe,next,content,false):continue
				var step=int(content.definition("terrains",c.terrain_id).get("cost_foot",0))
				var crossing=MovementRules.crossing_cost(state,now,next)
				if crossing>0:step=crossing
				if step<=0:continue
				# Intact controlled track extends distribution, while off-track reach remains six cost.
				if MovementRules.rail_neighbor(state,now,next):step=0
				var total=cost+step;var key=HexGrid.key(next)
				if total<=6 and total<int(distance.get(key,100000)):
					distance[key]=total;buckets[total].append(next)
	return distance

static func naval_supply_reach(state: Dictionary, owner: String, content: ContentRegistry) -> Dictionary:
	var ports=state.cities.filter(func(c):return c.port and not c.blockaded and EconomyRules.building_level(c,"port")>0 and (c.owner_id==owner or (StateAccess.allied(state,owner,c.owner_id) and StateAccess.relation(state,owner,c.owner_id).get("supply",false))))
	var seeds={};var coverage={}
	for city in ports:
		for dir in HexGrid.DIRECTIONS:
			var h=HexGrid.coordinate(city.position)+dir;var cell=StateAccess.cell(state,h)
			if not cell.is_empty() and (content.definition("terrains",cell.terrain_id).water or cell.get("water_under_bridge",false)):
				var key=HexGrid.key(h);seeds[key]=city.id;coverage[key]=true
	var visited={};var probe={"owner_id":owner,"def_id":"river_gunboat"}
	if ports.size()<2:return coverage
	for seed in seeds:
		if visited.has(seed):continue
		var component=[];var connected_ports={};var open: Array=[HexGrid.from_key(seed)];visited[seed]=true
		while not open.is_empty():
			var current=open.pop_front();var key=HexGrid.key(current);component.append(key)
			if seeds.has(key):connected_ports[seeds[key]]=true
			for dir in HexGrid.DIRECTIONS:
				var next=current+dir;var nk=HexGrid.key(next);var cell=StateAccess.cell(state,next)
				if visited.has(nk) or cell.is_empty() or cell.region_id=="restricted":continue
				if not (content.definition("terrains",cell.terrain_id).water or cell.get("water_under_bridge",false)):continue
				var enemy=StateAccess.at(state,"units",next)
				if not enemy.is_empty() and not StateAccess.allied(state,owner,enemy.owner_id):continue
				if MovementRules.adjacent_hostile(state,probe,next,content,false):continue
				visited[nk]=true;open.append(next)
		if connected_ports.size()>=2:
			for key in component:coverage[key]=true
	return coverage

static func distribute(state: Dictionary, owner: String, content: ContentRegistry, events: Array) -> void:
	var coverage=supply_reach(state,owner,content)
	var troops=state.units.filter(func(u):return u.owner_id==owner)
	var needs_naval=troops.any(func(u):return u.cargo_parent_id!=null or (u.position!=null and MovementRules.domain_of(u,content)!="land"))
	var naval_coverage=naval_supply_reach(state,owner,content) if needs_naval else {}
	troops.sort_custom(func(a,b):
		if a.supply_priority!=b.supply_priority:return a.supply_priority>b.supply_priority
		var da=int(coverage.get(HexGrid.key(HexGrid.coordinate(a.position)),100000)) if a.position!=null else 100000
		var db=int(coverage.get(HexGrid.key(HexGrid.coordinate(b.position)),100000)) if b.position!=null else 100000
		return da<db if da!=db else str(a.id)<str(b.id))
	for u in troops:
		var prior_supply=u.supply_state
		var pos=u.position
		if u.cargo_parent_id!=null:
			var ship=StateAccess.find(state,"units",u.cargo_parent_id);pos=ship.get("position")
		var connected=pos!=null and coverage.has(HexGrid.key(HexGrid.coordinate(pos)))
		if pos!=null and (MovementRules.domain_of(u,content)!="land" or u.cargo_parent_id!=null):
			connected=naval_coverage.has(HexGrid.key(HexGrid.coordinate(pos)))
			for city in state.cities:
				if city.owner_id==owner and city.port and not city.blockaded and EconomyRules.building_level(city,"port")>0 and HexGrid.distance(HexGrid.coordinate(city.position),HexGrid.coordinate(pos))<=2:connected=true
		var d=EffectRules.scaled_definition(u,content)
		var reduction=EffectRules.technology(state,owner,"food_upkeep_reduction",u,content)+EffectRules.general_bonus(state,u,"food_upkeep_reduction",content)
		var food=int(EffectRules.reduced_cost({"food":int(d.upkeep.food)*u.stack},reduction).food)
		if state.weather.current=="snow":food+=u.stack
		var fed=connected and StateAccess.pay(state,owner,{"food":food},events,"粮食补给")
		if fed:
			u.supply_state="FULL";u.food_reserve=3+EffectRules.technology(state,owner,"reserve_cap_flat",u,content);u.unsupplied_own_phases=0
			if prior_supply=="NONE" and owner==state.player_faction_id:state.metrics.formations_restored_from_none=int(state.metrics.get("formations_restored_from_none",0))+1
		else:
			u.supply_state="FULL" if u.food_reserve>=2 else ("LOW" if u.food_reserve==1 else "NONE")
			u.food_reserve=maxi(0,u.food_reserve-1)
			u.unsupplied_own_phases=u.unsupplied_own_phases+1 if u.supply_state=="NONE" else 0
			if u.supply_state=="NONE":u.morale=maxi(0,u.morale-8)
		var cut=u.get("rail_supply_cut",{})
		if not cut.is_empty():
			if connected or not StateAccess.hostile(state,cut.cut_by,owner):u.erase("rail_supply_cut")
			elif ["NONE","LOW","FULL"].find(u.supply_state)<["NONE","LOW","FULL"].find(cut.prior_supply):
				if cut.cut_by==state.player_faction_id:state.metrics.rail_cut_changed_enemy_supply=int(state.metrics.get("rail_cut_changed_enemy_supply",0))+1
				events.append({"type":"EnemySupplyCut","owner_id":cut.cut_by,"unit_id":u.id,"prior_supply":cut.prior_supply,"supply_state":u.supply_state});u.erase("rail_supply_cut")
		if connected:
			var price=EffectRules.reduced_cost({"arms":int(d.ammo_refill_arms)},EffectRules.technology(state,owner,"ammo_refill_reduction",u,content)).arms
			price*=u.stack
			while u.ammo<int(d.ammo_capacity) and price>0 and StateAccess.pay(state,owner,{"arms":price},events,"弹药补充"):u.ammo+=1
		if u.unsupplied_own_phases>=2:
			var loss=maxi(1,int(u.max_hp*80/1000));u.hp-=loss
			events.append({"type":"Attrition","unit_id":u.id,"amount":loss})
			if u.hp<=0:CombatRules.defeat(state,u,events,content);continue
		if fed and u.position!=null:
			var healing=0
			for c in state.cities:
				if c.owner_id==owner and HexGrid.distance(HexGrid.coordinate(c.position),HexGrid.coordinate(u.position))<=1:healing=maxi(healing,5*EconomyRules.building_level(c,"hospital"))
			healing=mini(healing,int(u.max_hp*.1));u.hp=mini(u.max_hp,u.hp+healing)
			u.morale=mini(50,u.morale+5+EffectRules.general_bonus(state,u,"morale_recovery_flat",content)) if u.morale<50 and not MovementRules.adjacent_hostile(state,u,HexGrid.coordinate(u.position),content,false) else u.morale
		u.supply_connected=connected
		if u.position!=null:
			var nearest=StateAccess.nearest_city(state,HexGrid.coordinate(u.position),owner)
			u.supply_city_id=nearest.get("id",null) if connected else null
		else:u.supply_city_id=null

static func refresh_transport(state: Dictionary, owner: String, content: ContentRegistry) -> void:
	var f=StateAccess.faction(state,owner);var pool=0
	for c in state.cities:
		if c.owner_id==owner:
			var level=EconomyRules.building_level(c,"station")
			if level>0:pool+=level+1
	f.transport_pool=mini(12,pool+EffectRules.technology(state,owner,"transport_pool_flat",{},content))

static func rail_route(state: Dictionary, owner: String, source: String, destination: String, cost: int, content: ContentRegistry, visible_only: bool = true) -> Array:
	var open: Array=[{"node":source,"path":[]}];var visited={source:true}
	while not open.is_empty():
		var now=open.pop_front()
		if now.node==destination:return now.path
		if now.path.size()>=12:continue
		for e in state.map.rail_edges:
			if e.damage!="intact" or not MovementRules.rail_available(state,e) or e.capacity_left<cost:continue
			var next=e.node_b if e.node_a==now.node else (e.node_a if e.node_b==now.node else "")
			if next.is_empty() or visited.has(next):continue
			var c=StateAccess.find(state,"cities",next)
			if c.is_empty() or EconomyRules.building_level(c,"station")==0:continue
			var rel=StateAccess.relation(state,owner,c.owner_id)
			if c.owner_id!=owner and not (rel.state=="ALLIANCE" and rel.passage):continue
			var safe=true
			for p in e.path_hexes:
				var probe={"owner_id":owner,"position":p}
				if MovementRules.adjacent_hostile(state,probe,HexGrid.coordinate(p),content,visible_only):safe=false;break
			if not safe:continue
			visited[next]=true;var path=now.path.duplicate();path.append(e.id);open.append({"node":next,"path":path})
	return []

static func rail_cost(state: Dictionary, u: Dictionary, content: ContentRegistry) -> int:
	var d=content.definition("units",u.def_id)
	return maxi(1,int(u.stack)+int(d.transport_extra)-EffectRules.status_bonus(state,u,"transport_cost_reduction"))

static func demolish(state: Dictionary, edge: Dictionary, owner: String, content: ContentRegistry, events: Array) -> void:
	var supplied={}
	for faction in state.factions:
		if faction.eliminated or not StateAccess.hostile(state,owner,faction.id):continue
		var coverage=supply_reach(state,faction.id,content)
		for unit in state.units:
			if unit.owner_id==faction.id and unit.position!=null and unit.cargo_parent_id==null and unit.supply_state!="NONE" and MovementRules.domain_of(unit,content)=="land" and coverage.has(HexGrid.key(HexGrid.coordinate(unit.position))):supplied[unit.id]=true
	edge.damage="broken";edge.capacity_left=0;MovementRules.invalidate_rail_cache()
	for faction in state.factions:
		if faction.eliminated or not StateAccess.hostile(state,owner,faction.id):continue
		var coverage=supply_reach(state,faction.id,content)
		for unit in state.units:
			if supplied.has(unit.id) and unit.owner_id==faction.id and not coverage.has(HexGrid.key(HexGrid.coordinate(unit.position))):
				unit.rail_supply_cut={"cut_by":owner,"prior_supply":unit.supply_state,"cut_at_version":state.state_version}
	events.append({"type":"RailDemolished","edge_id":edge.id,"owner_id":owner})

static func transport(state: Dictionary, u: Dictionary, destination: Dictionary, route: Array, content: ContentRegistry, events: Array) -> void:
	var cost=rail_cost(state,u,content)
	StateAccess.faction(state,u.owner_id).transport_pool-=cost
	StateAccess.faction(state,u.owner_id).transport_used_phase=true
	for id in route:
		for e in state.map.rail_edges:
			if e.id==id:e.capacity_left-=cost
	var from=u.position.duplicate();u.position=destination.position.duplicate();u.ap_left=0;u.attack_ready=false;u.transported_this_phase=true;u.moved_this_phase=true
	StateAccess.invalidate_occupancy()
	events.append({"type":"RailTransported","unit_id":u.id,"from":from,"position":u.position,"route":route,"cost":cost})

static func process_jobs(state: Dictionary, owner: String, content: ContentRegistry, events: Array) -> void:
	for job in state.engineer_jobs.duplicate():
		if job.owner_id!=owner:continue
		var u=StateAccess.find(state,"units",job.unit_id)
		if u.is_empty():
			var refund={}
			for key in job.paid_cost:refund[key]=int(job.paid_cost[key]*job.remaining_own_phases/maxi(1,job.total_own_phases)*.5)
			StateAccess.add_resources(state,owner,refund,events,"工兵损失退款");state.engineer_jobs.erase(job);continue
		var edge={}
		for e in state.map.rail_edges:
			if e.id==job.edge_id:edge=e
		if edge.is_empty() or u.position==null:continue
		var adjacent=edge.path_hexes.any(func(p):return HexGrid.distance(HexGrid.coordinate(p),HexGrid.coordinate(u.position))<=1)
		if not adjacent:job.paused=true;continue
		job.paused=false;job.remaining_own_phases-=1
		if job.remaining_own_phases<=0:
			edge.damage="intact";edge.capacity_left=edge.capacity_max;state.engineer_jobs.erase(job)
			events.append({"type":"RailRepaired","edge_id":edge.id,"unit_id":u.id,"owner_id":owner})
			if edge.is_bridge and owner==state.player_faction_id:state.metrics.bridges_repaired=int(state.metrics.get("bridges_repaired",0))+1
	MovementRules.invalidate_rail_cache()
