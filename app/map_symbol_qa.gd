class_name MapSymbolQA
extends RefCounted

var app
var checks: Array=[]
var captures: Array=[]
var folder=""

static func run(application) -> void:
	var qa=MapSymbolQA.new();qa.app=application;await qa.execute()

func check(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:push_error("MAP_SYMBOL_QA: "+name)

func settle() -> void:
	for index in range(8):await app.get_tree().process_frame
	await RenderingServer.frame_post_draw

func capture(name: String, facts: Dictionary) -> void:
	var path=folder+"/"+name+".png"
	check(await app.capture_ui(path,"map_symbols_"+name),"native_complete_viewport:"+name)
	var metadata_path=path.get_basename()+".json"
	var metadata=JSON.parse_string(FileAccess.get_file_as_string(metadata_path))
	metadata["map_symbols"]=facts;metadata["scenario_id"]=app.match_controller.state.scenario_id
	metadata["camera"]=[app.map_view.camera.x,app.map_view.camera.y];metadata["zoom"]=app.map_view.zoom
	var file=FileAccess.open(metadata_path,FileAccess.WRITE);file.store_string(JSON.stringify(metadata,"\t"));file.close()
	captures.append({"path":path,"metadata":metadata_path,"facts":facts})

func visible_unit_ids() -> Array:
	# Independent rules visibility and projection. Do not use a renderer helper
	# to decide which units should have produced an actual drawing command.
	var view: MapView=app.map_view;var state: Dictionary=app.match_controller.state;var result: Array=[]
	for unit in state.units:
		if unit.position==null or not VisibilityRules.unit_visible(state,state.player_faction_id,unit):continue
		var world=HexGrid.to_world(HexGrid.coordinate(unit.position))
		var screen=(world-view.camera)*view.zoom+view.size*.5
		if Rect2(Vector2.ZERO,view.size).grow(-3).has_point(screen):result.append(unit.id)
	return result

func execute() -> void:
	if app.qa_save_path.is_empty():push_error("Map symbol QA requires isolated --qa-session");app.get_tree().quit(1);return
	var args=OS.get_cmdline_user_args();var index=args.find("--map-symbol-output")
	folder=args[index+1] if index>=0 else "res://reports/screenshots/map_symbols_native"
	for scenario in ["asia_1840","campaign_1924_03"]:
		app.settings.tutorial=false;app.start_game(scenario,app.content.scenarios[scenario].player_default);app.close_overlay();await settle()
		app.selected_unit_id="";app.selected_city_id="";app.selected_poi_id="";app.pending={};app.order_mode="";app.refresh_battle();await settle()
		var state: Dictionary=app.match_controller.state;var view: MapView=app.map_view
		var before=ContentRegistry.fingerprint(state);var focus=StateAccess.find(state,"cities","beijing" if scenario=="asia_1840" else "shanhaiguan")
		check(not focus.is_empty(),"real_focus_city_exists:"+scenario)
		if focus.is_empty():continue
		var anchor=HexGrid.to_world(HexGrid.coordinate(focus.position))
		var previous_zoom=0.0;var previous_rebuilds=0
		for scale in [.14,.199,.201,.40,.559,.561,.90]:
			view.zoom=scale;view.focus_world(anchor);await settle()
			var facts=view.map_symbol_capture_facts();var expected=visible_unit_ids()
			var actual: Array=facts.unit_counter_ids+facts.unit_detail_ids
			var name=scenario+"_"+str(roundi(scale*1000))
			check(not expected.is_empty() and expected.all(func(id):return actual.has(id)),"all_visible_rule_formations_drawn:"+name)
			var unique: Dictionary={}
			for id in actual:unique[id]=true
			check(actual.size()==unique.size(),"no_duplicate_formation_commands:"+name)
			if scale<.56:
				check(facts.unit_detail_ids.is_empty() and not facts.unit_counter_ids.is_empty(),"quiet_scale_uses_unit_counters:"+name)
				check(facts.city_detail_ids.is_empty() and not facts.city_counter_ids.is_empty(),"quiet_scale_uses_city_counters:"+name)
				var size: Array=facts.unit_counter_screen_size
				var diagonal=Vector2(size[0],size[1]).length()+2*MapSemanticZoom.unit_border(scale)
				check(diagonal<HexGrid.to_world(HexGrid.DIRECTIONS[0]).length()*scale,"counter_diagonal_fits_adjacent_cell_spacing:"+name)
			else:
				check(facts.unit_counter_ids.is_empty() and not facts.unit_detail_ids.is_empty(),"near_scale_restores_all_authored_unit_sources:"+name)
				check(facts.city_counter_ids.is_empty() and not facts.city_detail_ids.is_empty(),"near_scale_restores_city_sources:"+name)
			if previous_zoom>0 and absf(scale-previous_zoom)<.01:
				check(view.unit_rebuilds>previous_rebuilds,"small_zoom_crossing_invalidates_symbol_cache:"+name)
			if scale>=.40:
				check(facts.background_legacy_terrain_symbols==0 and facts.background_painted_scenery>0,"painted_scenery_replaces_redundant_vector_terrain_marks:"+name)
			await capture(name,facts)
			previous_zoom=scale;previous_rebuilds=view.unit_rebuilds
		for crossing in [[.561,.559],[.201,.199]]:
			view.zoom=crossing[0];view.focus_world(anchor);await settle()
			var rebuilds=view.unit_rebuilds
			view.zoom=crossing[1];view.queue_redraw();await settle()
			var reverse=view.map_symbol_capture_facts()
			check(view.unit_rebuilds>rebuilds and reverse.unit_detail_ids.is_empty() and not reverse.unit_counter_ids.is_empty(),"reverse_small_zoom_crossing_restores_compact_symbols:"+scenario+":"+str(crossing[1]))
		var click_targets=state.units.filter(func(unit):return unit.position!=null and unit.owner_id==state.player_faction_id)
		click_targets.sort_custom(func(a,b):return StateAccess.at(state,"cities",HexGrid.coordinate(a.position)).is_empty() and not StateAccess.at(state,"cities",HexGrid.coordinate(b.position)).is_empty())
		for target in click_targets.slice(0,3):
			app.selected_unit_id="";app.selected_city_id="";app.selected_poi_id="";app.pending={};app.order_mode="";app.refresh_battle()
			view.zoom=.201;view.focus_world(HexGrid.to_world(HexGrid.coordinate(target.position)));await settle()
			view.select_screen(view.world_to_screen(HexGrid.to_world(HexGrid.coordinate(target.position))));await settle()
			check(app.selected_unit_id==target.id,"compact_counter_click_beats_nearby_city_snap:"+scenario+":"+str(target.id))
		app.selected_unit_id="";app.selected_city_id="";app.selected_poi_id="";app.pending={};app.order_mode="";app.refresh_battle();await settle()
		var own=state.units.filter(func(unit):return unit.position!=null and unit.owner_id==state.player_faction_id)[0]
		view.zoom=.40;view.focus_world(HexGrid.to_world(HexGrid.coordinate(own.position)));await settle()
		view.select_screen(view.world_to_screen(HexGrid.to_world(HexGrid.coordinate(own.position))));await settle()
		var selected=view.map_symbol_capture_facts()
		check(app.selected_unit_id==own.id and selected.unit_detail_ids.has(own.id),"ordinary_map_click_selects_and_promotes_formation:"+scenario)
		check(ContentRegistry.fingerprint(app.match_controller.state)==before,"zoom_and_selection_preserve_complete_state_and_rng:"+scenario)
		await capture(scenario+"_selected",selected)
	var failures=checks.filter(func(row):return not row.passed)
	var report={"passed":failures.is_empty(),"build_version":ContentRegistry.APP_VERSION,"checks":checks,"failures":failures,"captures":captures,"physical_android_device_tested":false,"formal_art_approval":false,"ew6_parity_claimed":false,"scope":"Actual published Asia and Shanhaiguan scenarios; native draw identities, geographic anchors, sub-cache-tolerance zoom crossings and ordinary selection; full native frames, no image editing."}
	var file=FileAccess.open(folder+"/validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("MAP_SYMBOL_NATIVE ",JSON.stringify({"passed":report.passed,"checks":checks.size(),"captures":captures.size(),"failures":failures}));app.get_tree().quit(0 if report.passed else 1)
