extends SceneTree

var content=ContentRegistry.new()
var kernel: CommandKernel
var checks: Array=[]
var failures: Array=[]
var journeys: Array=[]
var candidate_root=""

func _init() -> void:run.call_deferred()

func verify(ok: bool, name: String) -> void:
	checks.append({"name":name,"passed":ok})
	if not ok:failures.append(name);push_error("LOCAL_MAP: "+name)

func order(state: Dictionary, type: String, fields: Dictionary={}) -> Dictionary:
	var command=fields.duplicate(true);command.type=type
	command.actor_id=state.turn_order[state.phase_index];command.expected_version=state.state_version
	return kernel.resolve(state,command)

func next_own_phase(state: Dictionary) -> Dictionary:
	var result=order(state,"EndPhase")
	if not result.valid:return {}
	state=result.state
	while state.status=="playing" and state.turn_order[state.phase_index]!=state.player_faction_id:
		result=order(state,"EndPhase")
		if not result.valid:return {}
		state=result.state
	return state

func port_orders_probe(original: Dictionary, port_id: String) -> void:
	# Exercise loading, phase readiness and unloading at the actual separate bank.
	# Other forces are absent; this fixture does not measure battle difficulty.
	var state=StateAccess.clone_transaction(original)
	var port=StateAccess.find(state,"cities",port_id)
	var shore=HexGrid.position(HarborRules.land_hex(port))
	var owner=state.player_faction_id
	var passenger=StateBuilder.unit("port_probe_rifle","rifle",owner,shore,content)
	var ship=StateBuilder.unit("port_probe_ship","transport_ship",owner,port.harbor_water_position.duplicate(),content)
	state.units=[passenger,ship];state.generals=[]
	state.protected_commander_id=null;state.protected_general_id=null
	state.objectives=[{"id":"port_orders_fixture","type":"survive","required":1,"progress":0}]
	StateAccess.invalidate_occupancy();VisibilityRules.refresh(state,content)
	var prefix=original.scenario_id+":"+owner+":separate_bank_"
	var loaded=order(state,"Embark",{"unit_id":passenger.id,"ship_id":ship.id})
	verify(loaded.valid,prefix+"actual_embark_command_accepted")
	if not loaded.valid:return
	state=loaded.state;passenger=StateAccess.find(state,"units",passenger.id);ship=StateAccess.find(state,"units",ship.id)
	verify(passenger.position==null and passenger.cargo_parent_id==ship.id and passenger.ap_left==0 and ship.ap_left==0,
		prefix+"loading_commits_cargo_and_both_action_budgets")
	verify(not order(state,"Disembark",{"unit_id":passenger.id,"target_hex":shore}).valid,
		prefix+"same_phase_unloading_is_rejected")
	state=next_own_phase(state)
	verify(not state.is_empty() and state.status=="playing",prefix+"next_own_phase_preserves_fixture")
	if state.is_empty():return
	var blocked=StateAccess.clone_transaction(state)
	StateAccess.find(blocked,"cities",port_id).blockaded=true
	verify(not order(blocked,"Disembark",{"unit_id":passenger.id,"target_hex":shore}).valid,
		prefix+"blockaded_port_cannot_unload")
	var hostile=StateAccess.clone_transaction(state)
	StateAccess.find(hostile,"cities",port_id).owner_id=hostile.turn_order[1]
	verify(not order(hostile,"Disembark",{"unit_id":passenger.id,"target_hex":shore}).valid,
		prefix+"opponent_port_cannot_unload")
	StateAccess.invalidate_occupancy()
	var landed=order(state,"Disembark",{"unit_id":passenger.id,"target_hex":shore})
	verify(landed.valid,prefix+"next_phase_actual_disembark_accepted")
	if landed.valid:
		passenger=StateAccess.find(landed.state,"units",passenger.id)
		verify(passenger.cargo_parent_id==null and passenger.position==shore and passenger.ap_left==0,
			prefix+"unloading_returns_infantry_to_real_bank_with_no_free_move")

func navigation_probe(original: Dictionary) -> void:
	# Exercise actual commands on the complete board. Remove the other troops
	# for this navigation fixture; it proves route/landing legality, not AI balance.
	var state=StateAccess.clone_transaction(original)
	var objective=state.objectives[0]
	var protected=StateAccess.find(state,"units",objective.target_ids[0])
	var ship=StateAccess.find(state,"units",protected.cargo_parent_id) if objective.type=="disembark" else protected
	var keep=[protected.id,ship.id]
	state.units=state.units.filter(func(u):return keep.has(u.id))
	state.generals=[];state.protected_commander_id=null;state.protected_general_id=null
	for u in state.units:u.general_id=null
	StateAccess.invalidate_occupancy();VisibilityRules.refresh(state,content)
	var actions: Array=[];var travelled=0;var command_errors: Array=[]
	for attempt in range(60):
		if state.is_empty() or state.status!="playing":break
		ship=StateAccess.find(state,"units",ship.id)
		protected=StateAccess.find(state,"units",protected.id)
		if ship.is_empty() or protected.is_empty():break
		var destination=HexGrid.coordinate(objective.destination)
		if objective.type=="disembark" and protected.get("cargo_sailed",false) and HexGrid.distance(HexGrid.coordinate(ship.position),destination)==1:
			var landing=order(state,"Disembark",{"unit_id":protected.id,"target_hex":objective.destination})
			if landing.valid:state=landing.state;actions.append("Disembark");break
			command_errors.append(landing.reason);break
		var graph=MovementRules.reachable(state,ship,content,400)
		var best_key="";var best_cost=100000
		for key in graph.costs:
			if HexGrid.distance(HexGrid.from_key(key),destination)<=1 and int(graph.costs[key])<best_cost:
				best_key=key;best_cost=int(graph.costs[key])
		if best_key.is_empty():command_errors.append("No navigable source-water approach");break
		var path=MovementRules.route_from_graph(graph,HexGrid.coordinate(ship.position),HexGrid.from_key(best_key))
		var budget=int(ship.ap_left);var spent=0;var target=HexGrid.coordinate(ship.position)
		for i in range(1,path.size()):
			var cost=MovementRules.step_cost(state,ship,path[i-1],path[i],content)
			if cost<=0 or spent+cost>budget:break
			spent+=cost;target=path[i]
		if target!=HexGrid.coordinate(ship.position):
			var moved=order(state,"Move",{"unit_id":ship.id,"target_hex":HexGrid.position(target)})
			if not moved.valid:command_errors.append(moved.reason);break
			travelled+=spent;state=moved.state;actions.append("Move")
			if state.status!="playing":break
			if objective.type=="disembark":continue
		state=next_own_phase(state)
	verify(not state.is_empty() and state.status=="won" and state.winner_id==original.player_faction_id,
		original.scenario_id+":"+original.player_faction_id+":real_commands_complete_water_objective")
	verify(command_errors.is_empty(),original.scenario_id+":"+original.player_faction_id+":no_illegal_route_or_landing_commands")
	journeys.append({"scenario":original.scenario_id,"side":original.player_faction_id,"status":state.get("status","invalid"),
		"round":state.get("round",0),"actions":actions,"navigation_cost":travelled,"errors":command_errors,
		"other_troops_removed_for_navigation_fixture":true,"ai_combat_balance_claimed":false})

func run() -> void:
	var args=OS.get_cmdline_user_args()
	for i in range(args.size()-1):
		if args[i]=="--candidate-root":candidate_root=args[i+1]
	verify(content.load_all(),"production_definitions_and_scenarios_loaded")
	if not candidate_root.is_empty():
		for mid in ["hankou","ningpu"]:
			var file=FileAccess.open(candidate_root.path_join(mid+".json"),FileAccess.READ)
			if file==null:verify(false,"candidate_file_present:"+mid);quit(1);return
			var map=ContentRegistry.integerize(JSON.parse_string(file.get_as_text()))
			StateAccess.freeze_value(map);content.maps[mid]=map
		content.content_hash=ContentRegistry.fingerprint({"source_hash":content.content_hash,"candidate_maps":content.maps})
	kernel=CommandKernel.new(content)
	for mid in ["hankou","ningpu"]:
		var map=content.maps[mid]
		verify(map.hex_radius_m==250 and map.hex_radius_px==48,mid+":physical_grid_refined_with_unchanged_interaction_hex")
		verify(map.cells.size()>=8000 and map.cells.size()<=12000,mid+":complete_local_board_retained")
		for city in map.cities:
			verify(int(city.strategic_hex_displacement_m)<=500,city.id+":city_no_longer_displaced_kilometres_to_water")
			var land=StateAccess.cell({"map":map},HarborRules.land_hex(city))
			var water=StateAccess.cell({"map":map},HexGrid.coordinate(city.harbor_water_position))
			verify(not land.is_empty() and land.region_id!="restricted" and content.definition("terrains",land.terrain_id).cost_foot>0,city.id+":approach_is_operable_actual_bank_land")
			verify(not water.is_empty() and water.region_id!="restricted" and content.definition("terrains",water.terrain_id).water and HexGrid.distance(HarborRules.land_hex(city),HexGrid.coordinate(water.position))==1,city.id+":separate_water_approach_is_navigable_adjacent_source_water")
		verify(map.rail_edges.is_empty() and map.crossings.all(func(c):return c.kind=="ferry" and not c.rail_allowed),mid+":no_invented_cross_river_rail_bridge")
	for scenario_id in ["legion_07","legion_08"]:
		for owner in content.scenarios[scenario_id].faction_roster:
			var state=StateBuilder.create(content,scenario_id,owner,{})
			verify(not state.is_empty(),scenario_id+":"+owner+":full_default_training_army_deploys")
			if state.is_empty():continue
			var standing=true;var occupied={}
			for u in state.units:
				if u.position==null:continue
				var hex=HexGrid.coordinate(u.position);var cell=StateAccess.cell(state,hex)
				var movement=content.definition("units",u.def_id).movement_profile
				var field="cost_water" if movement in ["water","river","sea"] else "cost_"+movement
				standing=standing and not cell.is_empty() and cell.region_id!="restricted" and content.definition("terrains",cell.terrain_id).get(field,0)>0 and not occupied.has(HexGrid.key(hex))
				occupied[HexGrid.key(hex)]=true
			verify(standing,scenario_id+":"+owner+":every_initial_unit_on_valid_distinct_domain_cell")
			var target=StateAccess.find(state,"cities",content.scenarios[scenario_id].target_city_id)
			verify(HexGrid.coordinate(state.objectives[0].destination)==HarborRules.land_hex(target),scenario_id+":"+owner+":water_objective_uses_shore_instead_of_inland_city_centre")
			var isolated=StateAccess.clone_transaction(state);isolated.units=[];StateAccess.invalidate_occupancy()
			var queued={"target_def_id":"river_gunboat","deploy_hex":target.position}
			var deployed=EconomyRules.deployment_hex(isolated,target,queued,content)
			verify(deployed!=null and HexGrid.distance(HexGrid.coordinate(deployed),HarborRules.land_hex(target))<=1 and content.definition("terrains",StateAccess.cell(isolated,HexGrid.coordinate(deployed)).terrain_id).water,scenario_id+":"+owner+":naval_production_uses_real_shore_approach")
			var coverage=LogisticsRules.naval_supply_reach(isolated,owner,content)
			verify(coverage.has(HexGrid.key(HexGrid.coordinate(target.harbor_water_position))),scenario_id+":"+owner+":controlled_harbor_supplies_its_water_approach")
			var land_deployment=EconomyRules.deployment_hex(isolated,target,{"target_def_id":"rifle","deploy_hex":target.harbor_position},content)
			verify(land_deployment!=null and HexGrid.distance(HexGrid.coordinate(land_deployment),HexGrid.coordinate(target.position))<=1,
				scenario_id+":"+owner+":infantry_production_remains_at_city_centre")
			port_orders_probe(state,target.id)
			navigation_probe(state)
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"journeys":journeys,
		"candidate_only":not candidate_root.is_empty(),"candidate_root":candidate_root,"content_hash":content.content_hash,
		"version":ContentRegistry.APP_VERSION,"test_driver_sha256":FileAccess.get_sha256("res://tests/local_map_refinement_test.gd"),
		"runtime_map_sha256":{"hankou":FileAccess.get_sha256("res://content/maps/hankou.json"),"ningpu":FileAccess.get_sha256("res://content/maps/ningpu.json")},
		"physical_android_device_tested":false,"full_ai_combat_balance_claimed":false}
	var file=FileAccess.open("res://reports/local_map_refinement_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("LOCAL_MAP_TESTS ",JSON.stringify({"passed":report.passed,"checks":checks.size(),"failures":failures,"journeys":journeys}));quit(0 if failures.is_empty() else 1)
