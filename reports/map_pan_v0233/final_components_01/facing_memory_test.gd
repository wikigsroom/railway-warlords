extends SceneTree

var checks: Array=[]
var failures: Array=[]
func _init() -> void:run.call_deferred()
func verify(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:failures.append(name);push_error(name)

func run() -> void:
	var content=ContentRegistry.new();verify(content.load_all(),"published_content_loaded")
	var state=StateBuilder.create(content,"campaign_1920_01","zhili",{})
	var kernel=CommandKernel.new(content);var issued={};var unit={}
	for candidate in state.units:
		if candidate.owner_id!=state.player_faction_id or candidate.position==null:continue
		var graph=MovementRules.reachable(state,candidate,content)
		for key in graph.costs:
			var target=HexGrid.from_key(key);var route=MovementRules.route_from_graph(graph,HexGrid.coordinate(candidate.position),target)
			if route.size()<2 or route[-1]-route[-2]!=Vector2i(0,-1):continue
			var c=VisualPlaytest.command(state,"Move",{"unit_id":candidate.id,"target_hex":HexGrid.position(target)})
			if kernel.preview(state,c).valid:issued=c;unit=candidate;break
		if not issued.is_empty():break
	verify(not issued.is_empty(),"legal_northbound_published_unit_found")
	if issued.is_empty():quit(1);return
	var result=kernel.resolve(state,issued);var memory=FacingMemory.new();memory.reset(state)
	var committed=ContentRegistry.fingerprint(result.state)
	memory.commit(result.state,result.events,state)
	verify(memory.vectors().get(unit.id,Vector2.ZERO).dot(Vector2.UP)>.99,"legal_north_move_records_rear_view_heading")
	verify(ContentRegistry.fingerprint(result.state)==committed,"presentation_commit_keeps_complete_rules_state_and_rng")
	var aged=StateAccess.clone_transaction(result.state)
	# Isolated log-aging fixture, not a fabricated claim of 300 native turns.
	for i in range(300):
		var note={"type":"LogAgingFixture","sequence":aged.state_version+i+1}
		aged.event_log.append(note)
		while aged.event_log.size()>250:aged.event_log.pop_front()
		memory.commit(aged,[note])
	verify(not aged.event_log.any(func(event):return event.type=="UnitMoved"),"movement_event_has_left_250_entry_battle_log")
	var save=SaveService.new("user://qa/facing_memory_%d"%Time.get_ticks_usec(),content)
	var aged_hash=ContentRegistry.fingerprint(aged)
	verify(save.write("test",aged,content.content_hash,{"facing":memory.snapshot()}),"independent_visual_ledger_written_atomically")
	var loaded=save.load_slot("test",content.content_hash);var restored=FacingMemory.new();restored.reset(loaded,save.last_presentation.get("facing",{}))
	verify(ContentRegistry.fingerprint(loaded)==aged_hash,"save_load_keeps_exact_rules_payload")
	verify(restored.snapshot()==memory.snapshot() and restored.vectors()[unit.id].dot(Vector2.UP)>.99,"heading_survives_save_after_log_truncation")
	var view=MapView.new();view.restore_headings(restored);view.update_unit_headings(loaded,[])
	verify(view.unit_headings[unit.id].dot(Vector2.UP)>.99,"native_map_hydrates_persistent_heading")
	view.free()
	verify(save.write("test",aged,content.content_hash),"legacy_save_without_visual_metadata_still_supported")
	loaded=save.load_slot("test",content.content_hash)
	verify(not loaded.is_empty() and save.last_presentation.is_empty(),"legacy_load_clears_previous_visual_metadata")
	verify(save.write("test",aged,content.content_hash,{"facing":memory.snapshot()}),"second_atomic_save_preserves_backup")
	var envelope=JSON.parse_string(FileAccess.get_file_as_string(save.path_for("test")));envelope.presentation.facing.headings[unit.id]=[1000,0]
	var file=FileAccess.open(save.path_for("test"),FileAccess.WRITE);file.store_string(JSON.stringify(envelope));file.close()
	loaded=save.load_slot("test",content.content_hash)
	verify(not loaded.is_empty() and save.last_presentation.is_empty(),"tampered_visual_checksum_recovers_verified_backup")
	var other=StateBuilder.create(content,"campaign_1924_03","zhili",{});restored.reset(other,memory.snapshot())
	verify(restored.headings.is_empty(),"another_match_cannot_inherit_stale_unit_ids")
	var undo_command=VisualPlaytest.command(result.state,"UndoMove",{})
	if kernel.preview(result.state,undo_command).valid:
		var undone=kernel.resolve(result.state,undo_command);var fresh=FacingMemory.new();fresh.reset(state);fresh.headings[unit.id]=[1000,0];fresh.commit(result.state,result.events,state);fresh.commit(undone.state,undone.events,result.state)
		verify(fresh.headings.get(unit.id)==[1000,0],"undo_move_restores_exact_pre_move_heading")
	var report={"passed":failures.is_empty(),"failed":failures.size(),"checks":checks,"failures":failures,"build_version":ContentRegistry.APP_VERSION,"content_hash":content.content_hash,"scope":"Published legal move plus explicit isolated 300-entry log-aging/corruption fixtures; no gameplay/RNG changes."}
	var output=FileAccess.open("res://reports/map_pan_v0233/final_components_01/facing_memory_tests.json",FileAccess.WRITE);output.store_string(JSON.stringify(report,"\t"));output.close()
	print("FACING_MEMORY_TEST ",checks.size()," checks / ",failures.size()," failures");quit(0 if failures.is_empty() else 1)
