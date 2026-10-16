extends SceneTree

var checks: Array=[]
var failures: Array=[]
var content=ContentRegistry.new()
var heartbeats=0
var trace_commands=0
var longest_worker_usec=0

func _init() -> void:run.call_deferred()
func check(ok: bool, name: String) -> void:
	checks.append({"name":name,"passed":ok})
	if not ok:failures.append(name);push_error(name)

func wait_job(job: RulesJob, limit_ms: int = 10000) -> bool:
	var deadline=Time.get_ticks_msec()+limit_ms
	while not job.is_completed() and Time.get_ticks_msec()<deadline:
		heartbeats+=1;await process_frame
	return job.is_completed()

func wait_controller(controller: MatchController, version: int, limit_ms: int = 10000) -> bool:
	var deadline=Time.get_ticks_msec()+limit_ms
	while int(controller.state.get("state_version",-1))<version and Time.get_ticks_msec()<deadline:await process_frame
	return int(controller.state.get("state_version",-1))>=version

func compare_worker_trace(worker: RulesWorker, initial: Dictionary, count: int, label: String) -> void:
	var kernel=CommandKernel.new(content);var actual=initial;var expected=StateAccess.clone_transaction(initial)
	var ai=AIPlanner.new(content,kernel);var reference=AIPlanner.new(content,kernel)
	var observer=StateBuilder.create(content,"campaign_1920_01","zhili",{})
	var observer_cell=HexGrid.coordinate(observer.map.cells[0].position)
	var observer_record=StateAccess.cell(observer,observer_cell)
	for index in range(count):
		if actual.status!="playing":break
		var before=ContentRegistry.fingerprint(actual)
		var command=reference.choose(expected);var result=kernel.resolve(expected,command)
		var job=worker.submit("plan",actual,{},content,ai)
		var deadline=Time.get_ticks_msec()+10000;var queries_valid=true;var query_frames=0
		while not job.is_completed() and Time.get_ticks_msec()<deadline:
			# The renderer may query a completely different map during computation.
			queries_valid=queries_valid and StateAccess.cell(observer,observer_cell)==observer_record
			for u in observer.units:
				if u.position!=null:
					queries_valid=queries_valid and StateAccess.at(observer,"units",HexGrid.coordinate(u.position)).id==u.id
					VisibilityRules.unit_visible(observer,observer.player_faction_id,u)
			heartbeats+=1;query_frames+=1;await process_frame
		check(job.is_completed() and job.worker_thread_id!=OS.get_main_thread_id(),label+":%02d:off_main_thread"%index)
		if not job.is_completed():job.cancel();break
		check(queries_valid and query_frames>0,label+":%02d:concurrent_renderer_queries"%index)
		check(ContentRegistry.fingerprint(actual)==before,label+":%02d:input_snapshot_and_rng_unchanged"%index)
		check(job.result.get("valid",false) and result.valid,label+":%02d:legal"%index)
		if not job.result.get("valid",false) or not result.valid:break
		check(ContentRegistry.fingerprint(job.command)==ContentRegistry.fingerprint(command),label+":%02d:same_decision"%index)
		check(ContentRegistry.fingerprint(job.result.events)==ContentRegistry.fingerprint(result.events),label+":%02d:same_ordered_events"%index)
		check(ContentRegistry.fingerprint(job.result.state)==ContentRegistry.fingerprint(result.state),label+":%02d:same_complete_state_and_rng"%index)
		var legacy=BattlePlayback.new();legacy.begin(actual,result.state,result.events,content)
		var staged=BattlePlayback.new();staged.adopt(job.result.presentation.playback)
		check(ContentRegistry.fingerprint(staged.steps)==ContentRegistry.fingerprint(legacy.steps) and ContentRegistry.fingerprint(staged.units)==ContentRegistry.fingerprint(legacy.units) and staged.active==legacy.active,label+":%02d:same_prepared_presentation_and_actor_order"%index)
		longest_worker_usec=maxi(longest_worker_usec,job.worker_usec);trace_commands+=1
		actual=job.result.state;expected=result.state

func check_prepared_sight_cache() -> void:
	var cache=PreparedSightCache.current()
	check(is_same(cache,PreparedSightCache.current()),"presentation_index_is_private_to_current_thread")
	var visible=["a","b","a"];visible.make_read_only()
	var first=cache.build(visible,"visible")
	check(first.known==["a","b"] and first.ids.size()==2,"presentation_index_preserves_first_seen_order_and_deduplicates")
	check(first.is_read_only() and first.ids.is_read_only() and first.known.is_read_only(),"published_presentation_index_is_immutable")
	check(is_same(first,cache.build(visible,"visible")),"unchanged_immutable_sight_reuses_exact_index")
	var changed=["b","c"];changed.make_read_only()
	var second=cache.build(changed,"visible")
	check(second.ids.has("c") and not second.ids.has("a") and second.known==["b","c"],"same_size_new_immutable_sight_has_exact_new_membership")
	check(first.known==["a","b"] and not first.ids.has("c"),"replacing_cache_does_not_mutate_published_previous_index")
	check(not is_same(first,second),"different_immutable_sight_does_not_reuse_stale_index")
	var explored=["a","b","d"];explored.make_read_only()
	var explored_index=cache.build(explored,"explored")
	check(explored_index.ids.has("d") and not second.ids.has("d"),"visible_and_explored_cache_slots_are_independent")
	var editable=["a","b"]
	var editable_before=cache.build(editable,"editable")
	editable[0]="c"
	var editable_after=cache.build(editable,"editable")
	check(editable_before.ids.has("a") and not editable_after.ids.has("a") and editable_after.ids.has("c"),"mutable_input_edit_rebuilds_without_stale_membership")
	editable.reverse()
	check(cache.build(editable,"editable").known==["b","c"],"mutable_input_reorder_preserves_new_order")
	check(not cache.sources.has("editable"),"mutable_input_is_never_retained_in_immutable_cache")
	check(is_same(second,cache.build(changed,"visible")),"mutable_builds_do_not_displace_other_immutable_slot")

func run() -> void:
	check(content.load_all(),"content_loads")
	check_prepared_sight_cache()
	var controller=MatchController.new();root.add_child(controller);controller.setup(content)
	var other=MatchController.new();root.add_child(other);other.setup(content)
	check(controller.worker==other.worker,"all_controllers_share_one_serialized_worker")
	check(RulesQueryCache.current()==RulesQueryCache.current(),"main_thread_has_stable_private_query_cache")
	await compare_worker_trace(controller.worker,StateBuilder.create(content,"campaign_1924_03","zhili",{}),16,"production_campaign")
	var map=ContentRegistry.integerize(JSON.parse_string(FileAccess.get_file_as_string("res://tests/fixtures/capacity_jingfeng.json")))
	for distribution in ["balanced","concentrated","single_faction"]:
		var fixture=CapacityFixture.create(content,map,distribution)
		check(not fixture.is_empty() and fixture.units.size()==240,"capacity_created:"+distribution)
		if not fixture.is_empty():await compare_worker_trace(controller.worker,fixture,8,"capacity_"+distribution)
	check(controller.start("campaign_1924_03","zhili",{},"normal"),"controller_starts")
	var commits: Array=[]
	controller.command_committed.connect(func(c):commits.append(c))
	controller.changed.connect(func(events):if not events.is_empty():controller.presentation_busy=true)
	var before=ContentRegistry.fingerprint(controller.state)
	var planner=AIPlanner.new(content,controller.kernel);var expected_command=planner.choose(controller.state)
	var expected=controller.kernel.resolve(controller.state,expected_command)
	check(controller.request_command(expected_command),"interactive_command_queued")
	var pending_job=controller._active_job
	check(controller.command_busy and ContentRegistry.fingerprint(controller.state)==before,"queued_command_does_not_commit_inline")
	check(not controller.request_command(expected_command),"double_click_cannot_queue_duplicate_command")
	controller.paused=true;check(await wait_job(pending_job),"paused_job_finishes_computing")
	for i in range(4):await process_frame
	check(controller.command_busy and commits.is_empty() and ContentRegistry.fingerprint(controller.state)==before,"pause_holds_complete_result_without_mutating_state_or_rng")
	controller.paused=false;check(await wait_controller(controller,1),"resume_commits_pending_result")
	check(commits.size()==1 and ContentRegistry.fingerprint(controller.state)==ContentRegistry.fingerprint(expected.state),"resume_commits_exact_result_once_on_main_thread")
	controller.presentation_busy=false
	var saved=controller.state;var saved_hash=ContentRegistry.fingerprint(saved)
	controller.request_command(controller.command("EndPhase"));pending_job=controller._active_job
	controller.load_state(saved);await wait_job(pending_job)
	for i in range(4):await process_frame
	check(not controller.command_busy and commits.size()==1 and ContentRegistry.fingerprint(controller.state)==saved_hash,"load_invalidates_uncommitted_command_and_preserves_save_snapshot")
	controller.toggle_auto_player();await process_frame
	pending_job=controller._active_job;check(pending_job!=null,"automatic_planning_started_in_worker")
	controller.toggle_auto_player()
	if pending_job!=null:await wait_job(pending_job)
	for i in range(4):await process_frame
	check(not controller.auto_running and not controller.command_busy and commits.size()==1 and ContentRegistry.fingerprint(controller.state)==saved_hash,"stop_discards_uncommitted_plan_without_changing_rng")
	controller.request_command(controller.command("EndPhase"));pending_job=controller._active_job;controller.abandon()
	if pending_job!=null:await wait_job(pending_job)
	for i in range(4):await process_frame
	check(controller.state.is_empty() and commits.size()==1 and not controller.command_busy,"abandon_has_no_late_commit_or_ghost_planner")
	controller.queue_free();await process_frame
	check(other.worker!=null and other.start("campaign_1924_03","zhili",{},"normal"),"remaining_controller_keeps_worker_alive")
	var job=other.worker.submit("preview",other.state,other.command("EndPhase"),content)
	check(await wait_job(job) and job.result.get("valid",false),"shared_worker_still_executes_after_one_controller_exits")
	var save_path="user://qa/worker_%d"%Time.get_ticks_usec()
	var first=other.state;var latest=StateAccess.clone_transaction(first)
	latest.state_version+=1;latest.factions[0].resources.cash+=1
	var first_hash=ContentRegistry.fingerprint(first);var latest_hash=ContentRegistry.fingerprint(latest)
	var write_a=other.worker.submit("save",first,{"path":save_path,"slot":"test"},content)
	var write_b=other.worker.submit("save",latest,{"path":save_path,"slot":"test"},content)
	var listing=other.worker.submit("slots",{}, {"path":save_path},content)
	var loading=other.worker.submit("load",{}, {"path":save_path,"slot":"test"},content)
	check(await wait_job(loading) and write_a.result.get("valid",false) and write_b.result.get("valid",false),"same_slot_writes_and_load_are_serialized_and_verified")
	check(listing.result.get("slots",[]).size()==8,"slot_listing_runs_in_serialized_io_queue")
	check(loading.result.get("valid",false) and ContentRegistry.fingerprint(loading.result.state)==latest_hash,"queued_load_reads_latest_completed_save_with_exact_state_and_rng")
	check(ContentRegistry.fingerprint(first)==first_hash and ContentRegistry.fingerprint(latest)==latest_hash,"background_save_and_load_do_not_mutate_inputs")
	check(loading.result.get("valid",false) and loading.result.state.map.cells.is_read_only(),"worker_loaded_geometry_is_frozen_before_publication")
	other.load_prepared_state(loading.result.state)
	check(ContentRegistry.fingerprint(other.state)==latest_hash,"prepared_load_swaps_exact_worker_result")
	for suffix in [".json",".json.bak",".json.tmp"]:
		if FileAccess.file_exists(save_path+"/test"+suffix):DirAccess.remove_absolute(save_path+"/test"+suffix)
	DirAccess.remove_absolute(save_path)
	other.queue_free();await process_frame
	check(RulesWorker._shared==null,"last_controller_joins_worker_and_releases_query_context")
	check(not PreparedSightCache._contexts.has(loading.worker_thread_id),"worker_shutdown_releases_its_presentation_index_context")
	var report={"game_version":ContentRegistry.APP_VERSION,"content_hash":content.content_hash,"checks":checks,"passed":checks.size()-failures.size(),"failed":failures.size(),"failures":failures,"trace_commands":trace_commands,"main_thread_heartbeats":heartbeats,"longest_worker_ms":longest_worker_usec/1000.0,"scope":"Native serialized thread, immutable input snapshots, concurrent renderer queries, exact commands/events/full-state/RNG equality, pause/resume/cancel/load/lifetime. Does not certify physical Android frame time."}
	var file=FileAccess.open("res://reports/rules_worker_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("RULES_WORKER_TESTS ",report.passed," passed / ",report.failed," failed; ",trace_commands," equivalent commands; ",heartbeats," main-thread heartbeats")
	quit(0 if failures.is_empty() else 1)
