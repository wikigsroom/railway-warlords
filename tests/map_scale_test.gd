extends SceneTree

var content=ContentRegistry.new()
var checks: Array=[]
var failures: Array=[]
var measurements: Array=[]

func _init() -> void:run.call_deferred()

func verify(ok: bool, name: String) -> void:
	checks.append({"name":name,"passed":ok})
	if not ok:failures.append(name);push_error("MAP_SCALE: "+name)

func run() -> void:
	verify(content.load_all(),"production_resources_loaded")
	if not content.errors.is_empty():quit(1);return
	var baseline=ContentRegistry.integerize(content.read_json("res://tests/fixtures/map_scale_baseline_v022.json"))
	for old in baseline.maps:
		var map=content.maps[old.id]
		verify(map.hex_radius_px==48 and HexGrid.RADIUS==48,old.id+"_interaction_hex_radius_unchanged")
		verify(map.hex_radius_m*5==old.hex_radius_m,old.id+"_physical_distance_per_hex_divided_by_five")
		verify(map.geographic_bounds==old.geographic_bounds and map.projection==old.projection,old.id+"_real_geographic_extent_and_projection_preserved")
		verify(map.cells.size()>=old.cells*24 and map.cells.size()<=old.cells*26,old.id+"_real_grid_area_increased_about_twenty_fivefold")
		var identities={};var coordinates={};var geographic_cities=true;var scale_ok=true;var rail_ok=true
		for cell in map.cells:
			identities[cell.id]=true;coordinates[HexGrid.key(HexGrid.coordinate(cell.position))]=true
		verify(identities.size()==map.cells.size() and coordinates.size()==map.cells.size(),old.id+"_no_overlapping_or_duplicate_interaction_cells")
		for city in map.cities:
			var previous=old.cities.filter(func(c):return c.id==city.id)[0]
			for field in ["name","lon_e6","lat_e6","reference_owner","administration_by_year"]:
				geographic_cities=geographic_cities and city.get(field)==previous.get(field)
			for axis in [0,1]:scale_ok=scale_ok and absf(city.render_position[axis]-previous.render_position[axis]*5)<=.04
			geographic_cities=geographic_cities and coordinates.has(HexGrid.key(HexGrid.coordinate(city.position)))
		verify(geographic_cities,old.id+"_historical_cities_and_period_administration_kept_at_source_coordinates")
		verify(scale_ok,old.id+"_city_geographic_render_positions_fivefold_on_both_axes")
		verify(map.cells.all(func(c):return c.terrain_id=="sea" or c.region_id=="restricted" or c.elevation_m!=null),old.id+"_no_unsampled_operable_land")
		for edge in map.rail_edges:
			for i in range(edge.path_hexes.size()):
				var hex=HexGrid.coordinate(edge.path_hexes[i]);rail_ok=rail_ok and coordinates.has(HexGrid.key(hex))
				if i>0:rail_ok=rail_ok and HexGrid.distance(hex,HexGrid.coordinate(edge.path_hexes[i-1]))==1
		verify(rail_ok,old.id+"_regenerated_rail_routes_follow_adjacent_actual_cells")
	verify(content.maps.hankou.hex_radius_m==250 and content.maps.ningpu.hex_radius_m==250,"local_legion_maps_receive_the_same_fivefold_geographic_refinement")
	var step=HexGrid.to_world(Vector2i(1,0)).length()
	verify(absf(step-sqrt(3.0)*48)<.001,"screen_hex_spacing_unchanged_at_the_same_camera_zoom")
	for scenario in ["conq_1920","conq_1922","conq_1924"]:
		var state=StateBuilder.create(content,scenario,"zhili",{})
		var template=content.maps[state.map.id];var template_hash=ContentRegistry.fingerprint(template)
		verify(is_same(state.map.admin_layers,template.admin_layers) and is_same(state.map.render_land,template.render_land),scenario+"_immutable_geography_shared_between_matches")
		var storage=SaveService.new("user://qa/map_scale_%d"%Time.get_ticks_usec(),content)
		var before=ContentRegistry.fingerprint(state);var started=Time.get_ticks_usec()
		var saved=storage.write("test",state,content.content_hash);var write_ms=(Time.get_ticks_usec()-started)/1000.0
		started=Time.get_ticks_usec();var loaded=storage.load_slot("test",content.content_hash);var read_ms=(Time.get_ticks_usec()-started)/1000.0
		var bytes=FileAccess.get_file_as_bytes(storage.path_for("test")).size()
		verify(saved and not loaded.is_empty() and ContentRegistry.fingerprint(loaded)==before,scenario+"_complete_large_map_save_roundtrip")
		verify(bytes<524288,scenario+"_save_keeps_reproducible_map_reference_instead_of_repeating_geometry")
		verify(loaded.map.cells.is_read_only() and loaded.map.cells.size()==template.cells.size(),scenario+"_load_restores_all_immutable_interaction_cells")
		var changed=StateAccess.clone_transaction(state)
		var cell=changed.map.cells.filter(func(c):return c.region_id!="restricted" and c.terrain_id=="plain")[0]
		StateAccess.mutable_cell(changed,HexGrid.coordinate(cell.position)).qa_runtime_marker="saved independently"
		changed.map.rail_edges[0].damage="broken"
		changed.units[0].hp-=1
		var changed_hash=ContentRegistry.fingerprint(changed)
		verify(storage.write("test",changed,content.content_hash) and ContentRegistry.fingerprint(storage.load_slot("test",content.content_hash))==changed_hash,scenario+"_terrain_delta_rail_damage_and_units_survive_reload")
		verify(ContentRegistry.fingerprint(template)==template_hash and ContentRegistry.fingerprint(state)==before,scenario+"_save_and_runtime_changes_do_not_mutate_other_matches_or_geography")
		verify(storage.write("test",changed,content.content_hash),scenario+"_atomic_backup_created")
		var corrupt=FileAccess.open(storage.path_for("test"),FileAccess.WRITE);corrupt.store_string("partial");corrupt.close()
		verify(ContentRegistry.fingerprint(storage.load_slot("test",content.content_hash))==changed_hash,scenario+"_interrupted_write_recovers_complete_large_map_backup")
		var reference=storage.pack_map(changed,content.content_hash)
		reference.map._template_reference.content_hash="unrelated geography"
		verify(storage.unpack_map(reference,content.content_hash).is_empty(),scenario+"_different_geography_reference_rejected")
		measurements.append({"scenario_id":scenario,"cells":template.cells.size(),"save_bytes":bytes,"write_ms":write_ms,"read_ms":read_ms})
	var state=StateBuilder.create(content,"conq_1922","zhili",{});var kernel=CommandKernel.new(content)
	state.date="1922-12-09";state.phase_index=state.turn_order.size()-1
	var result=kernel.resolve(state,{"type":"EndPhase","actor_id":state.turn_order[state.phase_index],"expected_version":state.state_version})
	var storage=SaveService.new("user://qa/map_scale_event_%d"%Time.get_ticks_usec(),content)
	verify(result.valid and result.state.cities.any(func(c):return c.id=="qingdao"),"fine_grid_retains_dated_qingdao_historical_activation")
	if result.valid:
		var fingerprint=ContentRegistry.fingerprint(result.state)
		verify(storage.write("test",result.state,content.content_hash) and ContentRegistry.fingerprint(storage.load_slot("test",content.content_hash))==fingerprint,"historical_cell_activation_survives_compact_save")
	var custom=StateAccess.clone_transaction(state);custom.map.id="isolated_custom_geography"
	var packed=storage.pack_map(custom,content.content_hash)
	verify(packed.map.has("cells") and not packed.map.has("_template_reference"),"unknown_imported_map_keeps_self_contained_save_payload")
	var fixture=ContentRegistry.integerize(content.read_json("res://tests/fixtures/capacity_full_conquest.json"))
	var full=CapacityFixture.create(content,fixture)
	var full_registry=ContentRegistry.new();full_registry.maps=content.maps;full_registry.content_hash=full.content_hash
	storage=SaveService.new("user://qa/map_scale_full_%d"%Time.get_ticks_usec(),full_registry)
	var full_hash=ContentRegistry.fingerprint(full)
	verify(storage.write("test",full,full.content_hash),"complete_74762_cell_full_visibility_workload_saved")
	var restored=storage.load_slot("test",full.content_hash)
	verify(ContentRegistry.fingerprint(restored)==full_hash,"full_visibility_roundtrip_preserves_every_cell_and_full_state")
	verify(FileAccess.get_file_as_bytes(storage.path_for("test")).size()<524288,"full_visibility_arrays_are_reconstructed_without_repeating_74762_ids")
	verify(full.visibility.all(func(v):return v.visible_cell_ids.size()==74762) and restored.visibility.all(func(v):return v.visible_cell_ids.size()==74762),"full_visibility_save_never_crops_or_discards_interaction_cells")
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"measurements":measurements,"content_hash":content.content_hash,"game_version":ContentRegistry.APP_VERSION,"baseline_version":baseline.version,"physical_android_device_tested":false}
	var file=FileAccess.open("res://reports/map_scale_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("MAP_SCALE_TESTS ",JSON.stringify({"passed":report.passed,"checks":checks.size(),"failures":failures,"measurements":measurements}));quit(0 if failures.is_empty() else 1)
