extends SceneTree

var content=ContentRegistry.new()
var results: Array=[]
var failures: Array=[]

func _init() -> void:run.call_deferred()

func arg(name: String, fallback: String) -> String:
	var args=OS.get_cmdline_user_args();var i=args.find(name)
	return args[i+1] if i>=0 and i+1<args.size() else fallback

func percentile(values: Array, p: float = .95) -> float:
	if values.is_empty():return 0.0
	var sorted=values.duplicate();sorted.sort();return sorted[mini(sorted.size()-1,int(ceil(sorted.size()*p))-1)]

func invariant(s: Dictionary) -> bool:
	var occupied={}
	for u in s.units:
		if u.hp<=0 or u.hp>u.max_hp or u.ammo<0 or u.position==null:return false
		var key=HexGrid.key(HexGrid.coordinate(u.position));var cell=StateAccess.cell(s,HexGrid.coordinate(u.position))
		if occupied.has(key) or cell.is_empty() or cell.region_id=="restricted":return false
		occupied[key]=true
	for f in s.factions:
		for resource in f.resources:
			if f.resources[resource]<0:return false
	return true

func run() -> void:
	if not content.load_all():push_error(str(content.errors));quit(1);return
	var production_baseline="--production-baseline" in OS.get_cmdline_user_args()
	var map=content.maps.jingfeng.duplicate(true) if production_baseline else ContentRegistry.integerize(content.read_json("res://tests/fixtures/capacity_full_conquest.json"))
	if production_baseline:
		map.id="qa_original_jingfeng";map.qa_capacity_fixture=true;map.military_deployment_claimed=false
		map.fixture_source={"usable_cells":map.cells.filter(func(c):return c.region_id!="restricted").size()}
	if not map.get("qa_capacity_fixture",false):push_error("Geographic fixture not compiled");quit(1);return
	var kernel=CommandKernel.new(content)
	var baseline="--baseline" in OS.get_cmdline_user_args()
	for distribution in ["balanced","concentrated","single_faction"]:
		var initial=CapacityFixture.create(content,map.duplicate(true),distribution,0 if production_baseline else 4096)
		if initial.is_empty() or initial.units.size()!=240 or not invariant(initial):failures.append(distribution+":fixture_invalid");continue
		var before=ContentRegistry.fingerprint(initial)
		var preview_ms: Array=[];var preview_types={};var search_sizes: Array=[]
		for u in initial.units:
			if u.owner_id!=initial.turn_order[0]:continue
			var t=Time.get_ticks_usec();var graph=MovementRules.reachable(initial,u,content)
			search_sizes.append(graph.costs.size())
			preview_ms.append((Time.get_ticks_usec()-t)/1000.0)
			var targets=graph.costs.keys();targets.sort()
			for key in targets:
				if key==HexGrid.key(HexGrid.coordinate(u.position)):continue
				var c={"type":"Move","unit_id":u.id,"target_hex":HexGrid.position(HexGrid.from_key(key)),"actor_id":initial.turn_order[0],"expected_version":initial.state_version}
				t=Time.get_ticks_usec();var p=kernel.preview(initial,c);preview_ms.append((Time.get_ticks_usec()-t)/1000.0)
				preview_types.Move=int(preview_types.get("Move",0))+1
				if p.valid:break
			for enemy in initial.units:
				if not StateAccess.hostile(initial,u.owner_id,enemy.owner_id) or not CombatRules.in_range(u,enemy.position,content):continue
				var c={"type":"Attack","unit_id":u.id,"target_hex":enemy.position,"actor_id":initial.turn_order[0],"expected_version":initial.state_version}
				t=Time.get_ticks_usec();kernel.preview(initial,c);preview_ms.append((Time.get_ticks_usec()-t)/1000.0)
				preview_types.Attack=int(preview_types.get("Attack",0))+1;break
		if ContentRegistry.fingerprint(initial)!=before:failures.append(distribution+":preview_mutated_state")
		var save_registry=ContentRegistry.new();save_registry.maps=content.maps;save_registry.content_hash=initial.content_hash
		var storage=SaveService.new("user://qa/capacity_%d"%Time.get_ticks_usec(),save_registry)
		var writes: Array=[];var reads: Array=[];var save_ok=true
		for i in range(3 if baseline else 10):
			var t=Time.get_ticks_usec();var ok=storage.write("test",initial,initial.content_hash);writes.append((Time.get_ticks_usec()-t)/1000.0)
			t=Time.get_ticks_usec();var loaded=storage.load_slot("test",initial.content_hash);reads.append((Time.get_ticks_usec()-t)/1000.0)
			save_ok=save_ok and ok and ContentRegistry.fingerprint(loaded)==before and loaded.map.cells.is_read_only()
		if not save_ok:failures.append(distribution+":save_roundtrip")
		var phases: Array=[];var samples=1 if baseline else 3
		for sample in range(samples):
			var s=StateAccess.clone_transaction(initial)
			var planner=AIPlanner.new(content,kernel);var owner=s.turn_order[s.phase_index]
			var started=Time.get_ticks_usec();var commands=0;var rejects=0;var choose_ms: Array=[];var resolve_ms: Array=[];var actions={}
			while s.status=="playing" and s.turn_order[s.phase_index]==owner and commands<2400:
				var t=Time.get_ticks_usec();var c=planner.choose(s);choose_ms.append((Time.get_ticks_usec()-t)/1000.0)
				t=Time.get_ticks_usec();var r=kernel.resolve(s,c);resolve_ms.append((Time.get_ticks_usec()-t)/1000.0)
				if not r.valid:rejects+=1;failures.append(distribution+":rejected:"+str(c));break
				s=r.state;commands+=1;actions[c.type]=int(actions.get(c.type,0))+1
				if not invariant(s):failures.append(distribution+":invariant");break
			var elapsed=(Time.get_ticks_usec()-started)/1000.0
			var complete=s.turn_order[s.phase_index]!=owner or s.status!="playing"
			if not complete or rejects>0:failures.append(distribution+":phase_incomplete")
			phases.append({"ms":elapsed,"commands":commands,"rejects":rejects,"completed":complete,"actions":actions,"choose_ms_p95":percentile(choose_ms),"resolve_ms_p95":percentile(resolve_ms),"choose_ms_max":choose_ms.max(),"resolve_ms_max":resolve_ms.max(),"remaining_units":s.units.size()})
			print("CAPACITY_PHASE ",distribution," ",sample," ",JSON.stringify(phases[-1]))
		var timing={"preview_ms_p95":percentile(preview_ms),"preview_ms_max":preview_ms.max(),"samples":preview_ms.size(),"preview_types":preview_types,"search_cells_max":search_sizes.max(),"save_write_ms_p95":percentile(writes),"save_read_ms_p95":percentile(reads),"save_bytes":FileAccess.get_file_as_bytes(storage.path_for("test")).size(),"ai_phase_ms_p95":percentile(phases.map(func(p):return p.ms)),"ai_phase_ms_max":phases.map(func(p):return p.ms).max()}
		results.append({"distribution":distribution,"initial_active_units":initial.units.size(),"acting_faction_units":initial.units.filter(func(u):return u.owner_id==initial.turn_order[0]).size(),"unit_types":content.tables.units.size(),"cells":map.cells.size(),"usable_cells":map.fixture_source.usable_cells,"fixture_hash":initial.fixture_map_hash,"save_roundtrip_passed":save_ok,"phase_samples":phases,"timings":timing,"target_passed":map.fixture_source.usable_cells>=4096 and timing.preview_ms_p95<=50 and timing.ai_phase_ms_max<=5000 and timing.save_write_ms_p95<=1000 and timing.save_read_ms_p95<=1000})
	var report={"passed":failures.is_empty(),"failures":failures,"baseline":baseline,"production_map_baseline_only":production_baseline,"results":results,"all_performance_targets_passed":not results.is_empty() and results.all(func(r):return r.target_passed),"production_content_hash":content.content_hash,"game_version":ContentRegistry.APP_VERSION,"platform":OS.get_name(),"physical_android_device_tested":false,"historical_deployment_claimed":false,"measurement":"Native Godot headless; fresh 240-unit state per phase; choose+resolve+invariant wall time, no forced EndPhase; 13 unit types on compiled real geography; render measured separately."}
	var file=FileAccess.open(arg("--report-path","res://reports/capacity_domain.json"),FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("CAPACITY_DOMAIN ",JSON.stringify({"passed":report.passed,"targets":report.all_performance_targets_passed,"cases":results.size()}));quit(0 if failures.is_empty() else 1)
