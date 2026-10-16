extends SceneTree

var content=ContentRegistry.new()
var passed: Array=[]
var failed: Array=[]
func _init() -> void:run.call_deferred()
func check(ok: bool, name: String) -> void:
	if ok:passed.append(name)
	else:failed.append(name);push_error("FAIL: "+name)
func command(s: Dictionary, type: String) -> Dictionary:return {"type":type,"actor_id":s.turn_order[s.phase_index],"expected_version":s.state_version}
func run() -> void:
	check(content.load_all(),"content_loaded");var kernel=CommandKernel.new(content)
	var state=StateBuilder.create(content,"conq_1922","zhili",{})
	check(state.map.cells.is_read_only() and state.map.admin_layers.is_read_only(),"real_geometry_recursively_frozen")
	var clone=StateAccess.clone_transaction(state)
	check(is_same(clone.map.cells,state.map.cells) and is_same(clone.map.admin_layers,state.map.admin_layers),"immutable_geometry_shared")
	check(not is_same(clone.units,state.units) and not is_same(clone.cities,state.cities) and not is_same(clone.map.rail_edges,state.map.rail_edges),"all_dynamic_groups_copied")
	var checksum=ContentRegistry.fingerprint(state)
	clone.units[0].hp-=1;clone.cities[0].stability=30;clone.map.rail_edges[0].damage="broken"
	check(ContentRegistry.fingerprint(state)==checksum,"dynamic_edits_leave_source_state_unchanged")
	var qingdao=state.map.reference_pois.filter(func(c):return c.id=="qingdao")[0]
	var original_cell=StateAccess.cell(state,HexGrid.coordinate(qingdao.position))
	StateAccess.mutable_cell(clone,HexGrid.coordinate(qingdao.position)).region_id="theater"
	check(original_cell.region_id=="restricted" and StateAccess.cell(clone,HexGrid.coordinate(qingdao.position)).region_id=="theater","copy_on_write_historical_cell_isolation")
	state.date="1922-12-09";state.phase_index=state.turn_order.size()-1
	checksum=ContentRegistry.fingerprint(state);var result=kernel.resolve(state,command(state,"EndPhase"))
	check(result.valid and ContentRegistry.fingerprint(state)==checksum,"qingdao_event_does_not_mutate_input_snapshot")
	if result.valid:
		check(result.state.cities.any(func(c):return c.id=="qingdao") and not state.cities.any(func(c):return c.id=="qingdao"),"historical_city_activation_commits_only_to_new_snapshot")
		check(result.state.map.cells.is_read_only(),"changed_cells_refrozen_after_commit")
	var legacy=StateAccess.clone_transaction(state);legacy.map.cells=[];legacy.map.cells.append({"id":"c","position":{"q":0,"r":0},"terrain_id":"plain","region_id":"theater"})
	var editable=StateAccess.clone_transaction(legacy);editable.map.cells[0].terrain_id="forest"
	check(legacy.map.cells[0].terrain_id=="plain","mutable_test_and_import_maps_still_deep_copied")
	var storage=SaveService.new("user://transaction_%d"%Time.get_ticks_usec());check(storage.write("test",state,content.content_hash),"snapshot_save_passes_checksum")
	var loaded=storage.load_slot("test",content.content_hash)
	check(loaded.map.cells.is_read_only() and ContentRegistry.fingerprint(loaded)==ContentRegistry.fingerprint(state),"loaded_geometry_frozen_without_changing_payload")
	# Compare the former full duplication with the transaction copy on the same real map.
	var old_ms: Array=[];var new_ms: Array=[]
	for i in range(30):
		var start=Time.get_ticks_usec();var full=state.duplicate(true);old_ms.append((Time.get_ticks_usec()-start)/1000.0)
		start=Time.get_ticks_usec();var current=StateAccess.clone_transaction(state);new_ms.append((Time.get_ticks_usec()-start)/1000.0)
		if i==0:check(ContentRegistry.fingerprint(full)==ContentRegistry.fingerprint(current),"transaction_copy_has_identical_serialized_payload")
	old_ms.sort();new_ms.sort()
	var report={"passed":passed.size(),"failed":failed.size(),"checks":passed,"failures":failed,"content_hash":content.content_hash,"samples":30,"full_duplicate_ms_median":old_ms[15],"transaction_copy_ms_median":new_ms[15],"full_duplicate_ms_p95":old_ms[28],"transaction_copy_ms_p95":new_ms[28],"measurement":"Native Godot real conquest state copy; not whole AI phase or Android performance."}
	var file=FileAccess.open("res://reports/transaction_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close();print("TRANSACTION_TESTS ",JSON.stringify(report));quit(0 if failed.is_empty() else 1)
