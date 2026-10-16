extends SceneTree

var content=ContentRegistry.new()
var kernel: CommandKernel
var results: Array=[]

func _init() -> void:run.call_deferred()

func run() -> void:
	if not content.load_all():print(content.errors);quit(1);return
	kernel=CommandKernel.new(content)
	var cases: Array=[]
	for id in content.scenarios:
		var mode=content.scenarios[id].mode
		for difficulty in (["normal","hard","challenge"] if mode=="campaign" else ["normal"]):cases.append({"id":id,"difficulty":difficulty})
	var args=OS.get_cmdline_user_args()
	if "--only" in args:
		var index=args.find("--only");var requested_ids=str(args[index+1]).split(",")
		cases=cases.filter(func(c):return requested_ids.has(c.id))
	if "--mode" in args:
		var index=args.find("--mode");cases=cases.filter(func(c):return content.scenarios[c.id].mode==args[index+1])
	if "--mixed-players" in args:
		var expanded: Array=[]
		for case in cases:
			expanded.append(case)
			var recipe=content.scenarios[case.id]
			var weak=recipe.get("weak_faction_ids",[]).filter(func(f):return content.playable_factions(case.id).has(f))
			# Some historical conquest maps intentionally expose only the default
			# capital as a level-2 start.  Full regression can still exercise the
			# published weak-player labels explicitly; this does not change runtime
			# scenario availability or any game rule.
			if "--force-weak" in args and weak.is_empty():weak=recipe.get("weak_faction_ids",[])
			if recipe.mode=="conquest" and not weak.is_empty():expanded.append({"id":case.id,"difficulty":case.difficulty,"player":weak[0]})
		cases=expanded
	var failed=false
	var completed_rounds=0;var total_commands=0
	for case in cases:
		var id=case.id;var recipe=content.scenarios[id];var state=StateBuilder.create(content,id,case.get("player",recipe.player_default),{},case.difficulty)
		var planners={};var phase=-1;var commands=0;var rejects=0;var preview_times: Array=[];var resolve_times: Array=[];var start=Time.get_ticks_msec()
		var phase_times: Array=[];var phase_key="";var phase_started=Time.get_ticks_msec();var peak_units=state.units.size();var last_reported_round=-1
		var limit=4 if state.mode=="conquest" else mini(8,recipe.round_limit+1)
		if "--full" in args:limit=int(recipe.round_limit)
		var guard=maxi(6000,limit*220*state.turn_order.size()*2) if "--full" in args else 6000
		while state.status=="playing" and state.round<=limit and commands<guard:
			if "--full" in args and state.round!=last_reported_round:
				last_reported_round=state.round
				var progress=FileAccess.open("res://reports/ai_full_conquest_progress.json",FileAccess.WRITE)
				progress.store_string(JSON.stringify({"running":true,"id":id,"player":state.player_faction_id,"round":state.round,"commands":commands,"elapsed_ms":Time.get_ticks_msec()-start,"completed_cases":results.size(),"content_hash":content.content_hash}));progress.close()
				if state.round%10==0:print("SOAK_PROGRESS ",id," ",state.player_faction_id," round ",state.round," commands ",commands)
			var owner=state.turn_order[state.phase_index]
			var key=owner+":"+str(StateAccess.faction(state,owner).own_phase_index)
			if key!=phase_key:
				if not phase_key.is_empty():phase_times.append(Time.get_ticks_msec()-phase_started)
				phase_key=key;phase_started=Time.get_ticks_msec()
			if not planners.has(key):planners[key]=AIPlanner.new(content,kernel)
			var c=planners[key].choose(state)
			var t=Time.get_ticks_usec();var p=kernel.preview(state,c);preview_times.append((Time.get_ticks_usec()-t)/1000.0)
			if not p.valid:rejects+=1;c=command(state,"EndPhase")
			t=Time.get_ticks_usec();var result=kernel.resolve(state,c);resolve_times.append((Time.get_ticks_usec()-t)/1000.0)
			if not result.valid:failed=true;break
			var before=state;state=result.state;commands+=1
			peak_units=maxi(peak_units,state.units.size())
			var occupied={}
			var violations: Array=[]
			for u in state.units:
				if u.hp<=0 or u.hp>u.max_hp or u.ammo<0:failed=true;violations.append("hp_or_ammo:"+u.id)
				if u.position!=null:
					var cell=HexGrid.key(HexGrid.coordinate(u.position))
					if occupied.has(cell):failed=true;violations.append("overlap:%s:%s:%s"%[cell,occupied[cell],u.id])
					occupied[cell]=u.id
			for f in state.factions:
				for resource in f.resources:
					if f.resources[resource]<0:failed=true;violations.append("negative_resource:"+f.id+":"+resource)
			if failed:
				var repro=FileAccess.open("res://reports/soak_failure.json",FileAccess.WRITE);repro.store_string(JSON.stringify({"scenario_id":id,"difficulty":case.difficulty,"command":c,"before":before,"after":state,"violations":violations}));repro.close()
				print("SOAK INVARIANT FAILED ",id," command ",commands," ",violations," action ",c);break
		if state.status=="playing" and state.round<=limit:
			failed=true;push_error("SOAK did not advance to the requested round limit: "+id)
		phase_times.append(Time.get_ticks_msec()-phase_started);phase_times.sort();preview_times.sort();resolve_times.sort()
		completed_rounds+=state.round-1;total_commands+=commands
		var report={"id":id,"difficulty":case.difficulty,"player":state.player_faction_id,"requested_rounds":limit,"completed_rounds":state.round-1,"terminal_before_requested_rounds":state.status!="playing" and state.round<=limit,"round":state.round,"status":state.status,"commands":commands,"rejects":rejects,"elapsed_ms":Time.get_ticks_msec()-start,"preview_ms_p95":percentile(preview_times),"resolve_ms_p95":percentile(resolve_times),"ai_phase_ms_p95":percentile(phase_times),"peak_units":peak_units,"kills":state.metrics.kills,"losses":state.metrics.losses,"captures":state.metrics.captures,"invariants_passed":not failed}
		results.append(report);print(JSON.stringify(report))
		if failed:break
	var summary={"cases":results.size(),"completed_rounds":completed_rounds,"commands":total_commands,"invariants_passed":not failed,"full_match_run":"--full" in args,"meets_100_aggregate_rounds":completed_rounds>=100,"single_match_100_rounds":results.any(func(r):return r.completed_rounds>=100),"meets_80_round_conquest":results.any(func(r):return r.id.begins_with("conq_") and r.completed_rounds>=80),"content_hash":content.content_hash,"results":results}
	var report_path="res://reports/ai_soak.json"
	if "--report-path" in args and args.find("--report-path")+1<args.size():report_path=args[args.find("--report-path")+1]
	var file=FileAccess.open(report_path,FileAccess.WRITE);file.store_string(JSON.stringify(summary,"\t"));file.close();print("SOAK_TOTAL_ROUNDS ",completed_rounds);quit(1 if failed else 0)
	if "--full" in args:
		var progress=FileAccess.open("res://reports/ai_full_conquest_progress.json",FileAccess.WRITE);progress.store_string(JSON.stringify({"running":false,"cases":results.size(),"passed":not failed,"content_hash":content.content_hash}));progress.close()

func command(s: Dictionary, type: String) -> Dictionary:return {"type":type,"actor_id":s.turn_order[s.phase_index],"expected_version":s.state_version}
func percentile(values: Array) -> float:return values[mini(values.size()-1,int(values.size()*.95))] if not values.is_empty() else 0.0
