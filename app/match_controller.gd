class_name MatchController
extends Node

signal changed(events: Array)
signal rejected(reason: String)
signal ai_status(text: String)
signal command_committed(command: Dictionary)
signal busy_changed()

var content: ContentRegistry
var kernel: CommandKernel
var worker: RulesWorker
var state: Dictionary={}
var facing_memory=FacingMemory.new()
var ai_running=false
var paused=false
var presentation_busy=false
var presentation_enabled=false
var command_busy=false
var auto_player=false
var auto_running=false
var generation=0
var ai_phase_times: Array=[]
var ai_phase_compute_times: Array=[]
var main_work_usec: Array=[]
var main_work_details: Array=[]
var worker_times: Array=[]
var presentation_options: Dictionary={"cinematics":true,"reduced_motion":false}
var prepared_presentation: Dictionary={}
var _active_job: RulesJob
var _auto_epoch=0
var _committing=false

func setup(registry: ContentRegistry) -> void:
	content=registry;kernel=CommandKernel.new(content)
	if worker==null:worker=RulesWorker.acquire()

func _exit_tree() -> void:
	_cancel_work()
	if worker!=null:worker.release();worker=null

func _cancel_work() -> void:
	generation+=1;_auto_epoch+=1
	if _active_job!=null:_active_job.cancel();_active_job=null
	ai_running=false;command_busy=false;auto_running=false;auto_player=false;prepared_presentation={}

func start(scenario_id: String, player: String, profile: Dictionary, difficulty: String) -> bool:
	var next=StateBuilder.create(content,scenario_id,player,profile,difficulty)
	if next.is_empty():rejected.emit("当前剧本未提供该势力的完整起局，或编组无法完整部署");return false
	_cancel_work();paused=false;presentation_busy=false
	state=next;facing_memory.reset(state);changed.emit([]);return true

func command(type: String, arguments: Dictionary = {}) -> Dictionary:
	var c=arguments.duplicate(true);c.type=type;c.actor_id=state.turn_order[state.phase_index];c.expected_version=state.state_version;return c

func _accept_command(c: Dictionary, from_ai: bool) -> bool:
	if state.is_empty():rejected.emit("当前没有战局");return false
	if paused or presentation_busy or command_busy or _committing or ((ai_running or auto_running) and not from_ai):rejected.emit("演出进行中、战局暂停或自动部署中");return false
	if not from_ai and c.get("actor_id")!=state.player_faction_id:rejected.emit("对手正在行动");return false
	return true

# Synchronous data/QA API. Interactive controls use request_command(), and AI
# uses the same serialized worker; no production input calls resolve() here.
func dispatch(c: Dictionary, from_ai: bool = false) -> bool:
	if not _accept_command(c,from_ai):return false
	var result=kernel.resolve(state,c)
	if not result.valid:rejected.emit(result.reason);return false
	_commit_result(c,result)
	if not from_ai:_continue_turn()
	return true

func request_command(c: Dictionary) -> bool:
	if not _accept_command(c,false):return false
	var started=Time.get_ticks_usec()
	var job=worker.submit("resolve",state,c,content,null,presentation_options)
	_active_job=job;command_busy=true;busy_changed.emit()
	main_work_usec.append(Time.get_ticks_usec()-started)
	_finish_requested.call_deferred(job,generation)
	return true

func _finish_requested(job: RulesJob, token: int) -> void:
	while token==generation and (not job.is_completed() or paused):await get_tree().process_frame
	if token!=generation:return
	var started=Time.get_ticks_usec()
	command_busy=false;_active_job=null
	if not _result_current(job):rejected.emit("战局已经更新，请重新选择");busy_changed.emit();return
	worker_times.append(job.worker_usec)
	if not job.result.get("valid",false):rejected.emit(job.result.get("reason","命令无法执行"));busy_changed.emit();return
	_commit_result(job.command,job.result)
	main_work_usec.append(Time.get_ticks_usec()-started)
	_continue_turn()

func _result_current(job: RulesJob) -> bool:
	return not state.is_empty() and is_same(state,job.base) and int(job.command.get("expected_version",-1))==int(state.state_version)

func _commit_result(c: Dictionary, result: Dictionary) -> void:
	assert(OS.get_thread_caller_id()==OS.get_main_thread_id())
	facing_memory.commit(result.state,result.events,state)
	state=result.state;prepared_presentation=result.get("presentation",{})
	# Gate reentrant command observers before announcing the atomic commit.
	# The presentation listener releases this gate when it has no animation.
	presentation_busy=presentation_enabled and not result.events.is_empty();_committing=true
	command_committed.emit(c.duplicate(true));changed.emit(result.events);_committing=false

func _continue_turn() -> void:
	if state.status=="playing" and state.turn_order[state.phase_index]!=state.player_faction_id:run_ai.call_deferred()

func _planned_command(planner: AIPlanner, token: int, auto_epoch: int = -1) -> bool:
	var started=Time.get_ticks_usec()
	var job=worker.submit("plan",state,{},content,planner,presentation_options)
	var queued=Time.get_ticks_usec()
	_active_job=job;command_busy=true;busy_changed.emit()
	var submitted=Time.get_ticks_usec()
	main_work_usec.append(submitted-started);main_work_details.append({"kind":"submit","queue_us":queued-started,"listeners_us":submitted-queued})
	while token==generation and (auto_epoch<0 or auto_epoch==_auto_epoch) and (not job.is_completed() or paused or presentation_busy):await get_tree().process_frame
	if token!=generation or (auto_epoch>=0 and auto_epoch!=_auto_epoch):job.cancel();return false
	started=Time.get_ticks_usec();command_busy=false;_active_job=null
	worker_times.append(job.worker_usec)
	if not _result_current(job) or not job.result.get("valid",false):return false
	_commit_result(job.command,job.result)
	var committed=Time.get_ticks_usec();main_work_usec.append(committed-started);main_work_details.append({"kind":"commit","listeners_us":committed-started})
	return true

func run_ai() -> void:
	if ai_running or command_busy or paused or state.is_empty():return
	ai_running=true;var token=generation
	while not state.is_empty() and state.status=="playing" and state.turn_order[state.phase_index]!=state.player_faction_id:
		if token!=generation:break
		if paused or presentation_busy:await get_tree().process_frame;continue
		var owner=state.turn_order[state.phase_index];var planner=AIPlanner.new(content,kernel)
		ai_status.emit("%s 正在部署"%StateAccess.faction_name(state,owner,content))
		var start_time=Time.get_ticks_msec();var count=0;var compute_usec=0
		var planning_limit=maxi(100,state.units.filter(func(u):return u.owner_id==owner).size()*16+state.cities.size()*8+32)
		while state.status=="playing" and state.turn_order[state.phase_index]==owner and count<planning_limit:
			if token!=generation:break
			if paused or presentation_busy:await get_tree().process_frame;continue
			if not await _planned_command(planner,token):
				if token!=generation:return
				paused=true;ai_running=false;busy_changed.emit();rejected.emit("对手命令未通过校验，战局已保留，可保存后重新载入。");return
			compute_usec+=worker_times[-1];count+=1
			await get_tree().process_frame
		if token!=generation:break
		if count>=planning_limit and state.status=="playing" and state.turn_order[state.phase_index]==owner:
			paused=true;ai_running=false;rejected.emit("对手部署暂缓，战局已保留。可保存后重新载入。");ai_status.emit("对手行动已暂停");return
		ai_phase_times.append(Time.get_ticks_msec()-start_time);ai_phase_compute_times.append(compute_usec)
		await get_tree().process_frame
	if token!=generation:return
	ai_running=false;ai_status.emit("");busy_changed.emit()
	if auto_player:run_auto_player.call_deferred()

func toggle_auto_player() -> void:
	auto_player=not auto_player;_auto_epoch+=1
	if not auto_player and auto_running:
		if _active_job!=null:_active_job.cancel();_active_job=null
		auto_running=false;command_busy=false
	ai_status.emit("自动作战已开启，可随时停止" if auto_player else "自动作战已停止")
	if auto_player and not state.is_empty() and state.turn_order[state.phase_index]==state.player_faction_id:run_auto_player.call_deferred()
	busy_changed.emit()

func run_auto_player() -> void:
	if auto_running or ai_running or command_busy or not auto_player or state.is_empty() or state.status!="playing":return
	auto_running=true;var token=generation;var epoch=_auto_epoch;var planner=AIPlanner.new(content,kernel)
	while token==generation and epoch==_auto_epoch and auto_player and state.status=="playing" and state.turn_order[state.phase_index]==state.player_faction_id:
		if paused or presentation_busy:await get_tree().process_frame;continue
		if not await _planned_command(planner,token,epoch):
			if token!=generation or epoch!=_auto_epoch:return
			auto_player=false;rejected.emit("自动作战命令未通过校验，战局已保留");break
		await get_tree().process_frame
	if token!=generation or epoch!=_auto_epoch:return
	auto_running=false;busy_changed.emit()
	_continue_turn()

func load_state(saved: Dictionary, presentation: Dictionary = {}) -> void:
	_cancel_work();paused=false;presentation_busy=false
	# Loading must not mutate a snapshot still being read by a cancelled worker.
	state=StateAccess.clone_transaction(saved);VisibilityRules.refresh(state,content);facing_memory.reset(state,presentation.get("facing",{}));changed.emit([])
	_continue_turn()

func load_prepared_state(saved: Dictionary, presentation: Dictionary = {}) -> void:
	# The worker owns the loaded file until publishing it, and has refreshed sight.
	_cancel_work();paused=false;presentation_busy=false;state=saved;facing_memory.reset(state,presentation.get("facing",{}));changed.emit([])
	_continue_turn()

func abandon() -> void:
	_cancel_work();state={};paused=false;presentation_busy=false
