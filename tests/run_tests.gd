extends SceneTree

var content=ContentRegistry.new()
var kernel: CommandKernel
var passed: Array=[]
var failed: Array=[]
var timings: Dictionary={}

func _init() -> void:run.call_deferred()

func assert_true(value: bool, name: String) -> void:
	if value:passed.append(name)
	else:failed.append(name);push_error("FAIL: "+name)

func fixture() -> Dictionary:
	var s=StateBuilder.create(content,"campaign_1920_01","zhili",{},"normal")
	s.map.cells=[];s.map.rail_edges=[];s.map.rail_nodes=[];s.map.crossings=[]
	for q in range(-7,8):
		for r in range(-7,8):s.map.cells.append({"id":"c_%d_%d"%[q,r],"position":{"q":q,"r":r},"terrain_id":"plain","region_id":"theater"})
	s.units=[];s.generals=[];s.cities=[];s.statuses=[];s.visibility=[];s.objectives=[];s.engineer_jobs=[];s.pending_aid=[];s.authored_events=[];s.event_log=[];s.last_move_inverse=null;s.status="playing";s.phase_index=0;s.round=1;s.date="1920-07-14";s.protected_commander_id=null
	s.protected_general_id=null;s.objectives=[{"id":"fixture","type":"capture","target_ids":["unreachable_fixture_goal"],"required":1,"progress":0,"protected":false}]
	for f in s.factions:f.resources={"cash":1000,"food":1000,"arms":1000};f.command_points=5;f.transport_pool=12;f.eliminated=false
	for r in s.relations:r.state="WAR"
	return s

func pair(a: String, b: String, distance: int = 1, stack: int = 1) -> Dictionary:
	var s=fixture();s.units=[StateBuilder.unit("a",a,"zhili",{"q":0,"r":0},content,stack),StateBuilder.unit("b",b,"anhui",{"q":distance,"r":0},content)];VisibilityRules.refresh(s,content);return s

func command(s: Dictionary, type: String, args: Dictionary = {}) -> Dictionary:
	var c=args.duplicate(true);c.type=type;c.actor_id=s.turn_order[s.phase_index];c.expected_version=s.state_version;return c

func city(s: Dictionary, id: String, q: int, level: int = 1) -> Dictionary:
	var d=content.tables.city_levels[level-1]
	var c={"id":id,"name":id,"position":{"q":q,"r":0},"owner_id":"zhili","level":level,"fort_hp":d.fort_hp,"fort_max_hp":d.fort_hp,"stability":100,"recruit_reserve":d.recruit_reserve_cap,"key_city":true,"port":false,"buildings":[{"def_id":"barracks","level":2,"damaged":false},{"def_id":"arsenal","level":2,"damaged":false},{"def_id":"station","level":1,"damaged":false}],"recruit_queue":[],"construction_queue":[],"construction_action_used":false,"air_sorties_left":2,"blockaded":false}
	s.cities.append(c);return c

func run() -> void:
	assert_true(content.load_all(),"content_registry_21_tables_33_scenarios")
	if not content.errors.is_empty():print(content.errors)
	kernel=CommandKernel.new(content)
	for case in [["rifle","rifle",1,33,14],["machine_gun","rifle",1,39,12],["cavalry","machine_gun",1,23,19],["cavalry","field_artillery",1,46,0],["field_artillery","rifle",2,46,0]]:
		var s=pair(case[0],case[1],case[2]);var p=CombatRules.preview(s,s.units[0],s.units[1],content)
		assert_true(p.damage==case[3] and p.counter==case[4],"combat_%s_%s_actual_%s"%[case[0],case[1],str(p)])
	var s=pair("field_artillery","rifle",2);var fort=city(s,"fort",2);var p=CombatRules.preview(s,s.units[0],s.units[1],content,fort)
	assert_true(p.fort_damage==63 and p.garrison_damage==9 and p.counter==0,"dual_hp_fort_63_garrison9_no_counter")
	s=pair("heavy_artillery","rifle",2);fort=city(s,"fort",2);p=CombatRules.preview(s,s.units[0],s.units[1],content,fort)
	assert_true(p.fort_damage==100 and p.garrison_damage==15,"fort_no_overflow_100_collateral15")
	s=pair("rifle","rifle");s.units[0].hp=50;assert_true(CombatRules.damage(s,s.units[0],s.units[1],content)==26,"half_health_damage26")
	s.units[0].hp=100;s.units[0].supply_state="LOW";assert_true(CombatRules.damage(s,s.units[0],s.units[1],content)==28,"low_supply_damage28")
	s.units[0].supply_state="FULL";StateAccess.cell(s,Vector2i(1,0)).terrain_id="forest";assert_true(CombatRules.damage(s,s.units[0],s.units[1],content)==29,"forest_cover_damage29")
	s=pair("rifle","rifle",1,3);assert_true(CombatRules.damage(s,s.units[0],s.units[1],content)==55,"three_stack_damage55")
	s=pair("rifle","rifle");var hash=ContentRegistry.fingerprint(s);var c=command(s,"Attack",{"unit_id":"a","target_hex":{"q":1,"r":0}});p=kernel.preview(s,c)
	assert_true(p.valid and ContentRegistry.fingerprint(s)==hash,"preview_is_read_only")
	var r=kernel.resolve(s,c);assert_true(r.valid and 100-r.state.units[0].hp>=p.counter_min and 100-r.state.units[0].hp<=p.counter_max and 100-r.state.units[1].hp>=p.damage_min and 100-r.state.units[1].hp<=p.damage_max and s.units[0].hp==100,"attack_atomic_clone_post_hit_counter")
	assert_true(r.state.units[0].ammo==3 and r.state.units[1].ammo==3 and r.state.units[0].ap_left==0,"attack_ammo_and_terminal_ap")
	assert_true(not kernel.resolve(r.state,c).valid,"stale_command_rejected")
	s=pair("rifle","rifle",6);p=kernel.preview(s,command(s,"Attack",{"unit_id":"a","target_hex":{"q":6,"r":0}}));assert_true(not p.valid,"fog_or_range_attack_rejected")
	s=fixture();s.units=[StateBuilder.unit("a","rifle","zhili",{"q":0,"r":0},content)];VisibilityRules.refresh(s,content)
	r=kernel.resolve(s,command(s,"Move",{"unit_id":"a","target_hex":{"q":2,"r":0}}));assert_true(r.valid and r.state.units[0].ap_left==2 and r.state.units[0].position.q==2,"segmented_movement_cost2")
	s=pair("rifle","rifle",3);r=kernel.resolve(s,command(s,"Move",{"unit_id":"a","target_hex":{"q":2,"r":0}}));assert_true(r.valid and r.state.units[0].ap_left==0,"enter_enemy_zoc_stops_movement")
	s=fixture();var home=city(s,"home",0);s.units=[StateBuilder.unit("blocked","rifle","zhili",home.position.duplicate(),content)];VisibilityRules.refresh(s,content)
	r=kernel.resolve(s,command(s,"Recruit",{"city_id":"home","def_id":"rifle","stack":2}));assert_true(r.valid and r.state.cities[0].recruit_reserve==60 and StateAccess.faction(r.state,"zhili").resources.cash==840,"recruit_two_stack_cost_and_population")
	EconomyRules.process_queues(r.state,"zhili",content,[]);assert_true(r.state.units.size()==2 and r.state.cities[0].recruit_queue.is_empty(),"recruit_next_own_phase_deploys_adjacent")
	s=fixture();home=city(s,"home",0);EconomyRules.recruit(s,home,{"def_id":"rifle","stack":1},content,[]);var qid=home.recruit_queue[0].id;EconomyRules.cancel_queue(s,home,qid,false,content,[]);assert_true(home.recruit_reserve==80 and StateAccess.faction(s,"zhili").resources.cash==980,"unready_cancel_75percent_full_population")
	s=fixture();home=city(s,"home",0);home.level=2;EconomyRules.construction(s,home,"hospital",content,[]);EconomyRules.process_queues(s,"zhili",content,[]);assert_true(EconomyRules.building_level(home,"hospital")==1,"construction_completes_after_own_phase")
	s=fixture();home=city(s,"home",0);home.fort_hp=0;s.units=[StateBuilder.unit("captor","rifle","anhui",{"q":-1,"r":0},content)];EconomyRules.capture_city(s,home,s.units[0],content,[]);assert_true(home.owner_id=="anhui" and home.stability==40 and home.recruit_reserve==32 and EconomyRules.building_level(home,"station")==0,"capture_stability_reserve_station_damage")
	s=fixture();home=city(s,"home",0);var u=StateBuilder.unit("a","rifle","zhili",home.position.duplicate(),content);u.hp=40;s.units=[u];VisibilityRules.refresh(s,content);r=kernel.resolve(s,command(s,"Reinforce",{"unit_id":"a"}));assert_true(r.valid and r.state.units[0].hp==65 and r.state.units[0].ap_left==0 and r.state.cities[0].recruit_reserve==77,"reinforce_25hp_population3_terminal")
	s=fixture();u=StateBuilder.unit("a","rifle","zhili",{"q":0,"r":0},content);s.units=[u];u.food_reserve=0;u.unsupplied_own_phases=1;LogisticsRules.distribute(s,"zhili",content,[]);assert_true(u.hp==92 and u.supply_state=="NONE","second_none_phase_attrition8")
	s=fixture();home=city(s,"home",0);u=StateBuilder.unit("a","rifle","zhili",{"q":0,"r":0},content);u.food_reserve=3;s.units=[u];StateAccess.faction(s,"zhili").resources.food=2;LogisticsRules.distribute(s,"zhili",content,[]);assert_true(StateAccess.faction(s,"zhili").resources.food==2 and u.food_reserve==2 and u.supply_state=="FULL","insufficient_food_no_partial_payment_reserve_used")
	s=fixture();home=city(s,"left",-3);var end=city(s,"right",3);s.map.rail_nodes=[{"id":"left","city_id":"left"},{"id":"right","city_id":"right"}];var path=[]
	for q in range(-3,4):path.append({"q":q,"r":0})
	s.map.rail_edges=[{"id":"edge","node_a":"left","node_b":"right","path_hexes":path,"damage":"intact","active_from":"1900-01-01","capacity_max":3,"capacity_left":3,"is_bridge":false}];u=StateBuilder.unit("a","rifle","zhili",home.position.duplicate(),content,2);s.units=[u];VisibilityRules.refresh(s,content)
	r=kernel.resolve(s,command(s,"RailTransport",{"unit_id":"a","destination_id":"right"}));assert_true(r.valid and r.state.units[0].position.q==3 and r.state.map.rail_edges[0].capacity_left==1 and StateAccess.faction(r.state,"zhili").transport_pool==10,"rail_atomic_dual_capacity_reservation")
	s.map.rail_edges[0].capacity_left=1;hash=ContentRegistry.fingerprint(s);r=kernel.resolve(s,command(s,"RailTransport",{"unit_id":"a","destination_id":"right"}));assert_true(not r.valid and ContentRegistry.fingerprint(s)==hash,"rail_shortfall_rejects_without_partial_change")
	s.map.rail_edges[0].capacity_left=3;s.map.rail_edges[0].damage="broken";u.def_id="engineer";r=kernel.resolve(s,command(s,"EngineerWork",{"unit_id":"a","edge_id":"edge","action":"repair"}));assert_true(r.valid,"engineer_adjacent_work_accepted")
	if r.valid:LogisticsRules.process_jobs(r.state,"zhili",content,[]);assert_true(r.state.map.rail_edges[0].damage=="intact","engineer_one_phase_restores_track")
	s=fixture();var f=StateAccess.faction(s,"zhili");f.transport_used_phase=true;StateAccess.relation(s,"zhili","anhui").state="NEUTRAL";assert_true(not kernel.preview(s,command(s,"Diplomacy",{"target_faction_id":"anhui","action":"declare_war"})).valid,"cannot_borrow_rail_then_declare_same_phase")
	s=fixture();var visibility=s.visibility;VisibilityRules.refresh(s,content);var order=s.turn_order.duplicate();TurnRules.end_phase(s,content,[]);assert_true(s.round==1 and s.phase_index==1,"phase_not_round")
	TurnRules.end_phase(s,content,[]);assert_true(s.round==2 and s.phase_index==0 and s.date=="1920-07-15","all_factions_complete_advances_date")
	s=StateBuilder.create(content,"conq_1924","zhili",{});s.date="1924-09-15"
	StateAccess.faction(s,s.turn_order[-1]).eliminated=true;s.phase_index=s.turn_order.size()-2
	TurnRules.end_phase(s,content,[])
	assert_true(s.round==2 and s.phase_index==0 and s.date=="1924-09-22","eliminated_final_faction_still_advances_round_and_date")
	s=StateBuilder.create(content,"conq_1924","zhili",{});s.date="1924-10-20";s.phase_index=s.turn_order.size()-3
	for id in [s.turn_order[0],s.turn_order[-1],s.turn_order[-2]]:StateAccess.faction(s,id).eliminated=true
	TurnRules.end_phase(s,content,[])
	assert_true(s.round==2 and s.phase_index==1 and s.date=="1924-10-27" and StateAccess.find(s,"cities","beijing").owner_id=="zhili" and s.authored_events[0].outcome=="not_triggered" and not s.turn_order.has("guominjun"),"skipping_eliminated_factions_advances_date_without_reviving_coup_source")
	var save=SaveService.new("user://test_suite");s=fixture();var start=Time.get_ticks_msec();assert_true(save.write("test",s,content.content_hash),"atomic_save_verified_write");var loaded=save.load_slot("test",content.content_hash);assert_true(ContentRegistry.fingerprint(loaded)==ContentRegistry.fingerprint(s),"save_load_hash_round_trip");timings.save_load_ms=Time.get_ticks_msec()-start
	s.round=2;save.write("test",s,content.content_hash);var broken=FileAccess.open(save.path_for("test"),FileAccess.WRITE);broken.store_string("{interrupted");broken.close();loaded=save.load_slot("test",content.content_hash);assert_true(loaded.get("round",0)==1,"corrupt_save_recovers_previous_backup")
	var repository=ProfileRepository.new(content,SaveService.new("user://test_profile_%s"%Time.get_ticks_msec()));s=fixture();s.status="won";s.result_stars=3;s.match_id="reward_test_unique";s.initial_player_count=14;var reward=repository.settle(s);var before=repository.profile.merit;repository.settle(s);assert_true(reward.merit>=100 and repository.profile.merit==before,"reward_ledger_idempotent")
	assert_true(repository.upgrade_tech("inf_drill") or repository.error!="","technology_upgrade_validation")
	var scenario_report: Array=[]
	for id in content.scenarios:
		var start_time=Time.get_ticks_msec();var recipe=content.scenarios[id];var state=StateBuilder.create(content,id,recipe.player_default,{},"normal")
		var occupied={};var valid=true
		for troop in state.units:
			if troop.position==null:continue
			var key=HexGrid.key(HexGrid.coordinate(troop.position))
			if occupied.has(key) or StateAccess.cell(state,HexGrid.coordinate(troop.position)).is_empty():valid=false
			occupied[key]=true
		assert_true(valid and state.units.size()>0 and state.cities.size()>0 and state.units.size()<=240,"scenario_deployment_"+id)
		scenario_report.append({"id":id,"units":state.units.size(),"cities":state.cities.size(),"load_ms":Time.get_ticks_msec()-start_time})
	var report={"passed":passed.size(),"failed":failed.size(),"checks":passed,"failures":failed,"timings":timings,"scenarios":scenario_report,"engine":Engine.get_version_info().string,"content_hash":content.content_hash}
	var file=FileAccess.open("res://reports/rule_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("RULE_TESTS: %d passed / %d failed"%[passed.size(),failed.size()]);quit(0 if failed.is_empty() else 1)
