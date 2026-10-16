extends SceneTree

class TimedKernel extends CommandKernel:
	var preview_us=0
	var preview_calls=0
	var resolve_us=0
	func preview(s: Dictionary, c: Dictionary) -> Dictionary:
		var start=Time.get_ticks_usec();var result=super.preview(s,c)
		preview_us+=Time.get_ticks_usec()-start;preview_calls+=1;return result
	func resolve(s: Dictionary, c: Dictionary) -> Dictionary:
		var start=Time.get_ticks_usec();var result=super.resolve(s,c)
		resolve_us+=Time.get_ticks_usec()-start;return result

class TimedPlanner extends AIPlanner:
	var cache_us=0
	var cache_calls=0
	var prepare_us=0
	func cached_attack(s: Dictionary, u: Dictionary, c: Dictionary) -> Dictionary:
		var start=Time.get_ticks_usec();var result=super.cached_attack(s,u,c)
		cache_us+=Time.get_ticks_usec()-start;cache_calls+=1;return result
	func prepare_attack_cache(s: Dictionary) -> void:
		var start=Time.get_ticks_usec();super.prepare_attack_cache(s)
		prepare_us+=Time.get_ticks_usec()-start

func _init() -> void:run.call_deferred()

func run() -> void:
	var content=ContentRegistry.new()
	if not content.load_all():push_error(str(content.errors));quit(1);return
	var args=OS.get_cmdline_user_args()
	var fixture="res://tests/fixtures/capacity_jingfeng.json"
	if "--fixture" in args:fixture=args[args.find("--fixture")+1]
	var distributions: Array=["balanced","single_faction"]
	if "--distributions" in args:distributions=Array(args[args.find("--distributions")+1].split(","))
	var map=ContentRegistry.integerize(content.read_json(fixture))
	var reports=[]
	for distribution in distributions:
		var s=CapacityFixture.create(content,map.duplicate(true),distribution,4096)
		var copy_samples=[]
		for sample in range(20):
			var started=Time.get_ticks_usec();var copied=StateAccess.clone_transaction(s)
			copy_samples.append((Time.get_ticks_usec()-started)/1000.0)
			if sample==0 and ContentRegistry.fingerprint(copied)!=ContentRegistry.fingerprint(s):push_error("Copy changed state");quit(1);return
		var kernel=TimedKernel.new(content);var planner=TimedPlanner.new(content,kernel)
		var choose_us=0;var commands=0;var owner=s.turn_order[s.phase_index]
		var actions={};var command_times=[]
		while s.status=="playing" and s.turn_order[s.phase_index]==owner and commands<2400:
			var start=Time.get_ticks_usec();var c=planner.choose(s);var elapsed=Time.get_ticks_usec()-start
			choose_us+=elapsed
			var resolved=kernel.resolve(s,c)
			if not resolved.valid:push_error(resolved.reason);quit(1);return
			s=resolved.state;commands+=1;actions[c.type]=int(actions.get(c.type,0))+1
			command_times.append({"type":c.type,"choose_ms":elapsed/1000.0})
		var report={"distribution":distribution,"commands":commands,"actions":actions,
			"choose_ms":choose_us/1000.0,"cache_ms":planner.cache_us/1000.0,
			"prepare_ms":planner.prepare_us/1000.0,"cache_calls":planner.cache_calls,
			"kernel_preview_ms":kernel.preview_us/1000.0,"kernel_preview_calls":kernel.preview_calls,
			"kernel_resolve_ms":kernel.resolve_us/1000.0,"command_times":command_times,
			"snapshot_copy_ms_samples":copy_samples,"fixture":fixture,"cells":map.cells.size()}
		reports.append(report)
		var compact=report.duplicate();compact.erase("command_times");print("CAPACITY_PROFILE ",JSON.stringify(compact))
	var out="res://reports/capacity_profile_v"+ContentRegistry.APP_VERSION.replace(".","")+".json"
	if "--report-path" in args:out=args[args.find("--report-path")+1]
	var file=FileAccess.open(out,FileAccess.WRITE)
	file.store_string(JSON.stringify({"content_hash":content.content_hash,"version":ContentRegistry.APP_VERSION,"profiles":reports},"\t"));file.close();quit()
