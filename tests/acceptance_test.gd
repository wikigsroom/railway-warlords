extends SceneTree

var content=ContentRegistry.new()
var kernel: CommandKernel
var passed: Array=[]
var failed: Array=[]
var replay_times: Array=[]
var replay_phases: Array=[]

func _init() -> void:run.call_deferred()
func verify(ok: bool, name: String) -> void:
	if ok:passed.append(name)
	else:failed.append(name);push_error("FAIL: "+name)
func cmd(s: Dictionary, type: String, args: Dictionary={}) -> Dictionary:
	var c=args.duplicate(true);c.type=type;c.actor_id=s.turn_order[s.phase_index];c.expected_version=s.state_version;return c
func fixture() -> Dictionary:
	var s=StateBuilder.create(content,"campaign_1920_01","zhili",{},"normal")
	s.units=[];s.cities=[];s.generals=[];s.statuses=[];s.visibility=[];s.engineer_jobs=[];s.pending_aid=[];s.authored_events=[];s.protected_general_id=null;s.protected_commander_id=null
	s.objectives=[{"id":"test","type":"capture","target_ids":["unreachable"],"required":1,"progress":0,"protected":false}]
	s.map.cells=[];s.map.rail_edges=[];s.map.rail_nodes=[];s.map.crossings=[]
	for q in range(-9,10):
		for r in range(-9,10):s.map.cells.append({"id":"c_%d_%d"%[q,r],"position":{"q":q,"r":r},"terrain_id":"plain","region_id":"theater"})
	for f in s.factions:f.resources={"cash":2000,"food":2000,"arms":2000};f.command_points=5;f.equipment_whitelist=content.tables.units.map(func(d):return d.id)
	StateAccess.invalidate_occupancy();return s
func add_city(s: Dictionary, id: String, hex: Vector2i, port: bool=false) -> Dictionary:
	var c={"id":id,"name":id,"position":HexGrid.position(hex),"owner_id":"zhili","level":3,"fort_hp":100,"fort_max_hp":100,"stability":100,"recruit_reserve":200,"key_city":true,"port":port,"buildings":[{"def_id":"barracks","level":2,"damaged":false},{"def_id":"arsenal","level":2,"damaged":false},{"def_id":"station","level":1,"damaged":false}],"recruit_queue":[],"construction_queue":[],"construction_action_used":false,"air_sorties_left":3,"blockaded":false}
	if port:c.buildings.append({"def_id":"port","level":1,"damaged":false})
	s.cities.append(c);return c
func add_unit(s: Dictionary, id: String, definition: String, hex: Vector2i, owner: String="zhili", stack: int=1) -> Dictionary:
	var u=StateBuilder.unit(id,definition,owner,HexGrid.position(hex),content,stack);s.units.append(u);StateAccess.invalidate_occupancy();return u
func add_general(s: Dictionary, id: String, u: Dictionary, rank: int=0) -> Dictionary:
	var d=content.definition("generals",id);var g={"id":id,"owner_id":u.owner_id,"rank":rank,"skill_ranks":{d.passive_skill:1,d.active_skill:1},"cooldowns":{},"assigned_unit_id":u.id,"injured_this_match":false,"unassign_cooldown":0,"earned_xp":0};u.general_id=id;s.generals.append(g);StateAccess.faction(s,u.owner_id).general_whitelist.append(id);return g

func run() -> void:
	verify(content.load_all(),"content_loaded");kernel=CommandKernel.new(content)
	# Every active skill must have a legal, resource-charged execution and reject a duplicate.
	for d in content.tables.skills:
		if d.kind!="active":continue
		var s=fixture();var candidates=content.tables.generals.filter(func(g):return g.active_skill==d.id)
		if candidates.is_empty():candidates=content.tables.generals.filter(func(g):return g.stars.cavalry>=3)
		var gd=candidates[0]
		var def_id="rifle"
		for ud in content.tables.units:
			if ud.attack>0 and EffectRules.scope_matches(d.caster_scope,{"def_id":ud.id},content):def_id=ud.id;break
		var caster=add_unit(s,"caster",def_id,Vector2i.ZERO);var general=add_general(s,gd.id,caster)
		general.active_skill_id=d.id
		var distance=maxi(1,int(content.definition("units",def_id).range_min))
		var enemy=add_unit(s,"enemy","rifle",Vector2i(distance,0),"anhui");enemy.hp=100;enemy.suppression=60
		var target=caster
		if d.id=="field_repair":target=add_unit(s,"vehicle","armored_car",Vector2i(0,1));target.hp=30
		if d.id=="ration_order":caster.food_reserve=0
		if d.id=="coordinated_fire":add_unit(s,"observer","rifle",Vector2i(1,1))
		StateAccess.cell(s,Vector2i(distance,1)).terrain_id="river"
		VisibilityRules.refresh(s,content)
		var args={"unit_id":caster.id,"target_id":enemy.id if d.consumes_main_attack else target.id,"target_hex":enemy.position.duplicate()}
		var before_cash=StateAccess.faction(s,"zhili").resources.cash;var before_cp=StateAccess.faction(s,"zhili").command_points
		var result=kernel.resolve(s,cmd(s,"ActivateSkill",args))
		verify(result.valid,"active_skill_exec_"+d.id)
		if result.valid:
			verify(StateAccess.faction(result.state,"zhili").command_points==before_cp-d.command_cost and StateAccess.faction(result.state,"zhili").resources.cash==before_cash-d.resource_cost.cash,"active_skill_cost_"+d.id)
			verify(not kernel.preview(result.state,cmd(result.state,"ActivateSkill",args)).valid,"active_skill_repeat_rejected_"+d.id)
		else:print("SKILL_REASON ",d.id," ",result.reason)
	var s=fixture();var city=add_city(s,"home",Vector2i.ZERO);var u=add_unit(s,"center","rifle",Vector2i.ZERO)
	for dir in HexGrid.DIRECTIONS:add_unit(s,"block_%s"%str(dir),"rifle",dir)
	EconomyRules.recruit(s,city,{"def_id":"rifle","stack":1},content,[]);EconomyRules.process_queues(s,"zhili",content,[])
	verify(city.recruit_queue.size()==1 and s.units.size()==7,"blocked_deployment_preserves_queue_and_units")
	StateAccess.remove_by_id(s,"units",s.units[-1].id);EconomyRules.process_queues(s,"zhili",content,[])
	verify(city.recruit_queue.is_empty() and s.units.size()==7,"ready_queue_deploys_after_space_reopens")
	s=fixture();city=add_city(s,"hostile_flag",Vector2i(1,0));city.owner_id="anhui";city.fort_hp=0;u=add_unit(s,"moving","engineer",Vector2i.ZERO);add_unit(s,"friendly_transit","rifle",Vector2i(1,0));VisibilityRules.refresh(s,content)
	var transit=kernel.resolve(s,cmd(s,"Move",{"unit_id":u.id,"target_hex":{"q":2,"r":0}}))
	verify(transit.valid and StateAccess.find(transit.state,"units",u.id).position=={"q":2,"r":0} and StateAccess.find(transit.state,"cities",city.id).owner_id=="anhui","friendly_transit_cannot_capture_and_stop_on_occupied_flag")
	s=fixture();city=add_city(s,"home",Vector2i.ZERO);u=add_unit(s,"center","rifle",Vector2i.ZERO)
	# All 28 technology branches participate without violating the combat, AP and cost caps.
	for tech in content.tables.technologies:StateAccess.faction(s,"zhili").profile_snapshot.tech_ranks[tech.id]=3
	u.general_id=null;s.statuses.append({"id":"test_status","target_id":u.id,"def_id":"fortified_order","value":1000,"source_owner_id":"zhili","expires_owner_phase":-1})
	verify(CombatRules.attack_bonus(s,u,content)<=int(content.rules.combat.attack_bonus_cap_max) and CombatRules.defense(s,u,content)<=int(content.rules.combat.defense_cap),"technology_combat_hard_caps")
	verify(EffectRules.reduced_cost({"cash":100,"arms":1},900)=={"cash":70,"arms":1},"cost_discount_30percent_and_nonzero_floor")
	TurnRules.own_start(s,"zhili",content,[]);verify(u.ap_left<=8,"all_technology_ap_cap")
	# Ship terminal actions, port access and deterministic emergency evacuation.
	s=fixture();city=add_city(s,"port",Vector2i.ZERO,true);u=add_unit(s,"cargo","rifle",Vector2i.ZERO);var ship=add_unit(s,"ship","transport_ship",Vector2i(1,0));StateAccess.cell(s,Vector2i(1,0)).terrain_id="river";VisibilityRules.refresh(s,content)
	var r=kernel.resolve(s,cmd(s,"Embark",{"unit_id":u.id,"ship_id":ship.id}));verify(r.valid,"port_embark_legal")
	if r.valid:
		verify(r.state.units[0].position==null and r.state.units[0].ap_left==0 and r.state.units[1].ap_left==0,"embark_terminates_both_actors")
		verify(not kernel.preview(r.state,cmd(r.state,"Disembark",{"unit_id":u.id,"target_hex":city.position})).valid,"same_phase_cargo_chain_rejected")
		TurnRules.own_start(r.state,"zhili",content,[]);var unloaded=kernel.resolve(r.state,cmd(r.state,"Disembark",{"unit_id":u.id,"target_hex":city.position}));verify(unloaded.valid and unloaded.state.units[0].ap_left==0 and unloaded.state.units[0].cargo_parent_id==null,"next_phase_controlled_port_unload")
	s=fixture();ship=add_unit(s,"ship","transport_ship",Vector2i.ZERO);StateAccess.cell(s,Vector2i.ZERO).terrain_id="river";var a=add_unit(s,"a","rifle",Vector2i(4,0));var b=add_unit(s,"b","rifle",Vector2i(5,0));a.position=null;b.position=null;a.cargo_parent_id=ship.id;b.cargo_parent_id=ship.id;StateAccess.invalidate_occupancy();VisibilityRules.refresh(s,content);CombatRules.defeat(s,ship,[],content)
	verify(s.units.size()==2 and a.position!=null and b.position!=null and a.position!=b.position and a.hp==50 and b.hp==50,"ship_sink_sorted_nonoverlapping_50percent_evacuations")
	s=fixture();ship=add_unit(s,"ship","transport_ship",Vector2i.ZERO);u=add_unit(s,"cargo","rifle",Vector2i(1,0));u.position=null;u.cargo_parent_id=ship.id
	for cell in s.map.cells:cell.terrain_id="river"
	VisibilityRules.refresh(s,content);CombatRules.defeat(s,ship,[],content);verify(s.units.is_empty(),"ship_sink_no_legal_shore_defeats_cargo")
	s=fixture();u=add_unit(s,"gunboat","river_gunboat",Vector2i.ZERO);StateAccess.cell(s,Vector2i.ZERO).terrain_id="river";var bridge=StateAccess.cell(s,Vector2i(1,0));bridge.terrain_id="ford";bridge.water_under_bridge=true
	verify(MovementRules.step_cost(s,u,Vector2i.ZERO,Vector2i(1,0),content)==1,"navigable_water_continues_under_rail_bridge")
	# Aircraft cannot bypass ownership, scenario access, weather or fortification.
	s=fixture();city=add_city(s,"airfield",Vector2i.ZERO);city.buildings.append({"def_id":"airfield","level":1,"damaged":false});StateAccess.faction(s,"zhili").airfield_whitelist=[city.id];u=add_unit(s,"friendly","rifle",Vector2i.ZERO);var target_city=add_city(s,"target",Vector2i(2,0));target_city.owner_id="anhui";add_unit(s,"enemy","rifle",Vector2i(2,0),"anhui");VisibilityRules.refresh(s,content)
	s.weather.current="rain";verify(not kernel.preview(s,cmd(s,"AirBomb",{"city_id":city.id,"target_hex":target_city.position})).valid,"rain_grounding_bomber")
	s.weather.current="clear";r=kernel.resolve(s,cmd(s,"AirBomb",{"city_id":city.id,"target_hex":target_city.position}));verify(r.valid and StateAccess.find(r.state,"cities","target").owner_id=="anhui" and StateAccess.find(r.state,"cities","target").fort_hp<100,"air_bomb_damages_without_capture")
	StateAccess.faction(s,"zhili").airfield_whitelist=[];verify(not kernel.preview(s,cmd(s,"AirRecon",{"city_id":city.id,"target_hex":target_city.position})).valid,"unlisted_airfield_cannot_fly")
	# Frozen progression and seasonally plausible forecast.
	var profile={"tech_ranks":{"inf_drill":1},"general_ranks":{"wu_peifu":1}}
	s=StateBuilder.create(content,"campaign_1920_01","zhili",profile);profile.tech_ranks.inf_drill=3
	verify(StateAccess.faction(s,"zhili").profile_snapshot.tech_ranks.inf_drill==1,"profile_freezes_at_match_start")
	verify(TurnRules.weather_at(s,"1920-07-21",8)!="snow" and TurnRules.weather_at(s,"1920-12-21",8)=="snow","summer_no_snow_winter_north_snow")
	s=StateBuilder.create(content,"conq_1924","zhili",{});s.date="1924-10-27";s.round=9;TurnRules.round_start(s,content,[])
	verify(s.turn_order.has("guominjun") and StateAccess.find(s,"cities","beijing").owner_id=="guominjun" and StateAccess.relation(s,"zhili","guominjun").state=="WAR","date_driven_coup_transfers_city_and_diplomacy")
	var count=s.factions.size();TurnRules.round_start(s,content,[]);verify(s.factions.size()==count,"historical_event_fires_once")
	# Real map river training must have water-adjacent controlled ports and protected cargo.
	for id in ["legion_07","legion_08"]:
		s=StateBuilder.create(content,id,"zhili",{})
		verify(s.cities.all(func(c):return not c.port or HexGrid.DIRECTIONS.any(func(dir):return StateAccess.cell(s,HexGrid.coordinate(c.position)+dir).get("terrain_id","") in ["river","sea"])),"real_port_water_neighbors_"+id)
		if id=="legion_08":
			verify(s.units.any(func(v):return v.cargo_parent_id!=null) and HexGrid.distance(HexGrid.coordinate(s.cities[0].position),HexGrid.coordinate(s.cities[1].position))>=2,"opposite_bank_ports_and_loaded_transport")
			var passenger=s.units.filter(func(v):return v.cargo_parent_id!=null)[0];var transport=StateAccess.find(s,"units",passenger.cargo_parent_id)
			verify(HexGrid.distance(HexGrid.coordinate(transport.position),HexGrid.coordinate(s.objectives[0].destination))>=4,"cross_river_transport_starts_away_from_destination")
			verify(not kernel.preview(s,cmd(s,"Disembark",{"unit_id":passenger.id,"target_hex":s.objectives[0].destination})).valid,"cross_river_training_cannot_instantly_win_before_sailing")
	# Twenty state samples: disk round-trip and the SAME next command must converge exactly.
	var storage=SaveService.new("user://acceptance_%d"%Time.get_ticks_msec(),content);s=StateBuilder.create(content,"campaign_1920_01","zhili",{})
	var rng=RandomNumberGenerator.new();rng.seed=19241023
	for i in range(20):
		if s.status!="playing":s=StateBuilder.create(content,"campaign_1920_01","zhili",{})
		var planner=AIPlanner.new(content,kernel);var c=planner.choose(s);var start=Time.get_ticks_usec()
		var written=storage.write("test",s,content.content_hash);var restored=storage.load_slot("test",content.content_hash)
		var direct=kernel.resolve(s,c);var replay=kernel.resolve(restored,c)
		verify(written and direct.valid and replay.valid and ContentRegistry.fingerprint(direct.state)==ContentRegistry.fingerprint(replay.state),"save_load_same_command_replay_%02d"%i)
		replay_phases.append({"round":s.round,"phase_index":s.phase_index,"owner_id":s.turn_order[s.phase_index]})
		replay_times.append((Time.get_ticks_usec()-start)/1000.0)
		if direct.valid:s=direct.state
		for skip in range(rng.randi_range(1,3)):
			if s.status!="playing":break
			var next_phase=kernel.resolve(s,cmd(s,"EndPhase"))
			if next_phase.valid:s=next_phase.state
	verify(storage.load_slot("test","different_ruleset").is_empty() and not storage.error.is_empty(),"wrong_content_hash_preserves_save_and_rejects_load")
	var file=FileAccess.open("res://reports/acceptance_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify({"passed":passed.size(),"failed":failed.size(),"checks":passed,"failures":failed,"replay_cases":20,"sampled_phases":replay_phases,"save_load_replay_total_ms":replay_times,"content_hash":content.content_hash},"\t"));file.close();print("ACCEPTANCE_TESTS %d passed / %d failed"%[passed.size(),failed.size()]);quit(0 if failed.is_empty() else 1)
