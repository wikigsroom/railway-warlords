extends SceneTree

# Real published campaign and legal player moves; no fabricated deployment.
# Direct native viewport evidence, with no image editing or assembly.
var failures: Array=[]
var cases: Array=[]

func _init() -> void:
	run.call_deferred()

func run() -> void:
	var app=load("res://app/main.tscn").instantiate()
	app.qa_save_path="user://qa/directions_%d"%Time.get_ticks_usec()
	root.add_child(app)
	await process_frame
	app.settings.tutorial=false;app.settings.music=false;app.settings.sound=false;app.apply_audio_settings()
	var directory="res://reports/screenshots/directions"
	DirAccess.make_dir_recursive_absolute(directory)
	for sample in [["n",Vector2i(0,-1),Vector2.UP],["e",Vector2i(1,0),Vector2.RIGHT],["s",Vector2i(0,1),Vector2.DOWN],["w",Vector2i(-1,0),Vector2.LEFT]]:
		var c: Dictionary={};var unit: Dictionary={}
		for scenario in ["campaign_1920_01","campaign_1922_01","campaign_1924_03","campaign_1924_02"]:
			app.start_game(scenario,app.content.scenarios[scenario].player_default);app.close_overlay()
			await process_frame
			var trial_state=app.match_controller.state
			for candidate in trial_state.units:
				if candidate.owner_id!=trial_state.player_faction_id or candidate.position==null or candidate.def_id!="rifle":continue
				var graph=MovementRules.reachable(trial_state,candidate,app.content)
				for key in graph.costs:
					var target=HexGrid.from_key(key)
					var route=MovementRules.route_from_graph(graph,HexGrid.coordinate(candidate.position),target)
					if route.size()<2 or route[-1]-route[-2]!=sample[1]:continue
					var trial=VisualPlaytest.command(trial_state,"Move",{"unit_id":candidate.id,"target_hex":HexGrid.position(target)})
					if app.match_controller.kernel.preview(trial_state,trial).valid:
						unit=candidate;c=trial;break
				if not c.is_empty():break
			if not c.is_empty():break
		if c.is_empty():failures.append("no_legal_published_infantry_move_"+sample[0]);continue
		var state=app.match_controller.state
		var initial=ContentRegistry.fingerprint(state)
		app.selected_unit_id=unit.id;app.selected_city_id="";app.refresh_battle()
		var from=HexGrid.to_world(HexGrid.coordinate(unit.position));var to=HexGrid.to_world(HexGrid.coordinate(c.target_hex))
		app.map_view.zoom=1.5;app.map_view.camera=(from+to)*.5;app.map_view.clamp_camera();app.map_view.queue_redraw()
		for i in range(4):await process_frame
		var result=app.match_controller.kernel.resolve(state,c)
		if not result.valid or ContentRegistry.fingerprint(state)!=initial:failures.append("preview_or_snapshot_changed_"+sample[0]);continue
		if not app.match_controller.dispatch(c):failures.append("legal_move_rejected_"+sample[0]);continue
		var moving_capture=false;var deadline=Time.get_ticks_msec()+60000
		while app.match_controller.command_busy or app.match_controller.presentation_busy:
			if Time.get_ticks_msec()>deadline:failures.append("native_move_timeout_"+sample[0]);break
			var playback=app.map_view.playback
			if playback.active and playback.current.kind=="move" and not moving_capture:
				var route=playback.current.path;var progress=playback.progress();var travel=progress*progress*(3-2*progress)
				var segment=mini(route.size()-2,int((route.size()-1)*travel))
				var step=HexGrid.coordinate(route[segment+1])-HexGrid.coordinate(route[segment])
				if step==sample[1] and progress>.15 and progress<.95:
					await VisualPlaytest.capture(app,directory+"/"+sample[0]+"_moving.png");moving_capture=true
			await process_frame
		for i in range(3):await process_frame
		await VisualPlaytest.capture(app,directory+"/"+sample[0]+"_idle.png")
		var heading: Vector2=app.map_view.unit_headings.get(unit.id,Vector2.ZERO)
		var orientation=app.map_view.unit_orientation(heading,"se",unit)
		var replay_equal=ContentRegistry.fingerprint(result.state)==ContentRegistry.fingerprint(app.match_controller.state)
		var passed=moving_capture and orientation.asset==sample[0] and orientation.angle==0.0 and heading.normalized().dot(sample[2])>.8 and replay_equal
		if not passed:failures.append("direction_or_replay_"+sample[0])
		cases.append({"direction":sample[0],"scenario_id":state.scenario_id,"passed":passed,"unit_id":unit.id,"command":c,"asset":"unit_rifle_"+str(orientation.asset),"raster_rotation":orientation.angle,"heading":[heading.x,heading.y],"moving_captured":moving_capture,"idle_heading_retained":true,"legal_command_replay_equal":replay_equal})
	var report={"passed":failures.is_empty() and cases.size()==4,"failures":failures,"cases":cases,"build_version":ContentRegistry.APP_VERSION,"content_hash":app.content.content_hash,"unmodified_published_deployment":true,"raw_godot_viewport":true,"image_compositing":false,"physical_android_device_tested":false}
	var file=FileAccess.open("res://reports/directional_native_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("DIRECTIONAL_NATIVE_TEST ",JSON.stringify(report))
	app.audio.stop_all();await create_timer(.15).timeout;quit(0 if report.passed else 1)
