class_name SnapshotReferenceAccess023
extends RefCounted
const ReferenceContext=preload("res://tests/fixtures/reference_cache_v023.gd")

static func invalidate_occupancy() -> void:
	var cache=ReferenceContext.current()
	cache.occupancy_sources.clear();cache.occupancy_indexes.clear()

static func find(state: Dictionary, group: String, id: String) -> Dictionary:
	for record in state.get(group, []):
		if record.id == id:
			return record
	return {}

static func at(state: Dictionary, group: String, hex: Vector2i, cache: RulesQueryCache = null) -> Dictionary:
	if cache==null:cache=ReferenceContext.current()
	var records=state.get(group,[])
	if not cache.occupancy_sources.has(group) or not is_same(cache.occupancy_sources[group],records):
		cache.occupancy_sources[group]=records;var index={}
		for record in records:
			if record.get("position")!=null:index[HexGrid.key(HexGrid.coordinate(record.position))]=record
		cache.occupancy_indexes[group]=index
	return cache.occupancy_indexes[group].get(HexGrid.key(hex),{})

static func cell(state: Dictionary, hex: Vector2i, cache: RulesQueryCache = null) -> Dictionary:
	if cache==null:cache=ReferenceContext.current()
	if not is_same(cache.last_cells, state.map.cells):
		cache.last_cells=state.map.cells
		cache.cell_index.clear();cache.cell_offsets.clear()
		for index in range(cache.last_cells.size()):
			var record=cache.last_cells[index];var key=HexGrid.key(HexGrid.coordinate(record.position))
			cache.cell_index[key]=record;cache.cell_offsets[key]=index
	return cache.cell_index.get(HexGrid.key(hex), {})

static func freeze_value(value: Variant) -> void:
	if value is Array or value is Dictionary:
		if value.is_read_only():return
		if value is Array:
			for child in value:freeze_value(child)
		else:
			for key in value:freeze_value(value[key])
		value.make_read_only()

static func freeze_map(map: Dictionary) -> void:
	# Geometry and cells stay immutable between commands. Historical restrictions
	# use mutable_cell(); capacities and reference POIs are always copied.
	for key in map:
		if key not in ["rail_edges","reference_pois","dynamic_cell_offsets"]:freeze_value(map[key])

static func clone_transaction(state: Dictionary) -> Dictionary:
	var next=state.duplicate(false)
	for key in state:
		var value=state[key]
		if key=="map":
			next.map=value.duplicate(false)
			for field in value:
				var geometry=value[field]
				if (geometry is Array or geometry is Dictionary) and not geometry.is_read_only():next.map[field]=geometry.duplicate(true)
		elif key=="visibility":
			next[key]=[]
			for sight in value:
				var copied=sight.duplicate(false)
				for field in sight:
					var entry=sight[field]
					if (entry is Array or entry is Dictionary) and not entry.is_read_only():copied[field]=entry.duplicate(true)
				next[key].append(copied)
		elif value is Array or value is Dictionary:next[key]=value.duplicate(true)
	return next

static func mutable_cell(state: Dictionary, hex: Vector2i) -> Dictionary:
	if state.map.cells.is_read_only():state.map.cells=state.map.cells.duplicate(false)
	var record=cell(state,hex)
	if not record.is_empty() and record.is_read_only():
		record=record.duplicate(true)
		var cache=ReferenceContext.current()
		var key=HexGrid.key(hex);state.map.cells[cache.cell_offsets[key]]=record;cache.cell_index[key]=record
	if not record.is_empty() and state.map.has("dynamic_cell_offsets"):
		var cache=ReferenceContext.current()
		state.map.dynamic_cell_offsets[str(cache.cell_offsets[HexGrid.key(hex)])]=true
	return record

static func faction(state: Dictionary, id: String) -> Dictionary:
	return find(state, "factions", id)

static func faction_name(state: Dictionary, id: String, content: ContentRegistry) -> String:
	return faction(state,id).get("name_override",content.definition("factions",id).get("name",id))

static func relation(state: Dictionary, a: String, b: String) -> Dictionary:
	if a == b:
		return {"state":"SELF","passage":true,"supply":true}
	for record in state.relations:
		if (record.faction_a == a and record.faction_b == b) or (record.faction_a == b and record.faction_b == a):
			return record
	return {"state":"NEUTRAL","passage":false,"supply":false}

static func hostile(state: Dictionary, a: String, b: String) -> bool:
	return relation(state, a, b).state == "WAR"

static func allied(state: Dictionary, a: String, b: String) -> bool:
	return a == b or relation(state, a, b).state == "ALLIANCE"

static func pay(state: Dictionary, owner: String, cost: Dictionary, events: Array, reason: String) -> bool:
	var resources = faction(state, owner).resources
	for resource in cost:
		if resources.get(resource, 0) < int(cost[resource]):
			return false
	for resource in cost:
		var before = int(resources.get(resource, 0))
		resources[resource] = before - int(cost[resource])
		if cost[resource] != 0:
			events.append({"type":"ResourceChanged","owner_id":owner,"resource":resource,
				"before":before,"delta":-int(cost[resource]),"after":resources[resource],"reason":reason})
	return true

static func add_resources(state: Dictionary, owner: String, amount: Dictionary, events: Array, reason: String) -> void:
	var resources = faction(state, owner).resources
	for resource in amount:
		var before = int(resources.get(resource, 0))
		resources[resource] = before + int(amount[resource])
		events.append({"type":"ResourceChanged","owner_id":owner,"resource":resource,
			"before":before,"delta":int(amount[resource]),"after":resources[resource],"reason":reason})

static func can_pay(state: Dictionary, owner: String, cost: Dictionary) -> bool:
	var f = faction(state, owner)
	if f.is_empty():
		return false
	for resource in cost:
		if int(f.resources.get(resource, 0)) < int(cost[resource]):
			return false
	return true

static func remove_by_id(state: Dictionary, group: String, id: String) -> void:
	for i in range(state[group].size()-1, -1, -1):
		if state[group][i].id == id:
			state[group].remove_at(i)
			invalidate_occupancy()
			return

static func nearest_city(state: Dictionary, hex: Vector2i, owner: String = "") -> Dictionary:
	var best: Dictionary = {}
	var best_distance: int = 1000000
	for city in state.cities:
		if not owner.is_empty() and city.owner_id != owner:
			continue
		var d = HexGrid.distance(hex, HexGrid.coordinate(city.position))
		if d < best_distance or (d == best_distance and str(city.id) < str(best.get("id","~"))):
			best = city
			best_distance = d
	return best

static func count_units(state: Dictionary, owner: String, definition: String, elite: Variant = null) -> int:
	var count: int = 0
	for unit in state.units:
		if unit.owner_id == owner and unit.def_id == definition and unit.elite_id == elite:
			count += 1
	for city in state.cities:
		if city.owner_id == owner:
			for queued in city.recruit_queue:
				if queued.target_def_id == definition and queued.get("elite_id") == elite:
					count += 1
	return count
