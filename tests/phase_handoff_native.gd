extends SceneTree

func _init() -> void:run.call_deferred()
func run() -> void:
	var app=load("res://app/main.tscn").instantiate();root.add_child(app)
	await process_frame
	var fixture=ContentRegistry.integerize(JSON.parse_string(FileAccess.get_file_as_string("res://tests/fixtures/capacity_jingfeng.json")))
	var state=CapacityFixture.create(app.content,fixture,"balanced")
	app.start_game("qa_capacity",state.player_faction_id);app.close_overlay();app.match_controller.load_state(state)
	for i in range(5):await process_frame
	var controller=app.match_controller
	var barrier=controller.worker.submit("preview",controller.state,controller.command("EndPhase"),app.content)
	while not barrier.is_completed():await process_frame
	for i in range(45):await RenderingServer.frame_post_draw
	controller.main_work_usec.clear()
	controller.command_committed.connect(func(c):if c.type=="EndPhase":controller.paused=true)
	var initial=ContentRegistry.fingerprint(controller.state)
	var accepted=controller.request_command(controller.command("EndPhase"))
	var unchanged=ContentRegistry.fingerprint(controller.state)==initial
	var deadline=Time.get_ticks_msec()+10000
	while controller.state.state_version==0 and Time.get_ticks_msec()<deadline:await process_frame
	for i in range(3):await RenderingServer.frame_post_draw
	var report={"game_version":ContentRegistry.APP_VERSION,"raw_native_source_window":true,"accepted":accepted,"no_inline_commit":unchanged,"state_version":controller.state.state_version,"phase_changed":controller.state.turn_order[controller.state.phase_index]!=controller.state.player_faction_id,"main_handoff_us_samples":controller.main_work_usec,"main_handoff_us_max":controller.main_work_usec.max(),"scope":"Native source scene, real 240-unit EndPhase command and main-thread UI callback; source window probe, not exported EXE or phone evidence."}
	var file=FileAccess.open("res://reports/phase_handoff_native.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("PHASE_HANDOFF ",JSON.stringify(report));quit()
