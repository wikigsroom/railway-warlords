extends SceneTree

var checks: Array=[]
var failures: Array=[]
func _init() -> void:run.call_deferred()
func verify(ok: bool, name: String) -> void:
	checks.append({"name":name,"passed":ok})
	if not ok:failures.append(name);push_error(name)
func compare(state: Dictionary, unit: Dictionary, content: ContentRegistry, name: String) -> void:
	var actual=MovementRules.reachable(state,unit,content)
	var reference=CapacityReferenceMovement020.reachable(state,unit,content)
	verify(actual==reference,name+"_ordered_paths_and_costs_match_archived_algorithm")

func run() -> void:
	var content=ContentRegistry.new();verify(content.load_all(),"current_production_loaded")
	verify(content.tables.is_read_only() and content.definition("terrains","plain").is_read_only(),"published_definition_tables_are_recursively_immutable")
	var state=StateBuilder.create(content,"campaign_1924_02","fengtian",{})
	var unit=state.units.filter(func(u):return u.owner_id==state.player_faction_id)[0]
	compare(state,unit,content,"first_query")
	compare(state,unit,content,"repeated_query")
	var graph=MovementRules.reachable(state,unit,content);graph.costs.clear();graph.previous.clear()
	compare(state,unit,content,"returned_graph_edits_cannot_change_validation")
	var visibility_state=StateAccess.clone_transaction(state)
	var visibility_unit=StateAccess.find(visibility_state,"units",unit.id)
	var visibility_enemy=visibility_state.units.filter(func(u):return u.position!=null and StateAccess.hostile(visibility_state,visibility_unit.owner_id,u.owner_id))[0]
	# Isolated visibility fixture on real map cells; no historical deployment claim.
	visibility_state.units=[visibility_unit,visibility_enemy];visibility_unit.def_id="rifle";visibility_unit.ap_left=4
	var neighbor_key=""
	for cell in visibility_state.map.cells:
		if cell.terrain_id!="plain" or cell.region_id=="restricted" or cell.get("water_under_bridge",false):continue
		for direction in HexGrid.DIRECTIONS:
			var adjacent=HexGrid.coordinate(cell.position)+direction;var next_cell=StateAccess.cell(visibility_state,adjacent)
			if next_cell.get("terrain_id")!="plain" or next_cell.get("region_id")=="restricted" or next_cell.get("water_under_bridge",false) or not StateAccess.at(visibility_state,"cities",adjacent).is_empty():continue
			visibility_unit.position=cell.position.duplicate();neighbor_key=HexGrid.key(adjacent);break
		if not neighbor_key.is_empty():break
	verify(not neighbor_key.is_empty(),"visibility_regression_has_reachable_neighbor")
	if not neighbor_key.is_empty():
		visibility_enemy.position=HexGrid.position(HexGrid.from_key(neighbor_key));StateAccess.invalidate_occupancy()
		var enemy_cell=StateAccess.cell(visibility_state,HexGrid.from_key(neighbor_key))
		var sight=visibility_state.visibility.filter(func(s):return s.faction_id==visibility_unit.owner_id)[0]
		sight.visible_cell_ids=sight.visible_cell_ids.duplicate()
		if not sight.visible_cell_ids.has(enemy_cell.id):sight.visible_cell_ids.append(enemy_cell.id)
		var visible_graph=MovementRules.reachable(visibility_state,visibility_unit,content)
		sight.visible_cell_ids=sight.visible_cell_ids.duplicate();sight.visible_cell_ids.erase(enemy_cell.id)
		compare(visibility_state,visibility_unit,content,"visibility_change_without_a_version_increment")
		var hidden_graph=MovementRules.reachable(visibility_state,visibility_unit,content)
		verify(not visible_graph.costs.has(neighbor_key) and hidden_graph.costs.has(neighbor_key),"hidden_enemy_changes_legal_destination")
	unit.ap_left=1
	compare(state,unit,content,"ap_change_on_the_same_state")
	unit.ap_left=4
	var other=state.units.filter(func(u):return u.id!=unit.id and u.position!=null)[0]
	other.position=HexGrid.position(HexGrid.coordinate(unit.position)+HexGrid.DIRECTIONS[0]);StateAccess.invalidate_occupancy()
	compare(state,unit,content,"occupant_change_without_a_version_increment")
	# An explicit editor copy keeps the original in-place mutation regression.
	content.tables=content.tables.duplicate(true)
	for table in content.tables:
		if content.tables[table] is Array:
			var index={}
			for record in content.tables[table]:
				if record is Dictionary and record.has("id"):index[record.id]=record
			content.indexes[table]=index
	content.rules=content.tables.rules
	var plain=content.definition("terrains","plain");var original_cost=plain.cost_foot;plain.cost_foot+=1
	compare(state,unit,content,"definition_change_on_the_same_registry")
	plain.cost_foot=original_cost
	state.map.crossings=state.map.crossings.duplicate(true)
	if not state.map.crossings.is_empty():state.map.crossings[0].intact=false
	compare(state,unit,content,"mutable_crossing_change")
	state.map.cells=state.map.cells.duplicate(true)
	var cell=StateAccess.cell(state,HexGrid.coordinate(unit.position));cell.terrain_id="forest"
	compare(state,unit,content,"mutable_geometry_bypasses_reuse")
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"content_hash":content.content_hash,"game_version":ContentRegistry.APP_VERSION,"reference_version":"0.2.0"}
	var file=FileAccess.open("res://reports/movement_cache_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("MOVEMENT_CACHE_TESTS ",JSON.stringify({"passed":report.passed,"checks":checks.size(),"failures":failures}));quit(0 if failures.is_empty() else 1)
