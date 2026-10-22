extends SceneTree

var output=""
var app

func _init() -> void:
	var args=OS.get_cmdline_user_args()
	for i in range(args.size()):
		if args[i]=="--report-output" and i+1<args.size():output=args[i+1]
	run.call_deferred()

func settle(frames: int) -> void:
	for i in frames:
		await process_frame
		await RenderingServer.frame_post_draw

func run() -> void:
	if output.is_empty():push_error("A new report path is required");quit(1);return
	app=load("res://app/main.tscn").instantiate();root.add_child(app)
	await settle(20)
	app.settings.tutorial=false;app.settings.music=false;app.settings.sound=false;app.apply_audio_settings()
	app.start_game("campaign_1924_03",app.content.scenarios.campaign_1924_03.player_default);app.close_overlay()
	await settle(20)
	if app.map_view==null:push_error("No native map view");quit(1);return
	var view: MapView=app.map_view
	view.camera=Vector2(16848,7000);view.zoom=1.05;view.queue_redraw()
	await settle(90)
	var before=ContentRegistry.fingerprint(app.match_controller.state)
	var frames: Array=[];var focused=0;var rebuilds=view.backdrop_rebuilds
	var prefetch_before={"requested":app.assets.map_prefetch_requested,"completed":app.assets.map_prefetch_completed,"sync_misses":app.assets.synchronous_map_misses}
	for i in 180:
		view.camera=Vector2(16848,7000)+Vector2(sin(float(i)*TAU/180.0)*420.0,cos(float(i)*TAU/180.0)*180.0)
		view.queue_redraw()
		var began=Time.get_ticks_usec()
		await process_frame
		await RenderingServer.frame_post_draw
		frames.append((Time.get_ticks_usec()-began)/1000.0)
		if DisplayServer.window_is_focused():focused+=1
	var facts=view.map_bank_capture_facts()
	var checks=[{"name":"actual_normal_game_scene","passed":app.content.errors.is_empty()},
		{"name":"all_180_drawn_frames_measured","passed":frames.size()==180},
		{"name":"rendering_keeps_match_unchanged","passed":before==ContentRegistry.fingerprint(app.match_controller.state)},
		{"name":"source_fine_reaches_present","passed":facts.hydrography.visible_fine_reaches>0},
		{"name":"muted_headwaters_drawn","passed":facts.hydrography.river_surface.drawn_antialiased_headwaters>0}]
	var passed=true
	for check in checks:passed=passed and check.passed
	var report={"passed":passed,"checks":checks,"build_version":ContentRegistry.APP_VERSION,
		"native_content_hash":app.content.content_hash,"scope":"Development Windows frame_post_draw intervals on an ordinary game scene. No shipping, Android-device, controlled baseline or art-quality claim.",
		"production_source_overrides":false,"frame_ms":frames,"focused_frames":focused,
		"window_size":[root.size.x,root.size.y],"mobile_ui":app.mobile_layout(),"maximum_fps":Engine.max_fps,
		"vsync_mode":DisplayServer.window_get_vsync_mode(),"gpu":RenderingServer.get_video_adapter_name(),
		"backdrop_rebuilds":view.backdrop_rebuilds-rebuilds,"prefetch_before":prefetch_before,
		"prefetch_after":{"requested":app.assets.map_prefetch_requested,"completed":app.assets.map_prefetch_completed,"sync_misses":app.assets.synchronous_map_misses},
		"final_camera":[view.camera.x,view.camera.y],"zoom":view.zoom,"hydrography":facts.hydrography,
		"qa_save_isolated":not app.qa_save_path.is_empty(),"physical_android_device_tested":false,
		"other_application_gpu_cpu_load_controlled":false,"formal_art_approval":false}
	var file=FileAccess.open(output,FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("RIVER_PAN_NATIVE passed=",passed," frames=",frames.size()," focused=",focused)
	quit(0 if passed else 1)
