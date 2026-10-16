extends SceneTree

var content=ContentRegistry.new()
var kernel: CommandKernel
var passed: Array=[]
var failed: Array=[]
var serial=0
var base: Dictionary={}

func _init() -> void:run.call_deferred()
func check(ok: bool, name: String) -> void:
	if ok:passed.append(name)
	else:failed.append(name);push_error("FAIL: "+name)
func cmd(s: Dictionary, type: String, args: Dictionary={}) -> Dictionary:
	var c=args.duplicate(true);c.type=type;c.actor_id=s.turn_order[s.phase_index];c.expected_version=s.state_version;return c
func apply(s: Dictionary, type: String, args: Dictionary={}) -> Dictionary:
	var result=kernel.resolve(s,cmd(s,type,args))
	check(result.valid,"command_%03d_%s"%[serial,type]);serial+=1
	if not result.valid:print("REASON ",result.reason);return s
	return result.state
func fixture() -> Dictionary:
	var s=base.duplicate(true)
	s.match_id="progression_%d"%serial;serial+=1
	s.units=[];s.cities=[];s.generals=[];s.statuses=[];s.visibility=[];s.engineer_jobs=[];s.pending_aid=[];s.authored_events=[];s.event_log=[];s.protected_general_id=null;s.protected_commander_id=null
	s.objectives=[{"id":"test","type":"capture","target_ids":["unreachable"],"required":1,"progress":0,"protected":false}]
	s.map.cells=[];s.map.rail_edges=[];s.map.rail_nodes=[];s.map.crossings=[]
	for q in range(-10,11):
		for r in range(-4,5):s.map.cells.append({"id":"c_%d_%d"%[q,r],"position":{"q":q,"r":r},"terrain_id":"plain","region_id":"theater"})
	for f in s.factions:f.resources={"cash":5000,"food":5000,"arms":5000};f.command_points=5;f.equipment_whitelist=content.tables.units.map(func(d):return d.id)
	StateAccess.invalidate_occupancy();return s
func city(s: Dictionary, id: String, hex: Vector2i, owner: String="zhili", port: bool=false) -> Dictionary:
	var c={"id":id,"name":id,"position":HexGrid.position(hex),"owner_id":owner,"level":3,"fort_hp":0,"fort_max_hp":100,"stability":100,"recruit_reserve":200,"key_city":true,"port":port,"buildings":[{"def_id":"barracks","level":2,"damaged":false},{"def_id":"arsenal","level":2,"damaged":false},{"def_id":"station","level":1,"damaged":false}],"recruit_queue":[],"construction_queue":[],"construction_action_used":false,"air_sorties_left":3,"blockaded":false}
	if port:c.buildings.append({"def_id":"port","level":1,"damaged":false})
	s.cities.append(c);StateAccess.invalidate_occupancy();return c
func unit(s: Dictionary, id: String, def_id: String, hex: Vector2i, owner: String="zhili") -> Dictionary:
	var u=StateBuilder.unit(id,def_id,owner,HexGrid.position(hex),content);s.units.append(u);StateAccess.invalidate_occupancy();return u
func repository(suffix: String) -> ProfileRepository:return ProfileRepository.new(content,SaveService.new("user://progression_%d_%s"%[Time.get_ticks_usec(),suffix]))
func complete(repo: ProfileRepository, s: Dictionary, scenario_id: String="", owner: String="zhili", difficulty: String="normal", stars: int=1, won: bool=false) -> Dictionary:
	if not scenario_id.is_empty():s.scenario_id=scenario_id;s.mode=content.scenarios[scenario_id].mode
	s.player_faction_id=owner;s.difficulty=difficulty;s.normalized=difficulty=="challenge" or s.mode=="legion"
	VictoryRules.finish(s,owner if won else "",[],"fixture_completed");s.result_stars=stars
	return repo.settle(s)

func run() -> void:
	check(content.load_all(),"content_loaded");kernel=CommandKernel.new(content);base=StateBuilder.create(content,"campaign_1920_01","zhili",{})
	# A selectable conquest start must contain a strategic base, rather than lose on its first command.
	for year in [1920,1922,1924]:
		var id="conq_%d"%year;var playable=content.playable_factions(id)
		check(playable.has("zhili") and playable.has("shanxi"),"conquest_strong_and_weak_available_%d"%year)
		for owner in playable:
			var started=StateBuilder.create(content,id,owner,{})
			check(not started.is_empty() and started.cities.any(func(c):return c.owner_id==owner and c.level>=2) and started.units.any(func(u):return u.owner_id==owner),"playable_conquest_has_base_and_units_%d_%s"%[year,owner])
			if not started.is_empty():
				VictoryRules.check(started,content,[]);check(started.status=="playing","playable_conquest_not_immediately_eliminated_%d_%s"%[year,owner])
		if year!=1920:check(not playable.has("anhui") and StateBuilder.create(content,id,"anhui",{}).is_empty(),"unsupported_anhui_start_rejected_%d"%year)
	check(StateBuilder.create(content,"conq_1920","unknown_faction",{}).is_empty(),"unlisted_faction_cannot_bypass_start_menu")
	# Reward improvement, repeat settlement, migration and excluded match types.
	var repo=repository("ledger");var s=fixture();var first=complete(repo,s,"campaign_1920_01","zhili","normal",1,true)
	check(first.research==30,"one_star_first_win_research_30")
	s=fixture();var improved=complete(repo,s,"campaign_1920_01","zhili","normal",3,true)
	check(improved.merit==40 and improved.research==20,"one_to_three_star_only_unclaimed_delta")
	var before=ContentRegistry.fingerprint(repo.profile);repo.settle(s)
	check(ContentRegistry.fingerprint(repo.profile)==before,"same_completed_match_cannot_pay_twice")
	s=fixture();var repeat=complete(repo,s,"campaign_1920_01","zhili","normal",2,true)
	check(repeat.merit==0 and repeat.research==0,"lower_star_repeat_no_currency")
	s=fixture();var conquest=complete(repo,s,"conq_1920","shanxi","normal",1,true)
	check(conquest.research==90,"conquest_first_win_research_90")
	s=fixture();var conquest_bonus=complete(repo,s,"conq_1920","shanxi","normal",3,true)
	check(conquest_bonus.research==30,"conquest_later_three_star_pays_bonus_once")
	s=fixture();check(complete(repo,s,"conq_1920","shanxi","normal",3,true).research==0,"conquest_three_star_repeat_no_bonus")
	for exclusion in ["debug_match","surrendered"]:
		s=fixture();s.status="won";s.result_stars=3;s[exclusion]=true;s.metrics.general_active_skill_uses=100
		before=ContentRegistry.fingerprint(repo.profile);var result=repo.settle(s)
		check(result.get("excluded",false) and ContentRegistry.fingerprint(repo.profile)==before,"excluded_"+exclusion+"_no_stats_xp_rewards")
	s=fixture();before=ContentRegistry.fingerprint(repo.profile)
	check(repo.settle(s).has("error") and ContentRegistry.fingerprint(repo.profile)==before,"unfinished_match_cannot_settle")
	s.status="won";s.content_hash="old_version"
	check(repo.settle(s).has("error") and ContentRegistry.fingerprint(repo.profile)==before,"mismatched_rules_cannot_settle")
	var legacy=repository("legacy");legacy.profile.victories["conq_1920:normal:shanxi"]=3;legacy.profile.reward_ledger.append("victory:conq_1920:normal:shanxi")
	check(complete(legacy,fixture(),"conq_1920","shanxi","normal",3,true).research==0,"legacy_three_star_win_not_paid_again")
	# All lesson defaults must satisfy their real roster budgets and focus requirements.
	for id in content.scenarios:
		var recipe=content.scenarios[id]
		if recipe.mode!="legion":continue
		var default_army=LegionRules.default_army(content,recipe);var validation=LegionRules.validate(content,recipe,default_army,[])
		check(validation.valid,"legion_default_budget_and_focus_"+id)
		var deployed=StateBuilder.create(content,id,"zhili",{"_legion_deployment":default_army,"_legion_generals":[]})
		check(not deployed.is_empty() and deployed.legion_deployment.spent<=recipe.deployment_cash_budget,"legion_default_complete_deployment_"+id)
	var lesson=content.scenarios.legion_12
	for elite in content.tables.elite_variants:
		var army=[LegionRules.entry(content,elite.id,2),LegionRules.entry(content,"rifle")]
		var validation=LegionRules.validate(content,lesson,army,[])
		check(validation.valid,"elite_budget_accepts_two_layers_"+elite.id)
		s=StateBuilder.create(content,"legion_12","zhili",{"_legion_deployment":army,"_legion_generals":[],"tech_ranks":{"inf_drill":3},"general_ranks":{"wu_peifu":6}})
		var elites=s.get("units",[]).filter(func(u):return u.owner_id=="zhili" and u.elite_id==elite.id)
		check(elites.size()==1 and elites[0].stack==2 and elites[0].max_hp==(content.definition("units",elite.base_unit).hp+elite.hp_bonus)*2,"elite_stats_and_stack_deployed_"+elite.id)
		if not s.is_empty():check(StateAccess.faction(s,"zhili").profile_snapshot==StateAccess.faction(s,"fengtian").profile_snapshot and int(StateAccess.faction(s,"zhili").profile_snapshot.tech_ranks.get("inf_drill",0))<3,"elite_challenge_frozen_equal_snapshot_"+elite.id)
	check(not LegionRules.validate(content,content.scenarios.legion_01,[LegionRules.entry(content,"elite_assault")],[]).valid,"zero_elite_slots_reject_elite")
	check(not LegionRules.validate(content,lesson,[LegionRules.entry(content,"elite_assault"),LegionRules.entry(content,"elite_cavalry")],[]).valid,"shared_elite_slot_cap")
	check(not LegionRules.validate(content,lesson,[LegionRules.entry(content,"rifle",4)],[]).valid,"invalid_stack_rejected")
	check(not LegionRules.validate(content,lesson,[LegionRules.entry(content,"rifle")],["wu_peifu","wu_peifu"]).valid,"duplicate_general_rejected")
	check(not LegionRules.validate(content,lesson,[{"def_id":"rifle","elite_id":"elite_artillery","stack":1}],[]).valid,"mismatched_elite_base_rejected")
	var expensive: Array=[]
	for i in range(30):expensive.append(LegionRules.entry(content,"rifle",3))
	check(not LegionRules.validate(content,lesson,expensive,[]).valid,"overspent_army_rejected")
	check(StateBuilder.create(content,"legion_05","zhili",{"_legion_deployment":expensive}).is_empty(),"invalid_roster_cannot_bypass_screen")
	var small=StateBuilder.create(content,"legion_12","zhili",{"_legion_deployment":[LegionRules.entry(content,"rifle")],"_legion_generals":[]},"hard")
	var larger=StateBuilder.create(content,"legion_12","zhili",{"_legion_deployment":[LegionRules.entry(content,"rifle",3),LegionRules.entry(content,"rifle",3)],"_legion_generals":[]})
	check(small.units.filter(func(u):return u.owner_id=="fengtian").size()==larger.units.filter(func(u):return u.owner_id=="fengtian").size(),"enemy_deployment_fixed_when_player_changes_army")
	check(small.difficulty=="normal" and small.normalized,"legion_difficulty_and_growth_fixed_in_backend")
	check(larger.units.filter(func(u):return u.owner_id=="zhili").all(func(u):return u.stack==3 and u.max_hp==300),"three_layer_regular_formations_reach_battle")
	var train=StateBuilder.create(content,"legion_12","zhili",{"_legion_deployment":[LegionRules.entry(content,"armored_train"),LegionRules.entry(content,"rifle")],"_legion_generals":[]})
	check(not train.is_empty() and train.units.filter(func(u):return u.owner_id=="zhili" and u.def_id=="armored_train").all(func(u):return train.map.rail_edges.any(func(edge):return edge.damage=="intact" and edge.path_hexes.has(u.position))),"prebuilt_armored_train_deploys_on_live_track")
	var base_city=small.cities.filter(func(c):return c.owner_id=="zhili")[0]
	var queued=kernel.resolve(small,cmd(small,"Recruit",{"city_id":base_city.id,"def_id":"field_artillery","elite_id":"elite_artillery","stack":1}))
	check(queued.valid,"fixed_elite_technology_allows_city_recruitment")
	if queued.valid:
		var hash=ContentRegistry.fingerprint(queued.state)
		check(not kernel.resolve(queued.state,cmd(queued.state,"Recruit",{"city_id":base_city.id,"def_id":"assault","elite_id":"elite_assault","stack":1})).valid and ContentRegistry.fingerprint(queued.state)==hash,"queued_elite_consumes_shared_lesson_slot_atomically")
	# Ownership at the phase boundary is not evidence of a kill.
	s=fixture();unit(s,"ours","rifle",Vector2i.ZERO);var starved_enemy=unit(s,"starved_enemy","rifle",Vector2i(7,0),"anhui");starved_enemy.hp=1;starved_enemy.supply_state="NONE";starved_enemy.food_reserve=0;starved_enemy.unsupplied_own_phases=1;VisibilityRules.refresh(s,content)
	s=apply(s,"EndPhase");check(s.metrics.kills==0,"enemy_starvation_is_not_a_player_kill")
	s=fixture();unit(s,"ours","rifle",Vector2i.ZERO);var countered_enemy=unit(s,"enemy","rifle",Vector2i(1,0),"anhui");countered_enemy.hp=1;s.phase_index=1;VisibilityRules.refresh(s,content)
	s=apply(s,"Attack",{"unit_id":"enemy","target_hex":{"q":0,"r":0}});check(s.metrics.kills==1,"player_counterattack_kill_attributed_on_enemy_phase")
	# Every action achievement uses successful domain commands, not injected profile counters.
	var all=repository("all_criteria")
	for i in range(18):
		var year=[1920,1922,1924][int(i/6)];var id="campaign_%d_%02d"%[year,i%6+1]
		complete(all,fixture(),id,"zhili","normal",3,true)
	for year in [1920,1922,1924]:complete(all,fixture(),"conq_%d"%year,"shanxi" if year!=1922 else "zhejiang","challenge",3,true)
	for i in range(12):complete(all,fixture(),"legion_%02d"%(i+1),"zhili","normal",1,true)
	# Suppress a defender, kill it, then use another formation to occupy in the same round.
	s=fixture();city(s,"target",Vector2i(1,0),"anhui");unit(s,"gun","machine_gun",Vector2i.ZERO);unit(s,"captor","rifle",Vector2i(0,1));var enemy=unit(s,"enemy","rifle",Vector2i(1,0),"anhui");enemy.hp=1;enemy.suppression=60;VisibilityRules.refresh(s,content)
	s=apply(s,"Attack",{"unit_id":"gun","target_hex":{"q":1,"r":0}});s=apply(s,"Move",{"unit_id":"captor","target_hex":{"q":1,"r":0}});complete(all,s)
	for i in range(3):
		s=fixture();unit(s,"cavalry","cavalry",Vector2i.ZERO);enemy=unit(s,"enemy","field_artillery",Vector2i(1,0),"anhui");enemy.hp=1;VisibilityRules.refresh(s,content)
		s=apply(s,"Attack",{"unit_id":"cavalry","target_hex":{"q":1,"r":0}});complete(all,s)
	for i in range(3):
		s=fixture();var target=city(s,"target",Vector2i(2,0),"anhui");target.fort_hp=1;unit(s,"gun","heavy_artillery",Vector2i.ZERO);unit(s,"captor","rifle",Vector2i(1,1));VisibilityRules.refresh(s,content)
		s=apply(s,"Attack",{"unit_id":"gun","target_hex":{"q":2,"r":0}});s=apply(s,"Move",{"unit_id":"captor","target_hex":{"q":2,"r":0}});complete(all,s)
	for i in range(10):
		s=fixture();unit(s,"gun","field_artillery",Vector2i.ZERO);unit(s,"observer","rifle",Vector2i(0,1));unit(s,"enemy","rifle",Vector2i(2,0),"anhui");VisibilityRules.refresh(s,content)
		s=apply(s,"Attack",{"unit_id":"gun","target_hex":{"q":2,"r":0}});complete(all,s)
	for i in range(2):
		s=fixture();var target=city(s,"target",Vector2i(2,0),"anhui");target.fort_hp=1;StateAccess.cell(s,Vector2i.ZERO).terrain_id="river";StateAccess.cell(s,Vector2i(1,0)).terrain_id="river";unit(s,"boat","river_gunboat",Vector2i.ZERO);unit(s,"captor","rifle",Vector2i(1,1));VisibilityRules.refresh(s,content)
		s=apply(s,"Attack",{"unit_id":"boat","target_hex":{"q":2,"r":0}});s=apply(s,"Move",{"unit_id":"captor","target_hex":{"q":2,"r":0}});complete(all,s)
	for i in range(20):
		s=fixture();var caster=unit(s,"caster","rifle",Vector2i.ZERO);var gd=content.tables.generals.filter(func(g):return g.active_skill=="entrench_order")[0]
		caster.general_id=gd.id;s.generals=[{"id":gd.id,"owner_id":"zhili","rank":0,"skill_ranks":{"entrench_order":1},"cooldowns":{},"assigned_unit_id":caster.id,"injured_this_match":false,"unassign_cooldown":0,"earned_xp":0}];VisibilityRules.refresh(s,content)
		s=apply(s,"ActivateSkill",{"unit_id":"caster","target_id":"caster","target_hex":{"q":0,"r":0}});complete(all,s)
	for i in range(10):
		s=rail_fixture(false);unit(s,"traveler","rifle",Vector2i(-8,0));VisibilityRules.refresh(s,content)
		s=apply(s,"RailTransport",{"unit_id":"traveler","destination_id":"right"});complete(all,s)
	for i in range(3):
		s=rail_fixture(true);s.map.rail_edges[0].damage="broken";unit(s,"engineer","engineer",Vector2i.ZERO);VisibilityRules.refresh(s,content)
		s=apply(s,"EngineerWork",{"unit_id":"engineer","edge_id":"edge"})
		for phase in range(6):s=apply(s,"EndPhase")
		complete(all,s)
	s=rail_fixture(false);s.cities.erase(s.cities[1]);s.cities[0].owner_id="anhui";unit(s,"engineer","engineer",Vector2i(0,1))
	for i in range(3):var cut_unit=unit(s,"cut_%d"%i,"rifle",Vector2i(7+i%2,-int(i/2)),"anhui");cut_unit.food_reserve=1
	VisibilityRules.refresh(s,content);s=apply(s,"EngineerWork",{"unit_id":"engineer","edge_id":"edge","action":"demolish"})
	check(int(s.metrics.get("rail_cut_changed_enemy_supply",0))==0,"demolition_alone_does_not_award_supply_achievement")
	var storage=SaveService.new("user://progression_cut_%d"%Time.get_ticks_usec());check(storage.write("test",s,content.content_hash),"rail_cut_marker_save_succeeds");s=storage.load_slot("test",content.content_hash)
	s=apply(s,"EndPhase");check(int(s.metrics.get("rail_cut_changed_enemy_supply",0))==3,"cut_counts_three_actual_enemy_supply_drops_after_load");complete(all,s)
	for i in range(10):
		s=fixture();city(s,"home",Vector2i.ZERO);var starving=unit(s,"starving","rifle",Vector2i.ZERO);starving.supply_state="NONE";starving.food_reserve=0;VisibilityRules.refresh(s,content)
		s=apply(s,"EndPhase");s=apply(s,"EndPhase");complete(all,s)
	for i in range(5):
		s=fixture();city(s,"port",Vector2i.ZERO,"zhili",true);var ship=unit(s,"ship","transport_ship",Vector2i(1,0));StateAccess.cell(s,Vector2i(1,0)).terrain_id="river";var passenger=unit(s,"passenger","rifle",Vector2i(3,0));passenger.position=null;passenger.cargo_parent_id=ship.id;VisibilityRules.refresh(s,content)
		s=apply(s,"Disembark",{"unit_id":"passenger","target_hex":{"q":0,"r":0}});complete(all,s)
	for achievement in content.tables.achievements:check(all.profile.achievements.has(achievement.id),"verified_criterion_"+achievement.id)
	check(all.profile.achievements.size()==24,"all_24_achievement_conditions_reachable")
	# Different missions/factions/versions cannot compete on one sorted leaderboard.
	var ranked=repository("ranked")
	complete(ranked,fixture(),"conq_1924","shanxi","challenge",3,true);complete(ranked,fixture(),"legion_01","zhili","normal",1,true)
	var old=ranked.profile.career_records[0].duplicate(true);old.content_hash="old";old.rounds=0;ranked.profile.career_records.append(old)
	check(ranked.ranking_groups().size()==2 and ranked.ranking_groups().all(func(g):return g.records.size()==1),"rankings_separate_scenario_faction_and_version")
	var file=FileAccess.open("res://reports/progression_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify({"passed":passed.size(),"failed":failed.size(),"checks":passed,"failures":failed,"achievement_criteria_covered":all.profile.achievements.size(),"content_hash":content.content_hash,"ruleset_version":ContentRegistry.RUNTIME_RULESET_VERSION,"scope":"Domain fixtures and real submitted commands; not human mission balance or historical deployment approval."},"\t"));file.close()
	print("PROGRESSION_TESTS %d passed / %d failed"%[passed.size(),failed.size()]);quit(0 if failed.is_empty() else 1)

func rail_fixture(bridge: bool) -> Dictionary:
	var s=fixture();city(s,"left",Vector2i(-8,0));city(s,"right",Vector2i(8,0));s.map.rail_nodes=[{"id":"left","city_id":"left"},{"id":"right","city_id":"right"}]
	var path: Array=[]
	for q in range(-8,9):path.append({"q":q,"r":0})
	s.map.rail_edges=[{"id":"edge","node_a":"left","node_b":"right","path_hexes":path,"damage":"intact","active_from":"1900-01-01","capacity_max":12,"capacity_left":12,"is_bridge":bridge}];StateAccess.faction(s,"zhili").transport_pool=12
	return s
