extends SceneTree
const Probe=preload("res://tests/fixtures/capacity_probe.gd")
const ProbePlanner=preload("res://tests/fixtures/capacity_probe_planner.gd")
const ProbeKernel=preload("res://tests/fixtures/capacity_probe_kernel.gd")
const Fingerprint=preload("res://tests/immutable_state_fingerprint.gd")

func _init() -> void:run.call_deferred()

func run() -> void:
	var content=ContentRegistry.new()
	if not content.load_all():push_error(str(content.errors));quit(1);return
	var map=ContentRegistry.integerize(content.read_json("res://tests/fixtures/capacity_full_conquest.json"))
	var initial=CapacityFixture.create(content,map,"single_faction",4096)
	var s=StateAccess.clone_transaction(initial);var baseline=StateAccess.clone_transaction(initial)
	var kernel=ProbeKernel.new(content);var planner=ProbePlanner.new(content,kernel)
	var normal_kernel=CommandKernel.new(content);var normal_planner=AIPlanner.new(content,normal_kernel)
	var owner=s.turn_order[s.phase_index];var commands=0;var choose_us=0;var resolve_us=0;var actions={}
	var fingerprint=Fingerprint.new()
	while s.status=="playing" and s.turn_order[s.phase_index]==owner and commands<2400:
		var start=Time.get_ticks_usec();var command=planner.choose(s);choose_us+=Time.get_ticks_usec()-start
		var expected_command=normal_planner.choose(baseline)
		if ContentRegistry.fingerprint(command)!=ContentRegistry.fingerprint(expected_command):push_error("Probe changed decision");quit(1);return
		start=Time.get_ticks_usec();var result=kernel.resolve(s,command);resolve_us+=Time.get_ticks_usec()-start
		var expected=normal_kernel.resolve(baseline,expected_command)
		if not result.valid or not expected.valid or fingerprint.result_hash(result)!=fingerprint.result_hash(expected):push_error("Probe changed complete result");quit(1);return
		s=result.state;baseline=expected.state;commands+=1;actions[command.type]=int(actions.get(command.type,0))+1
	if commands<100 or ContentRegistry.fingerprint(s)!=ContentRegistry.fingerprint(baseline):push_error("Probe incomplete or changed final state");quit(1);return
	var ms={}
	for key in Probe.times:ms[key]=Probe.times[key]/1000.0
	var report={"game_version":ContentRegistry.APP_VERSION,"commands":commands,"actions":actions,"equivalent":true,"choose_ms":choose_us/1000.0,"resolve_ms":resolve_us/1000.0,"timed_ms":ms,"calls":Probe.counts,"reachable_compute_ms":Probe.Movement.compute_us/1000.0,"open_sort_ms":Probe.Movement.sort_us/1000.0,"note":"Paired instrumentation; timings include clock overhead and shared cache interference."}
	var file=FileAccess.open("res://reports/capacity_breakdown_v024.json",FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"\t"));file.close();print("CAPACITY_BREAKDOWN ",JSON.stringify(report));quit()
