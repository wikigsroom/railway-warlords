extends SceneTree

var content=ContentRegistry.new()
var checks: Array=[]
var failures: Array=[]
var trace_commands=0
var capacity_phase_traces: Array=[]
var fingerprints=preload("res://tests/immutable_state_fingerprint.gd").new()

func _init() -> void:run.call_deferred()
func check(ok: bool, name: String) -> void:
	checks.append({"name":name,"passed":ok})
	if not ok:failures.append(name);push_error(name)

func compare_visibility(s: Dictionary, name: String) -> void:
	var actual=StateAccess.clone_transaction(s);var expected=StateAccess.clone_transaction(s)
	CapacityReferenceVisibility.refresh(expected,content);VisibilityRules.refresh(actual,content)
	check(ContentRegistry.fingerprint(actual.visibility)==ContentRegistry.fingerprint(expected.visibility),name+":ordered_visibility_exploration_ghosts")
	var equal=true
	for observer in s.turn_order:
		for u in actual.units:
			equal=equal and VisibilityRules.unit_visible(actual,observer,u)==CapacityReferenceVisibility.unit_visible(expected,observer,u)
		for cell in actual.map.cells.slice(0,100):
			var h=HexGrid.coordinate(cell.position)
			equal=equal and VisibilityRules.hex_visible(actual,observer,h)==CapacityReferenceVisibility.hex_visible(expected,observer,h)
	check(equal,name+":fog_membership")

func compare_movement(s: Dictionary, name: String) -> void:
	var types={}
	for unit in s.units:
		if unit.position==null or types.has(unit.def_id):continue
		types[unit.def_id]=true
		var actual=MovementRules.reachable(s,unit,content)
		var expected=CapacityReferenceMovement020.reachable(s,unit,content)
		check(ContentRegistry.fingerprint(actual)==ContentRegistry.fingerprint(expected),name+":ordered_paths:"+unit.def_id)
	for crossing in s.map.get("crossings",[]):
		for hex in [HexGrid.coordinate(crossing.from),HexGrid.coordinate(crossing.to)]:
			check(MovementRules.neighbors(s,hex)==CapacityReferenceMovement020.neighbors(s,hex),name+":crossing_neighbors:"+str(hex))
		var a=HexGrid.coordinate(crossing.from);var b=HexGrid.coordinate(crossing.to)
		check(MovementRules.crossing_cost(s,a,b)==CapacityReferenceMovement020.crossing_cost(s,a,b),name+":crossing_cost:"+crossing.id)

func run() -> void:
	check(content.load_all(),"content_loaded")
	var kernel=CommandKernel.new(content)
	for id in content.scenarios:
		var recipe=content.scenarios[id]
		var s=StateBuilder.create(content,id,recipe.player_default,{})
		compare_visibility(s,id+":opening")
		compare_movement(s,id+":opening")
		var changed=StateAccess.clone_transaction(s)
		for sight in changed.visibility:
			sight.temporary_reveals.append({"center":changed.map.cells[-1].position.duplicate(),"radius":3,"expires_owner_phase":StateAccess.faction(changed,sight.faction_id).own_phase_index+2})
		if not changed.units.is_empty():
			changed.units[0].position=null;StateAccess.invalidate_occupancy()
		compare_visibility(changed,id+":reveal_and_embark")
		var planners={};var references={}
		for step in range(12):
			if s.status!="playing":break
			var key=s.turn_order[s.phase_index]+":"+str(StateAccess.faction(s,s.turn_order[s.phase_index]).own_phase_index)
			if not planners.has(key):planners[key]=AIPlanner.new(content,kernel);references[key]=CapacityReferenceAI020.new(content,kernel)
			var actual=planners[key].choose(s);var expected=references[key].choose(s)
			check(ContentRegistry.fingerprint(actual)==ContentRegistry.fingerprint(expected),id+":AI_command_%02d"%step)
			var result=kernel.resolve(s,actual)
			check(result.valid,id+":legal_AI_command_%02d"%step)
			if not result.valid:break
			s=result.state;trace_commands+=1
	var allied=StateBuilder.create(content,"conq_1922","zhili",{})
	for r in allied.relations:
		if r.faction_a in allied.turn_order.slice(0,3) and r.faction_b in allied.turn_order.slice(0,3):r.state="ALLIANCE"
	compare_visibility(allied,"three_faction_alliance_order")
	var sight=allied.visibility[0];VisibilityRules.hex_visible(allied,sight.faction_id,HexGrid.coordinate(allied.map.cells[0].position))
	sight.visible_cell_ids=[allied.map.cells[-1].id]
	check(VisibilityRules.hex_visible(allied,sight.faction_id,HexGrid.coordinate(allied.map.cells[-1].position)),"replaced_membership_array_invalidates_lookup")
	sight.visible_cell_ids.append(allied.map.cells[0].id)
	check(VisibilityRules.hex_visible(allied,sight.faction_id,HexGrid.coordinate(allied.map.cells[0].position)),"appended_membership_array_invalidates_lookup")
	if FileAccess.file_exists("res://tests/fixtures/capacity_full_conquest.json"):
		var map=ContentRegistry.integerize(content.read_json("res://tests/fixtures/capacity_full_conquest.json"))
		if map.get("qa_capacity_fixture",false):
			var large=CapacityFixture.create(content,map)
			compare_visibility(large,"capacity_240_full_visibility")
			compare_movement(large,"capacity_240_full_visibility")
			var a=AIPlanner.new(content,kernel);var b=CapacityReferenceAI020.new(content,kernel)
			for step in range(24):
				var command=a.choose(large);var old=b.choose(large)
				check(ContentRegistry.fingerprint(command)==ContentRegistry.fingerprint(old),"capacity_240_AI_%02d"%step)
				var result=kernel.resolve(large,command)
				check(result.valid,"capacity_240_legal_%02d"%step)
				if not result.valid:break
				large=result.state;trace_commands+=1
			for distribution in ["balanced","concentrated","single_faction"]:
				var state=CapacityFixture.create(content,map,distribution)
				fingerprints.cache.clear()
				var owner=state.turn_order[state.phase_index]
				var initial_rng=state.combat_random.duplicate(true)
				var planner=AIPlanner.new(content,kernel);var reference=CapacityReferenceAI020.new(content,kernel)
				var commands=0
				var final_expected_state=state
				while state.status=="playing" and state.turn_order[state.phase_index]==owner and commands<2400:
					var command=planner.choose(state);var old=reference.choose(state)
					var same=ContentRegistry.fingerprint(command)==ContentRegistry.fingerprint(old)
					check(same,"capacity_"+distribution+":full_phase_AI_%03d"%commands)
					if not same:break
					var actual=kernel.resolve(state,command);var expected=kernel.resolve(state,old)
					var equal=actual.valid and expected.valid and fingerprints.result_hash(actual)==fingerprints.result_hash(expected)
					check(equal,"capacity_"+distribution+":state_events_rng_%03d"%commands)
					if commands==0:check(ContentRegistry.fingerprint(actual)==ContentRegistry.fingerprint(expected),"capacity_"+distribution+":complete_raw_first_result")
					if not equal:break
					final_expected_state=expected.state
					state=actual.state;commands+=1;trace_commands+=1
				check(ContentRegistry.fingerprint(state)==ContentRegistry.fingerprint(final_expected_state),"capacity_"+distribution+":complete_raw_final_state")
				check(state.turn_order[state.phase_index]!=owner or state.status!="playing","capacity_"+distribution+":complete_phase")
				capacity_phase_traces.append({"distribution":distribution,"commands":commands,"initial_rng":initial_rng,"final_rng":state.combat_random,"final_state_sha256":ContentRegistry.fingerprint(state)})
	var mutable=StateBuilder.create(content,"campaign_1924_02","fengtian",{})
	mutable.map.crossings=mutable.map.crossings.duplicate(true)
	if not mutable.map.crossings.is_empty():
		var crossing=mutable.map.crossings[0];var a=HexGrid.coordinate(crossing.from);var b=HexGrid.coordinate(crossing.to)
		MovementRules.crossing_cost(mutable,a,b);crossing.intact=false
		check(MovementRules.crossing_cost(mutable,a,b)==CapacityReferenceMovement020.crossing_cost(mutable,a,b),"mutable_crossing_change_invalidates_geometry")
		crossing.to={"q":b.x+2,"r":b.y}
		check(MovementRules.neighbors(mutable,a)==CapacityReferenceMovement020.neighbors(mutable,a),"mutable_crossing_endpoint_preserves_order")
	var report={"passed":checks.size()-failures.size(),"failed":failures.size(),"checks":checks,"failures":failures,"content_hash":content.content_hash,"game_version":ContentRegistry.APP_VERSION,"trace_commands":trace_commands,"reference_version":"AI/movement 0.2.0; visibility 0.1.3","reference_source":"Delivered immutable source ZIPs; only unique class_name changed","measurement":"Ordered visibility, exploration, ghosts, reachable path costs/predecessors, crossing order and deterministic AI commands compared with preserved implementation. Every state field/event/RNG is checked; recursively immutable geometry and sight arrays reuse exact serialized SHA only after deep-read-only proof, with raw complete first/final fingerprints as well. These are behavior comparisons, not historical audits."}
	report.capacity_phase_traces=capacity_phase_traces
	var file=FileAccess.open("res://reports/performance_equivalence.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("PERFORMANCE_EQUIVALENCE ",report.passed," passed ",report.failed," failed ",trace_commands," commands");quit(0 if failures.is_empty() else 1)
