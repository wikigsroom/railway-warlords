class_name ResponsivenessQA
extends RefCounted

static func option(args: PackedStringArray, name: String, fallback: String) -> String:
	var i=args.find(name);return args[i+1] if i>=0 and i+1<args.size() else fallback

static func run(app: Control) -> void:
	var args=OS.get_cmdline_user_args()
	if app.qa_save_path.is_empty():push_error("Responsiveness QA requires isolated saves");app.get_tree().quit(1);return
	var fixture_path=option(args,"--capacity-fixture","")
	var map=ContentRegistry.integerize(JSON.parse_string(FileAccess.get_file_as_string(fixture_path)))
	var state=CapacityFixture.create(app.content,map,"balanced")
	if state.is_empty():push_error("Capacity fixture could not be created");app.get_tree().quit(1);return
	app.start_game("qa_capacity",state.player_faction_id);app.close_overlay();app.match_controller.load_state(state)
	for i in range(8):await app.get_tree().process_frame
	var controller=app.match_controller;var view=app.map_view
	view.fit_map();view.playback.speed=4.0
	Engine.max_fps=0;DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	# Drain startup autosaves and range queries before measuring active play.
	var barrier=controller.worker.submit("preview",controller.state,controller.command("EndPhase"),app.content)
	while not barrier.is_completed():await app.get_tree().process_frame
	for i in range(45):await RenderingServer.frame_post_draw
	controller.main_work_usec.clear();controller.worker_times.clear()
	var commits: Array=[];var native_images: Array=[]
	controller.command_committed.connect(func(c):
		commits.append(c.duplicate(true))
		if c.type=="EndPhase":controller.paused=true
		if commits.size()>=24 and controller.auto_player:controller.toggle_auto_player())
	var frames: Array=[];var planning_frames=0;var animation_frames=0;var planning_finished_frames=0
	var start=Time.get_ticks_usec();var previous=start;var center=view.camera;var zoom=view.zoom;var i=0
	controller.toggle_auto_player()
	# frame_post_draw can observe the actor's last frame before the main
	# presentation coroutine releases its command gate on process_frame.
	while Time.get_ticks_usec()-start<120000000 and (commits.size()<24 or controller.command_busy or controller.presentation_busy or view.playback.active):
		if controller.command_busy:
			planning_frames+=1
			if controller._active_job!=null and controller._active_job.is_completed():planning_finished_frames+=1
		if view.playback.active:animation_frames+=1
		view.camera=center+Vector2(sin(i*.012)*35,cos(i*.012)*20)/zoom;view.queue_redraw()
		i+=1;await RenderingServer.frame_post_draw
		var now=Time.get_ticks_usec();frames.append((now-previous)/1000.0);previous=now
		if native_images.is_empty() and view.playback.active and view.playback.current.get("kind")=="attack":
			var capture=option(args,"--capture-path","res://reports/screenshots/responsiveness_native.png")
			if app.get_viewport().get_texture().get_image().save_png(capture)==OK:native_images.append(capture)
	if controller.auto_player:controller.toggle_auto_player()
	var phase_version=int(controller.state.state_version)+1
	var phase_accepted=controller.request_command(controller.command("EndPhase"))
	var phase_deadline=Time.get_ticks_msec()+10000
	while int(controller.state.state_version)<phase_version and Time.get_ticks_msec()<phase_deadline:
		await RenderingServer.frame_post_draw
		var now=Time.get_ticks_usec();frames.append((now-previous)/1000.0);previous=now
	for extra in range(4):
		await RenderingServer.frame_post_draw
		var now=Time.get_ticks_usec();frames.append((now-previous)/1000.0);previous=now
	var phase_changed=controller.state.turn_order[controller.state.phase_index]!=controller.state.player_faction_id
	var sorted=frames.duplicate();sorted.sort();var elapsed=(Time.get_ticks_usec()-start)/1000000.0
	var main_max=controller.main_work_usec.max() if not controller.main_work_usec.is_empty() else 999999
	var passed=commits.size()>=25 and phase_accepted and phase_changed and planning_frames>0 and animation_frames>0 and not native_images.is_empty() and main_max<=8000
	var report={"game_version":ContentRegistry.APP_VERSION,"content_hash":app.content.content_hash,"qa_capacity_fixture":true,"real_usable_cells":state.map.cells.filter(func(c):return c.region_id!="restricted").size(),"initial_active_units":state.units.size(),"viewport":[int(app.get_viewport_rect().size.x),int(app.get_viewport_rect().size.y)],"mobile_layout_profile":app.mobile_layout(),"ui_scale":app.settings.ui_scale,"physical_android_device_tested":OS.has_feature("android"),"is_exported_executable":not OS.has_feature("editor"),"passed":passed,"commands":commits,"command_count":commits.size(),"planning_frames":planning_frames,"completed_result_wait_frames":planning_finished_frames,"animation_frames":animation_frames,"total_frames":frames.size(),"duration_seconds":elapsed,"average_fps":frames.size()/elapsed,"frame_ms_p95":sorted[mini(sorted.size()-1,int(ceil(sorted.size()*.95))-1)],"frame_ms_max":sorted[-1],"main_handoff_us_samples":controller.main_work_usec,"main_handoff_us_max":main_max,"worker_ms_samples":controller.worker_times.map(func(t):return t/1000.0),"raw_native_captures":native_images,"scope":"Active complete-production-map/240-unit play, 24 real legal AI commands, background planning and resolve, main-thread submit/atomic commit including synchronous signal listeners, live pan and native combat presentation at 4x speed. Startup, manual save/load, scene construction and OS lifecycle excluded. Desktop mobile layout is not physical X30."}
	var path=option(args,"--responsiveness-report","res://reports/responsiveness_native.json")
	report.end_phase_accepted=phase_accepted;report.end_phase_changed=phase_changed
	report.scope+=" Includes a real player EndPhase, resource/phase update and phased UI refresh; enemy planning paused after that commit."
	report.main_work_details=controller.main_work_details;report.presentation_timings=app.qa_presentation_timings;report.order_timings=app.qa_order_timings
	var file=FileAccess.open(path,FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("RESPONSIVENESS_QA ",passed,"; commands=",commits.size(),"; handoff_max_us=",main_max,"; planning_frames=",planning_frames,"; animation_frames=",animation_frames)
	app.get_tree().quit(0 if passed else 1)
