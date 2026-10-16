class_name CapacityReferenceVisibility
extends RefCounted

static func unit_visible(state: Dictionary, observer: String, unit: Dictionary) -> bool:
	if unit.owner_id==observer or StateAccess.allied(state,observer,unit.owner_id):
		return true
	if unit.position==null:
		return false
	for sight in state.visibility:
		if sight.faction_id==observer:
			var cell=StateAccess.cell(state,HexGrid.coordinate(unit.position))
			return sight.visible_cell_ids.has(cell.get("id",""))
	return false

static func hex_visible(state: Dictionary, observer: String, hex: Vector2i) -> bool:
	var cell=StateAccess.cell(state,hex)
	if cell.is_empty():
		return false
	for sight in state.visibility:
		if sight.faction_id==observer:
			return sight.visible_cell_ids.has(cell.id)
	return false

static func clear_line(state: Dictionary, from: Vector2i, to: Vector2i) -> bool:
	var line=HexGrid.line(from,to)
	for i in range(1,line.size()-1):
		var cell=StateAccess.cell(state,line[i])
		if not cell.is_empty() and cell.terrain_id in ["peak","forest"]:
			return false
	return true

static func refresh(state: Dictionary, content: ContentRegistry) -> void:
	var scenario=content.scenarios.get(state.scenario_id,{})
	var full=scenario.get("full_visibility",false)
	for faction in state.factions:
		var sight: Dictionary = {}
		for record in state.visibility:
			if record.faction_id==faction.id:
				sight=record
		if sight.is_empty():
			sight={"faction_id":faction.id,"visible_cell_ids":[],"explored_cell_ids":[],"last_seen":[],"temporary_reveals":[]}
			state.visibility.append(sight)
		var visible: Dictionary = {}
		var sources: Array = []
		for unit in state.units:
			if unit.position!=null and unit.owner_id==faction.id:
				var definition=content.definition("units",unit.def_id)
				var radius=3 if definition.movement_profile in ["cavalry","motor"] else 2
				radius+=EffectRules.technology(state,faction.id,"vision_flat",unit,content)
				sources.append({"position":unit.position,"radius":radius})
		for city in state.cities:
			if city.owner_id==faction.id:
				sources.append({"position":city.position,"radius":2})
		for reveal in sight.temporary_reveals:
			if reveal.expires_owner_phase>faction.own_phase_index:
				sources.append({"position":reveal.center,"radius":reveal.radius})
		if full:
			for cell in state.map.cells:visible[cell.id]=true
		else:
			for source in sources:
				var origin=HexGrid.coordinate(source.position);var radius=int(source.radius)
				for q in range(origin.x-radius,origin.x+radius+1):
					for r in range(origin.y-radius,origin.y+radius+1):
						var hex=Vector2i(q,r)
						if HexGrid.distance(origin,hex)>radius:continue
						var cell=StateAccess.cell(state,hex)
						if not cell.is_empty() and not visible.has(cell.id) and clear_line(state,origin,hex):visible[cell.id]=true
		sight.visible_cell_ids=visible.keys()
		for id in sight.visible_cell_ids:
			if not sight.explored_cell_ids.has(id):
				sight.explored_cell_ids.append(id)
		sight.temporary_reveals=sight.temporary_reveals.filter(func(r):return r.expires_owner_phase>faction.own_phase_index)
	for relation in state.relations:
		if relation.state=="ALLIANCE":
			var a:Dictionary={}
			var b:Dictionary={}
			for sight in state.visibility:
				if sight.faction_id==relation.faction_a:a=sight
				if sight.faction_id==relation.faction_b:b=sight
			if not a.is_empty() and not b.is_empty():
				var shared=a.visible_cell_ids.duplicate()
				for id in b.visible_cell_ids:
					if not shared.has(id):shared.append(id)
				a.visible_cell_ids=shared.duplicate()
				b.visible_cell_ids=shared.duplicate()
	for sight in state.visibility:
		for unit in state.units:
			if unit.owner_id==sight.faction_id or unit.position==null or not unit_visible(state,sight.faction_id,unit):continue
			var old=sight.last_seen.filter(func(x):return x.unit_id==unit.id)
			if old.is_empty():sight.last_seen.append({"unit_id":unit.id,"position":unit.position.duplicate(),"def_id":unit.def_id,"owner_id":unit.owner_id,"round":state.round})
			else:old[0].position=unit.position.duplicate();old[0].round=state.round
