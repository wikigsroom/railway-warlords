extends SceneTree

var failures: Array=[]
var checks: Array=[]
func _init() -> void:run.call_deferred()
func verify(ok: bool, name: String) -> void:
	checks.append({"name":name,"passed":ok})
	if not ok:failures.append(name);push_error(name)
func run() -> void:
	var content=ContentRegistry.new();verify(content.load_all(),"current_content_loads")
	var controller=MatchController.new();root.add_child(controller);controller.setup(content)
	verify(controller.start("campaign_1924_03","zhili",{},"normal"),"documented_defense_starts")
	var events_seen: Array=[]
	controller.changed.connect(func(events):
		if not events.is_empty():events_seen.append(events.duplicate(true));controller.presentation_busy=true)
	controller.toggle_auto_player()
	# A native worker must be allowed to finish actual enlarged-map planning.
	# Headless frames are uncapped, so a frame count is not a completion signal.
	var deadline=Time.get_ticks_msec()+30000
	while events_seen.is_empty() and Time.get_ticks_msec()<deadline:await process_frame
	verify(controller.auto_player and controller.auto_running and controller.state.state_version==1 and events_seen.size()==1,"automatic_player_issues_one_legal_command_then_waits_for_its_presentation")
	var committed=ContentRegistry.fingerprint(controller.state)
	controller.toggle_auto_player()
	for i in range(8):await process_frame
	verify(not controller.auto_player and not controller.auto_running and ContentRegistry.fingerprint(controller.state)==committed,"stop_button_cancels_further_planning_without_undoing_committed_command")
	verify(not controller.dispatch(controller.command("EndPhase")),"manual_order_blocked_until_presentation_finishes")
	controller.presentation_busy=false;controller.paused=true;controller.toggle_auto_player()
	for i in range(8):await process_frame
	verify(ContentRegistry.fingerprint(controller.state)==committed,"pause_panel_prevents_automatic_commands")
	var saved=controller.state.duplicate(true);controller.load_state(saved)
	for i in range(8):await process_frame
	verify(not controller.auto_player and not controller.auto_running and not controller.presentation_busy and ContentRegistry.fingerprint(controller.state)==committed,"loading_resets_presentation_and_invalidates_previous_automatic_coroutine")
	controller.toggle_auto_player();controller.abandon()
	for i in range(8):await process_frame
	verify(controller.state.is_empty() and not controller.auto_running and not controller.ai_running,"abandoning_does_not_leave_a_ghost_planner_running")
	controller.queue_free();await process_frame
	var file=FileAccess.open("res://reports/automation_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify({"build_version":ContentRegistry.APP_VERSION,"content_hash":content.content_hash,"checks":checks,"failures":failures,"passed":checks.size()-failures.size(),"failed":failures.size()},"\t"));file.close()
	print("AUTOMATION_TESTS ",checks.size()-failures.size()," passed / ",failures.size()," failed");quit(0 if failures.is_empty() else 1)
