class_name CapacityReferenceMovement020
extends RefCounted

static var _rail_source: Array=[]
static var _rail_date=""
static var _rail_version=-1
static var _rail_links: Dictionary={}

static func domain_of(unit: Dictionary, content: ContentRegistry) -> String:
	var profile = content.definition("units",unit.def_id).movement_profile
	return "sea" if profile in ["water","sea"] else ("river" if profile=="river" else "land")

static func adjacent_hostile(state: Dictionary, unit: Dictionary, hex: Vector2i, content: ContentRegistry, visible_only: bool = true) -> bool:
	var from_cell=StateAccess.cell(state,hex)
	if from_cell.is_empty() or from_cell.terrain_id=="peak":return false
	var a=content.definition("terrains",from_cell.terrain_id)
	for direction in HexGrid.DIRECTIONS:
		var enemy_hex=hex+direction;var enemy=StateAccess.at(state,"units",enemy_hex)
		if enemy.is_empty() or not StateAccess.hostile(state,unit.owner_id,enemy.owner_id):continue
		if visible_only and not VisibilityRules.unit_visible(state,unit.owner_id,enemy):continue
		var to_cell=StateAccess.cell(state,enemy_hex)
		if to_cell.is_empty() or to_cell.terrain_id=="peak":continue
		var b=content.definition("terrains",to_cell.terrain_id)
		if a.water==b.water:return true
	return false

static func rail_neighbor(state: Dictionary, a: Vector2i, b: Vector2i) -> bool:
	if not is_same(_rail_source,state.map.rail_edges) or _rail_date!=state.date or _rail_version!=int(state.state_version):
		_rail_source=state.map.rail_edges;_rail_date=state.date;_rail_version=state.state_version;_rail_links.clear()
		for edge in state.map.rail_edges:
			if edge.damage!="intact" or not rail_available(state,edge):continue
			for i in range(edge.path_hexes.size()-1):
				var x=HexGrid.coordinate(edge.path_hexes[i]);var y=HexGrid.coordinate(edge.path_hexes[i+1])
				_rail_links[HexGrid.key(x)+"/"+HexGrid.key(y)]=true;_rail_links[HexGrid.key(y)+"/"+HexGrid.key(x)]=true
	return _rail_links.has(HexGrid.key(a)+"/"+HexGrid.key(b))

static func invalidate_rail_cache() -> void:_rail_version=-1

static func rail_available(state: Dictionary, edge: Dictionary) -> bool:
	return state.date>=edge.active_from and state.date>=edge.get("military_access_from","0000-00-00")

static func crossing_cost(state: Dictionary, a: Vector2i, b: Vector2i) -> int:
	for crossing in state.map.get("crossings",[]):
		if crossing.get("intact",true) and ((HexGrid.coordinate(crossing.from)==a and HexGrid.coordinate(crossing.to)==b) or (HexGrid.coordinate(crossing.from)==b and HexGrid.coordinate(crossing.to)==a)):
			if crossing.get("kind","")=="bridge" and state.map.rail_edges.any(func(e):return e.id==crossing.get("rail_edge_id","") and e.damage!="intact"):continue
			return int(crossing.cost)
	return 0

static func step_cost(state: Dictionary, unit: Dictionary, a: Vector2i, b: Vector2i, content: ContentRegistry, visible_only: bool = true, combat_endpoint: bool = false) -> int:
	var cell=StateAccess.cell(state,b)
	if cell.is_empty() or cell.region_id=="restricted":
		return 0
	var definition=content.definition("units",unit.def_id)
	if definition.movement_profile=="rail" and not rail_neighbor(state,a,b):return 0
	var crossing=crossing_cost(state,a,b)
	if HexGrid.distance(a,b)!=1 and (crossing==0 or definition.movement_profile in ["water","river","sea"]):
		return 0
	var terrain=content.definition("terrains",cell.terrain_id)
	var profile=definition.movement_profile
	var field="cost_water" if profile in ["water","river","sea"] else "cost_"+profile
	var cost=1 if profile=="rail" else int(terrain.get(field,0))
	if cell.get("water_under_bridge",false):
		if profile in ["water","river","sea"]:cost=1
		elif profile!="rail" and crossing==0:return 0
	var from_cell=StateAccess.cell(state,a)
	if from_cell.get("water_under_bridge",false) and profile not in ["water","river","sea","rail"] and crossing==0:return 0
	if crossing>0 and profile in ["foot","cavalry","motor"]:
		cost=crossing
	if cost<=0:
		return 0
	if profile=="river" and cell.terrain_id=="sea":
		var near_land=false
		for dir in HexGrid.DIRECTIONS:
			var neighbor=StateAccess.cell(state,b+dir)
			if not neighbor.is_empty() and not content.definition("terrains",neighbor.terrain_id).water:
				near_land=true
		if not near_land:
			return 0
	var occupant=StateAccess.at(state,"units",b)
	if not occupant.is_empty() and occupant.id!=unit.id:
		if not visible_only or VisibilityRules.unit_visible(state,unit.owner_id,occupant):
			if not StateAccess.allied(state,unit.owner_id,occupant.owner_id):
				if not combat_endpoint or not StateAccess.hostile(state,unit.owner_id,occupant.owner_id):return 0
			elif adjacent_hostile(state,unit,b,content,visible_only):return 0
	var city=StateAccess.at(state,"cities",b)
	if not city.is_empty() and city.owner_id!=unit.owner_id:
		var relation=StateAccess.relation(state,unit.owner_id,city.owner_id)
		if relation.state=="WAR" and (not definition.can_occupy or (city.fort_hp>0 and not combat_endpoint)):
			return 0
		if relation.state in ["NEUTRAL","TRUCE"] and not relation.passage:
			return 0
	if state.weather.current=="rain" and profile!="rail" and not terrain.water and cell.terrain_id!="road":
		cost+=1
	if state.weather.current=="snow" and profile in ["cavalry","motor"] and cell.terrain_id=="plain":
		cost+=1
	return cost

static func neighbors(state: Dictionary, hex: Vector2i) -> Array:
	var result: Array = []
	for direction in HexGrid.DIRECTIONS:
		result.append(hex+direction)
	for crossing in state.map.get("crossings",[]):
		if HexGrid.coordinate(crossing.from)==hex:
			result.append(HexGrid.coordinate(crossing.to))
		elif HexGrid.coordinate(crossing.to)==hex:
			result.append(HexGrid.coordinate(crossing.from))
	return result

static func reachable(state: Dictionary, unit: Dictionary, content: ContentRegistry, budget: int = -1) -> Dictionary:
	if unit.position==null:
		return {"costs":{},"previous":{}}
	if budget<0:
		budget=int(unit.ap_left)
	var origin=HexGrid.coordinate(unit.position)
	var costs={HexGrid.key(origin):0}
	var previous: Dictionary={}
	var open: Array=[{"hex":origin,"cost":0}]
	while not open.is_empty():
		open.sort_custom(func(a,b):return a.cost<b.cost)
		var current=open.pop_front()
		if current.cost>int(costs[HexGrid.key(current.hex)]):
			continue
		if current.hex!=origin and adjacent_hostile(state,unit,current.hex,content):
			continue
		for next_hex in neighbors(state,current.hex):
			var step=step_cost(state,unit,current.hex,next_hex,content)
			if step<=0:
				continue
			var total=int(current.cost)+step
			var key=HexGrid.key(next_hex)
			if total>budget or total>=int(costs.get(key,1000000)):
				continue
			costs[key]=total
			previous[key]=current.hex
			open.append({"hex":next_hex,"cost":total})
	return {"costs":costs,"previous":previous}

static func counterattack_reaches(state: Dictionary, unit: Dictionary, targets: Array, content: ContentRegistry, phases: int) -> bool:
	# This is strategic reach, not a movement command: enemy cities may be combat
	# endpoints, but occupied intermediate cells remain blocked. Phase boundaries
	# refresh AP and allow departure from a zone of control after stopping there.
	if unit.position==null or unit.cargo_parent_id!=null or targets.is_empty():return false
	var ap=mini(int(content.rules.progression.ap_cap),int(content.definition("units",unit.def_id).ap)+EffectRules.technology(state,unit.owner_id,"ap_flat",unit,content))
	if ap<=0:return false
	var budget=ap*phases;var target_keys={}
	for city in targets:target_keys[HexGrid.key(HexGrid.coordinate(city.position))]=true
	var origin=HexGrid.coordinate(unit.position);var costs={HexGrid.key(origin):0}
	var open: Array=[{"hex":origin,"cost":0}]
	while not open.is_empty():
		open.sort_custom(func(a,b):return a.cost<b.cost)
		var current=open.pop_front();var current_key=HexGrid.key(current.hex)
		if current.cost!=costs[current_key]:continue
		if target_keys.has(current_key):return true
		var departure=int(current.cost)
		if departure>0 and adjacent_hostile(state,unit,current.hex,content,false):departure=int(ceil(float(departure)/ap))*ap
		for next_hex in neighbors(state,current.hex):
			var key=HexGrid.key(next_hex);var endpoint=target_keys.has(key)
			var step=step_cost(state,unit,current.hex,next_hex,content,false,endpoint)
			if step<=0 or step>ap:continue
			var start=int(current.cost) if endpoint else departure
			if start%ap+step>ap:start=int(ceil(float(start)/ap))*ap
			var total=start+step
			if total>budget or total>=int(costs.get(key,1000000)):continue
			if endpoint:return true
			costs[key]=total;open.append({"hex":next_hex,"cost":total})
	return false

static func path(state: Dictionary, unit: Dictionary, target: Vector2i, content: ContentRegistry, budget: int = -1) -> Array:
	var graph=reachable(state,unit,content,budget)
	return route_from_graph(graph,HexGrid.coordinate(unit.position),target) if unit.position!=null else []

static func route_from_graph(graph: Dictionary, origin: Vector2i, target: Vector2i) -> Array:
	if not graph.costs.has(HexGrid.key(target)):
		return []
	var route: Array=[target]
	var current=target
	while current!=origin:
		current=graph.previous[HexGrid.key(current)]
		route.push_front(current)
	return route

static func resolve_move(state: Dictionary, unit: Dictionary, route: Array, content: ContentRegistry, events: Array) -> void:
	var from=unit.position.duplicate()
	var current=HexGrid.coordinate(unit.position)
	var last_legal=current
	for i in range(1,route.size()):
		var target=route[i] if route[i] is Vector2i else HexGrid.coordinate(route[i])
		var actual=step_cost(state,unit,current,target,content,false)
		if actual<=0 or actual>unit.ap_left:
			unit.position=HexGrid.position(last_legal);unit.ap_left=0;StateAccess.invalidate_occupancy()
			for sight in state.visibility:
				if sight.faction_id==unit.owner_id:sight.temporary_reveals.append({"center":HexGrid.position(target),"radius":0,"expires_owner_phase":StateAccess.faction(state,unit.owner_id).own_phase_index+1})
			events.append({"type":"UnitContact","unit_id":unit.id,"position":HexGrid.position(target)})
			break
		var occupant=StateAccess.at(state,"units",target)
		if not occupant.is_empty() and i==route.size()-1:
			unit.position=HexGrid.position(last_legal);StateAccess.invalidate_occupancy()
			break
		unit.ap_left-=actual
		unit.facing="se" if HexGrid.to_world(target).x>=HexGrid.to_world(current).x else "sw"
		unit.position=HexGrid.position(target)
		StateAccess.invalidate_occupancy()
		current=target
		if occupant.is_empty():last_legal=target
		unit.moved_this_phase=true
		var city=StateAccess.at(state,"cities",target)
		if occupant.is_empty() and not city.is_empty() and StateAccess.hostile(state,unit.owner_id,city.owner_id):
			EconomyRules.capture_city(state,city,unit,content,events)
			break
		if adjacent_hostile(state,unit,target,content,false):
			unit.ap_left=0
			break
	if unit.moved_this_phase:
		for i in range(state.statuses.size()-1,-1,-1):
			if state.statuses[i].target_id==unit.id and state.statuses[i].def_id=="entrenched":
				state.statuses.remove_at(i)
	var traveled: Array=[]
	for step in route:
		var point=step if step is Vector2i else HexGrid.coordinate(step)
		traveled.append(HexGrid.position(point))
		if point==HexGrid.coordinate(unit.position):break
	events.append({"type":"UnitMoved","unit_id":unit.id,"from":from,"position":unit.position.duplicate(),"path":traveled})
