extends SceneTree

# Development-only A/B measurement of the additional substrate pass. This
# keeps the same game, source geometry, camera path and GPU in one process.
# It is neither an old-build comparison nor physical Android evidence.
var app
var stages: Array=[]

func _init() -> void:execute.call_deferred()

func settle(frames: int) -> void:
	for i in frames:await process_frame

func measure(enabled: bool, repeat_index: int, saved_bases: Dictionary, saved_opacities: Dictionary) -> void:
	var view=app.map_view;var details=view.map_details
	details.relief_underlays=saved_bases.duplicate() if enabled else {}
	details.relief_opacities=saved_opacities.duplicate() if enabled else {}
	details.macro_chunks.clear();details.macro_chunk_meshes.clear();details.continuous_color_templates.clear();details.macro_index_prepared=false
	view.backdrop_signature="";view.camera=Vector2(16848,7000);view.zoom=1.05
	await settle(90)
	var times: Array=[];var draws: Array=[];var focused=0;var before=view.backdrop_rebuilds
	for i in 180:
		view.camera=Vector2(16848,7000)+Vector2(sin(float(i)*TAU/180.0)*420.0,cos(float(i)*TAU/180.0)*180.0)
		view.queue_redraw()
		var started=Time.get_ticks_usec()
		await process_frame
		times.append((Time.get_ticks_usec()-started)/1000.0)
		draws.append(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME))
		if DisplayServer.window_is_focused():focused+=1
	var sorted=times.duplicate();sorted.sort();var elapsed=0.0
	for ms in times:elapsed+=ms
	stages.append({"underlay_enabled":enabled,"repeat":repeat_index,"recorded_at_utc":Time.get_datetime_string_from_system(true),"sample_frames":times.size(),"focused_frames":focused,"average_fps":times.size()*1000.0/elapsed,"frame_ms_p95":sorted[170],"frame_ms_max":sorted[-1],"draw_calls_min":draws.min(),"draw_calls_max":draws.max(),"backdrop_rebuilds":view.backdrop_rebuilds-before,"cached_chunks":details.macro_chunk_meshes.size(),"frame_ms_samples":times})
	print("PAN_COST_STAGE ",JSON.stringify(stages[-1].duplicate().merged({"frame_ms_samples":"saved_in_report"},true)))

func execute() -> void:
	app=load("res://app/main.tscn").instantiate();root.add_child(app)
	await settle(20)
	app.settings.tutorial=false;app.start_game("campaign_1924_03",app.content.scenarios.campaign_1924_03.player_default);app.close_overlay()
	await settle(20)
	Engine.max_fps=0;DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	var before=ContentRegistry.fingerprint(app.match_controller.state)
	var bases=app.map_view.map_details.relief_underlays.duplicate();var opacities=app.map_view.map_details.relief_opacities.duplicate()
	for mode in [[false,1],[true,1],[true,2],[false,2]]:await measure(mode[0],mode[1],bases,opacities)
	var unchanged=ContentRegistry.fingerprint(app.match_controller.state)==before
	var report={"version":ContentRegistry.APP_VERSION,"platform":OS.get_name(),"renderer":RenderingServer.get_current_rendering_method(),"gpu":RenderingServer.get_video_adapter_name(),"viewport":[int(app.get_viewport_rect().size.x),int(app.get_viewport_rect().size.y)],"stages":stages,"warmup_frames_per_stage":90,"frame_cap":Engine.max_fps,"vsync_disabled":true,"underlay_source_cells":bases.size(),"state_unchanged":unchanged,"same_process_same_camera_path":true,"compared_to_previous_export":false,"physical_android_device_tested":false,"occlusion_beyond_focus_measured":false,"other_godot_tests_running":false,"measurement":"Native development game; uncapped pan on actual Jingfeng geography. A/B toggles only substrate assignments and mineral opacities; 24-percent sprite foot fade remains in both modes. Windows desktop only."}
	var file=FileAccess.open("res://reports/relief_grounding_v0232/pan_cost.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	var view=app.map_view;var details=view.map_details
	details.relief_underlays=bases;details.relief_opacities=opacities
	details.macro_chunks.clear();details.macro_chunk_meshes.clear();details.continuous_color_templates.clear();details.macro_index_prepared=false
	view.camera=Vector2(16848,7000);view.zoom=1.05;view.backdrop_signature=""
	await settle(8)
	await app.capture_ui("res://reports/relief_grounding_v0232/mountain_batched.png","relief_grounding_batched_development")
	print("PAN_COST_COMPLETE state_unchanged=",unchanged);quit(0 if unchanged else 1)
