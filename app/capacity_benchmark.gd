class_name CapacityBenchmark
extends RefCounted

static func option(args: PackedStringArray, name: String, fallback: String) -> String:
	var i=args.find(name);return args[i+1] if i>=0 and i+1<args.size() else fallback

static func percentile(values: Array) -> float:
	var ordered=values.duplicate();ordered.sort();return ordered[mini(ordered.size()-1,int(ceil(ordered.size()*.95))-1)]

static func run(app: Control) -> void:
	var args=OS.get_cmdline_user_args()
	if app.qa_save_path.is_empty():push_error("Capacity measurements require an isolated --qa-session");app.get_tree().quit(1);return
	var path=option(args,"--capacity-fixture","")
	var json=JSON.new()
	if json.parse(FileAccess.get_file_as_string(path))!=OK or not json.data is Dictionary:push_error("Capacity geographic fixture unavailable");app.get_tree().quit(1);return
	var state=CapacityFixture.create(app.content,ContentRegistry.integerize(json.data),"balanced")
	if state.is_empty() or state.units.size()!=240:push_error("Capacity fixture has insufficient active units");app.get_tree().quit(1);return
	app.start_game("qa_capacity",state.player_faction_id);app.close_overlay()
	app.match_controller.load_state(state);app.select_next_unit()
	# start_game defers focus_player and Containers need a frame to lay out.
	# Establish the measurement camera only after those real UI operations settle.
	for i in range(3):await app.get_tree().process_frame
	app.notice.text="容量测试夹具 · 真实地理 · 240编队测试部署（不代表历史起局）"
	Engine.max_fps=0;DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	var view=app.map_view;var center=view.world_bounds.get_center()
	var fit=minf(view.size.x/view.world_bounds.size.x,view.size.y/view.world_bounds.size.y)*.90
	view.zoom=fit;view.camera=center;view.queue_redraw()
	for i in range(90):await RenderingServer.frame_post_draw
	var stages: Array=[];var preview_times: Array=[];var battle_commands: Array=[]
	var units=state.units.filter(func(u):return u.owner_id==state.player_faction_id)
	for stage in ["atlas_static","atlas_pan","tactical_select","sustained_pan_zoom","battle_active"]:
		var frames: Array=[];var minimum_drawable=240
		var live_draws: Array=[];var initial_active_units=app.match_controller.state.units.size()
		if stage=="tactical_select":
			view.zoom=.85;view.camera=HexGrid.to_world(HexGrid.coordinate(units[0].position));view.queue_redraw()
			for i in range(30):await RenderingServer.frame_post_draw
		elif stage in ["battle_active","sustained_pan_zoom"]:
			view.zoom=fit;view.camera=center;view.reachable={};view.queue_redraw()
			for i in range(30):await RenderingServer.frame_post_draw
			if stage=="battle_active":
				var command=AIPlanner.new(app.content,app.match_controller.kernel).choose(app.match_controller.state)
				if command.type!="Attack" or not app.match_controller.dispatch(command,true):push_error("Capacity workload did not execute a legal real attack");app.get_tree().quit(1);return
				battle_commands.append(command)
		var stage_started=Time.get_ticks_usec()
		var duration=float(option(args,"--capacity-duration","60"))
		var previous=Time.get_ticks_usec()
		var i=0
		while (Time.get_ticks_usec()-stage_started)/1000000.0<duration if stage=="sustained_pan_zoom" else (view.playback.active if stage=="battle_active" else i<180):
			if stage in ["atlas_pan","sustained_pan_zoom"]:
				view.camera=center+Vector2(sin(i*.025)*45,cos(i*.025)*35)/fit
				view.zoom=fit*(1.0+.035*sin(i*.017));view.queue_redraw()
			elif stage=="tactical_select" and i%12==0:
				var u=units[(i/12)%units.size()];view.selected_unit_id=u.id
				view.camera=HexGrid.to_world(HexGrid.coordinate(u.position))
				var t=Time.get_ticks_usec();view.reachable=MovementRules.reachable(state,u,app.content).costs
				preview_times.append((Time.get_ticks_usec()-t)/1000.0);view.queue_redraw()
			await RenderingServer.frame_post_draw
			var now=Time.get_ticks_usec();frames.append((now-previous)/1000.0);previous=now
			var rect=Rect2(view.camera-view.size/(2*view.zoom),view.size/view.zoom).grow(170)
			var current_state=app.match_controller.state
			var drawable=current_state.units.filter(func(u):return rect.has_point(HexGrid.to_world(HexGrid.coordinate(u.position))) and VisibilityRules.unit_visible(current_state,current_state.player_faction_id,u)).size()
			minimum_drawable=mini(minimum_drawable,drawable)
			live_draws.append(view.unit_layer_draw_count());i+=1
		var total=0.0
		for ms in frames:total+=ms
		if frames.is_empty():push_error("Capacity stage contains no native frames: "+stage);app.get_tree().quit(1);return
		stages.append({"stage":stage,"frames":frames.size(),"duration_seconds":(Time.get_ticks_usec()-stage_started)/1000000.0,"initial_active_units":initial_active_units,"final_active_units":app.match_controller.state.units.size(),"frame_ms_p95":percentile(frames),"frame_ms_max":frames.max(),"average_fps":1000.0/(total/frames.size()),"minimum_drawable_units":minimum_drawable,"unit_layer_draw_count_min":live_draws.min(),"frame_ms_samples":frames})
	view.zoom=fit;view.camera=center;view.reachable={};view.queue_redraw()
	await RenderingServer.frame_post_draw
	var report={"game_version":ContentRegistry.APP_VERSION,"production_content_hash":app.content.content_hash,"fixture_content_hash":state.content_hash,"fixture_map_hash":state.fixture_map_hash,"fixture_file_sha256":FileAccess.get_sha256(path),"platform":OS.get_name(),"renderer":RenderingServer.get_current_rendering_method(),"gpu":RenderingServer.get_video_adapter_name(),"viewport":app.get_viewport_rect().size,"window":DisplayServer.window_get_size(),"ui_scale":app.settings.ui_scale,"mobile_layout_profile":app.mobile_layout(),"safe_insets":app.safe_insets(),"physical_android_device_tested":OS.has_feature("android"),"is_exported_executable":not OS.has_feature("editor"),"qa_save_isolated":true,"cells":state.map.cells.size(),"usable_cells":state.map.fixture_source.usable_cells,"active_units":state.units.size(),"unit_types":app.content.tables.units.size(),"historical_deployment_claimed":false,"frame_cap":Engine.max_fps,"vsync_disabled":true,"warmup_frames":90,"selection_preview_ms":preview_times,"stages":stages,"render_target_passed":stages.all(func(s):return s.average_fps>=60),"measurement":"Native full game viewport, 240-unit explicit QA workload on real geography. Uncapped static atlas, per-frame pan, and 15 tactical selection previews. Desktop mobile layout is not physical Android GPU evidence."}
	var out=option(args,"--capacity-report","res://reports/capacity_render.json")
	report.battle_commands=battle_commands;report.unit_layer_rebuilds=view.unit_rebuilds;report.backdrop_rebuilds=view.backdrop_rebuilds
	report.measurement="Native complete scene on real geography: 240-unit static atlas, continuous pan/zoom, tactical selection, legally resolved real combat, and a timed sustained pan/zoom stage. Desktop results are not physical Android evidence."
	DirAccess.make_dir_recursive_absolute(out.get_base_dir())
	var file=FileAccess.open(out,FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	if "--profile-draw" in args:
		var profile=FileAccess.open(out.get_basename()+"_draw_profile.json",FileAccess.WRITE)
		profile.store_string(JSON.stringify({"samples":view.profile_draw_samples,"backdrop_rebuilds":view.backdrop_rebuilds,"cpu_only":true},"\t"));profile.close()
	print("CAPACITY_RENDER ",JSON.stringify({"target":report.render_target_passed,"stages":stages.map(func(s):return {"stage":s.stage,"fps":s.average_fps,"p95":s.frame_ms_p95,"minimum_drawable":s.minimum_drawable_units})}))
	await app.capture_frame()
